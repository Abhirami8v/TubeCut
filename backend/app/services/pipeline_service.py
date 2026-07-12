"""
pipeline_service.py

Orchestrates the full "paste a link -> get clips" pipeline as a single
background task, updating the Job row's status/progress at each step so
the frontend's step-by-step UI can poll GET /jobs/{id} and render live
progress. This is the only module that calls every other service in
sequence; individual services stay independent and unit-testable.
"""

from __future__ import annotations

import json
import traceback
from threading import Semaphore

from sqlalchemy.orm import Session

from app.core.config import REFRAME_TARGET_HEIGHT, REFRAME_TARGET_WIDTH, TARGET_CLIP_COUNT
from app.core.logging_utils import JobLogger
from app.core.database import SessionLocal
from app.models.caption import CaptionBlock
from app.models.clip import Clip
from app.models.job import Job, JobStatus
from app.services import (
    audio_service,
    caption_burn_service,
    caption_service,
    clip_service,
    gemini_service,
    hook_score_service,
    reframe_service,
    style_service,
    transcription_router,
    transcription_service,
    video_service,
)

# Global semaphore to limit active jobs running concurrently
_job_semaphore = Semaphore(1)


def _update_job(db: Session, job: Job, *, status: JobStatus, progress: float, label: str) -> None:
    job.status = status
    job.progress_percent = progress
    job.current_step_label = label
    db.commit()


def run_pipeline(
    job_id: str,
    url: str,
    target_clip_count: int | None,
    auto_reframe: bool,
    auto_caption_style_id: str | None,
) -> None:
    """
    Entry point invoked as a FastAPI BackgroundTask.
    Serially runs jobs using a global Semaphore to avoid CPU/RAM OOM.
    """
    with _job_semaphore:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job is None:
                return

            _run_pipeline_inner(db, job, url, target_clip_count, auto_reframe, auto_caption_style_id)

        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            try:
                db.rollback()
                job = db.query(Job).filter(Job.id == job_id).first()
                if job is not None:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    job.current_step_label = "Failed"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


def _run_pipeline_inner(
    db: Session,
    job: Job,
    url: str,
    target_clip_count: int | None,
    auto_reframe: bool,
    auto_caption_style_id: str | None,
) -> None:
    import gc
    import os

    # --- Step 1: download -------------------------------------------------
    _update_job(db, job, status=JobStatus.DOWNLOADING, progress=5, label="Downloading video")
    logger = JobLogger(job.id)
    download = video_service.download_video(url, logger=logger)
    job.source_title = download["title"]
    job.source_duration = download["duration"] or video_service.probe_duration(download["file_path"])
    job.source_video_path = download["file_path"]
    db.commit()

    # --- Step 2: extract audio ---------------------------------------------
    _update_job(db, job, status=JobStatus.EXTRACTING_AUDIO, progress=20, label="Extracting audio track")
    audio_path = audio_service.extract_audio(job.source_video_path, job_id=job.id)
    job.source_audio_path = audio_path
    db.commit()
    gc.collect()

    # --- Step 3: transcribe --------------------------------------------------
    _update_job(db, job, status=JobStatus.TRANSCRIBING, progress=35, label="Transcribing speech")
    transcript = transcription_router.transcribe(audio_path, logger=logger)
    job.transcript_json = json.dumps(transcript)
    db.commit()

    # Clean up the audio file immediately to save disk space
    try:
        os.remove(audio_path)
        logger.info(f"Cleaned up temporary audio track: {audio_path}")
    except OSError:
        pass
    gc.collect()

    # --- Step 4: AI analysis / segmentation -----------------------------
    _update_job(db, job, status=JobStatus.ANALYZING, progress=50, label="Analyzing transcript for clip-worthy moments")
    candidates = gemini_service.analyze_transcript(transcript, target_clip_count or TARGET_CLIP_COUNT)
    gc.collect()

    # --- Step 5: build Clip rows with hook scores -------------------------
    _update_job(db, job, status=JobStatus.SEGMENTING, progress=60, label="Scoring and segmenting clips")

    default_style = None
    if auto_caption_style_id:
        default_style = style_service.get_style(db, auto_caption_style_id)
    if default_style is None:
        default_style = style_service.get_default_style(db)

    clip_rows: list[Clip] = []
    for idx, candidate in enumerate(candidates):
        start = max(0.0, candidate["start_time"])
        end = min(job.source_duration or candidate["end_time"], candidate["end_time"])
        if end <= start:
            continue

        clip_words = transcription_service.words_in_range(transcript, start, end)
        text = candidate.get("title") and candidate.get("reason") or transcription_service.text_in_range(
            transcript, start, end
        )
        full_text = transcription_service.text_in_range(transcript, start, end)

        hook_breakdown = hook_score_service.compute_hook_score(full_text, clip_words)
        viral_score = hook_score_service.blend_scores(candidate["confidence_score"], hook_breakdown["total"])

        clip = Clip(
            job_id=job.id,
            index_in_job=idx,
            title=candidate.get("title") or f"Clip {idx + 1}",
            source_start_time=start,
            source_end_time=end,
            trim_start_time=start,
            trim_end_time=end,
            transcript_text=full_text,
            confidence_score=candidate["confidence_score"],
            hook_score=hook_breakdown["total"],
            viral_score=viral_score,
            ai_reason=candidate.get("reason"),
            render_status="pending",
            applied_style_id=default_style.id if default_style else None,
        )
        db.add(clip)
        db.flush()  # assign clip.id

        blocks = caption_service.build_blocks_from_words(
            clip_words, words_per_block=default_style.words_per_block if default_style else 3
        )
        for block in blocks:
            db.add(CaptionBlock(clip_id=clip.id, **block))

        clip_rows.append(clip)

    db.commit()
    gc.collect()

    # --- Step 6: render each clip (trim -> [reframe] -> burn captions) ----
    _update_job(db, job, status=JobStatus.RENDERING_CLIPS, progress=70, label="Rendering clips")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    from app.core.config import MAX_PARALLEL_CLIP_RENDERS

    total = max(len(clip_rows), 1)

    def render_task(clip_id):
        # SQLAlchemy sessions are not thread-safe, so each thread needs its own session
        thread_db = SessionLocal()
        try:
            clip = thread_db.query(Clip).filter(Clip.id == clip_id).first()
            job_thread = thread_db.query(Job).filter(Job.id == job.id).first()
            if clip and job_thread:
                _render_single_clip(thread_db, job_thread, clip, auto_reframe)
                return clip_id, True, None
            return clip_id, False, "Clip or Job not found"
        except Exception as e:
            traceback.print_exc()
            try:
                clip = thread_db.query(Clip).filter(Clip.id == clip_id).first()
                if clip:
                    clip.render_status = "failed"
                    thread_db.commit()
            except Exception:
                pass
            return clip_id, False, str(e)
        finally:
            thread_db.close()

    completed_count = 0
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CLIP_RENDERS) as executor:
        futures = {executor.submit(render_task, clip.id): clip.id for clip in clip_rows}
        for future in as_completed(futures):
            clip_id, success, error_msg = future.result()
            completed_count += 1
            progress = 70 + int(28 * (completed_count / total))
            _update_job(
                db,
                job,
                status=JobStatus.RENDERING_CLIPS,
                progress=min(98, progress),
                label=f"Rendering clip {completed_count} of {total}",
            )

    _update_job(db, job, status=JobStatus.COMPLETED, progress=100, label="Done")

    # Clean up the large source video file to save disk space
    if job.source_video_path:
        try:
            os.remove(job.source_video_path)
            logger.info(f"Cleaned up large source video file: {job.source_video_path}")
        except OSError:
            pass

    gc.collect()


def _render_single_clip(db: Session, job: Job, clip: Clip, auto_reframe: bool) -> None:
    clip.render_status = "rendering"
    db.commit()

    logger = JobLogger(job.id)

    # Step 1: Render uncaptioned clip
    uncaptioned_path = clip_service.render_uncaptioned_clip(
        source_video_path=job.source_video_path,
        trim_start_time=clip.trim_start_time,
        trim_end_time=clip.trim_end_time,
        clip_id=clip.id,
        auto_reframe=auto_reframe,
        logger=logger,
    )

    if auto_reframe:
        clip.reframed_clip_path = uncaptioned_path
        clip.is_vertical = True
    else:
        clip.raw_clip_path = uncaptioned_path
    db.commit()

    # Step 2: Burn captions on top of the uncaptioned clip
    style_dict = None
    block_dicts = None
    if clip.applied_style and clip.caption_blocks:
        style_dict = clip.applied_style.to_dict()
        block_dicts = [b.to_dict() for b in clip.caption_blocks]

    final_path = clip_service.render_captioned_only(
        uncaptioned_path=uncaptioned_path,
        clip_id=clip.id,
        applied_style=style_dict,
        caption_blocks=block_dicts,
        logger=logger,
    )

    clip.final_clip_path = final_path
    clip.thumbnail_path = clip_service.generate_thumbnail(final_path, clip.id)
    clip.render_status = "ready"
    db.commit()
