"""
api/clips.py

All per-clip endpoints: fetching a single clip's full detail (with
caption blocks), trimming/re-rendering, caption block CRUD (update,
split, merge), and applying a caption style (which triggers a re-burn
so the preview always reflects the latest edit).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.caption import CaptionBlock, CaptionStyle
from app.models.clip import Clip
from app.schemas.clip import (
    ApplyStyleRequest,
    ClipResponse,
    CreateCaptionRequest,
    DeleteCaptionRequest,
    MergeCaptionRequest,
    SplitCaptionRequest,
    TrimClipRequest,
    TrimRenderResponse,
    UpdateCaptionRequest,
)
from app.services import caption_burn_service, caption_service, clip_service, style_service, transcription_service
from app.utils.file_urls import to_media_url

router = APIRouter(tags=["clips"])


def _get_clip_or_404(db: Session, clip_id: str) -> Clip:
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip


def _clip_to_response(clip: Clip) -> ClipResponse:
    summary = clip.to_summary_dict()
    return ClipResponse(
        **summary,
        preview_url=to_media_url(clip.final_clip_path or clip.reframed_clip_path or clip.raw_clip_path),
        final_url=to_media_url(clip.final_clip_path),
        download_url=f"/clips/{clip.id}/download" if clip.final_clip_path else None,
        thumbnail_url=to_media_url(clip.thumbnail_path),
        caption_blocks=[b.to_dict() for b in sorted(clip.caption_blocks, key=lambda b: b.order_index)],
    )


def _rebuild_caption_indices(clip: Clip, db: Session) -> None:
    blocks = sorted(clip.caption_blocks, key=lambda b: b.start_time)
    for i, block in enumerate(blocks):
        block.order_index = i
    db.commit()


def _reburn_clip(db: Session, clip: Clip) -> None:
    """Re-generate the .ass file from current blocks/style and re-render the final mp4."""
    job = clip.job
    if not job or not job.source_video_path:
        return

    clip.render_status = "rendering"
    db.commit()

    try:
        style = clip.applied_style
        if style is None:
            style = style_service.get_default_style(db)
            clip.applied_style_id = style.id
            db.commit()

        style_dict = style.to_dict()
        block_dicts = [b.to_dict() for b in sorted(clip.caption_blocks, key=lambda b: b.order_index)]

        from app.core.logging_utils import JobLogger
        logger = JobLogger(job.id)

        final_path = clip_service.render_clip_final(
            source_video_path=job.source_video_path,
            trim_start_time=clip.trim_start_time,
            trim_end_time=clip.trim_end_time,
            clip_id=clip.id,
            auto_reframe=clip.is_vertical,
            applied_style=style_dict,
            caption_blocks=block_dicts,
            logger=logger,
        )

        clip.final_clip_path = final_path
        clip.thumbnail_path = clip_service.generate_thumbnail(final_path, clip.id)
        clip.render_status = "ready"
        db.commit()
    except Exception as e:
        clip.render_status = "failed"
        db.commit()
        raise e


def _rebuild_word_accurate_captions(db: Session, clip: Clip) -> None:
    """Restore one CaptionBlock per Whisper word for kinetic styles."""
    if not clip.job.transcript_json:
        return
    try:
        transcript = json.loads(clip.job.transcript_json)
    except (TypeError, json.JSONDecodeError):
        return

    words = transcription_service.words_in_range(
        transcript,
        clip.trim_start_time,
        clip.trim_end_time,
    )
    if not words:
        return

    for block in list(clip.caption_blocks):
        db.delete(block)
    db.flush()
    for index, word in enumerate(words):
        start = max(0.0, float(word["start"]))
        end = max(start + 0.06, float(word["end"]))
        db.add(
            CaptionBlock(
                clip_id=clip.id,
                order_index=index,
                start_time=start,
                end_time=end,
                text=str(word["word"]).strip(),
            )
        )
    db.commit()
    db.refresh(clip)


@router.get("/clips/{clip_id}", response_model=ClipResponse)
def get_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    return _clip_to_response(clip)


@router.get("/clips/{clip_id}/download")
def download_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    file_path = Path(clip.final_clip_path or clip.reframed_clip_path or clip.raw_clip_path or "")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Rendered video is not available")

    safe_title = "".join(char if char.isalnum() or char in " -_" else "_" for char in clip.title).strip()
    filename = f"{safe_title or 'tubecut-clip'}.mp4"
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        content_disposition_type="attachment",
    )


@router.post("/clips/{clip_id}/trim", response_model=TrimRenderResponse)
def trim_clip(clip_id: str, payload: TrimClipRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    job = clip.job

    if not job.source_video_path:
        raise HTTPException(status_code=400, detail="Source video unavailable for this job")

    clip_duration = clip.source_end_time - clip.source_start_time
    if payload.trim_start_time < 0 or payload.trim_end_time > clip_duration:
        raise HTTPException(status_code=400, detail="Trim window must fall within the original clip bounds")
    if payload.trim_end_time <= payload.trim_start_time:
        raise HTTPException(status_code=400, detail="trim_end_time must be greater than trim_start_time")

    absolute_start = clip.source_start_time + payload.trim_start_time
    absolute_end = clip.source_start_time + payload.trim_end_time

    clip.render_status = "rendering"
    db.commit()

    try:
        clip.trim_start_time = absolute_start
        clip.trim_end_time = absolute_end
        db.commit()

        # Clear cached crop json because the trim window has changed!
        from app.core.config import CLIPS_DIR
        import os
        cache_path = CLIPS_DIR / f"crop_{clip.id}.json"
        if cache_path.exists():
            try:
                os.remove(cache_path)
            except OSError:
                pass

        _reburn_clip(db, clip)
    except Exception as exc:  # noqa: BLE001
        clip.render_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Trim render failed: {exc}") from exc

    return TrimRenderResponse(
        clip_id=clip.id,
        trim_start_time=payload.trim_start_time,
        trim_end_time=payload.trim_end_time,
        render_status=clip.render_status,
        preview_url=to_media_url(clip.final_clip_path),
    )


@router.post("/clips/{clip_id}/create-caption", response_model=ClipResponse)
def create_caption(clip_id: str, payload: CreateCaptionRequest, db: Session = Depends(get_db)):
    """
    Manually add a new caption block to a clip. Used both to fill in
    gaps the auto-transcription missed and as the primary way to add
    captions entirely from scratch when a clip has none (e.g. Whisper
    produced no words for this time range).
    """
    clip = _get_clip_or_404(db, clip_id)

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    clip_duration = clip.trim_end_time - clip.trim_start_time
    if payload.end_time > clip_duration + 0.5:
        raise HTTPException(status_code=400, detail="Caption block must fall within the clip's duration")

    new_block = CaptionBlock(
        clip_id=clip.id,
        order_index=len(clip.caption_blocks),
        start_time=payload.start_time,
        end_time=payload.end_time,
        text=payload.text,
    )
    db.add(new_block)
    db.commit()

    _rebuild_caption_indices(clip, db)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)


@router.post("/clips/{clip_id}/delete-caption", response_model=ClipResponse)
def delete_caption(clip_id: str, payload: DeleteCaptionRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    block = db.query(CaptionBlock).filter(CaptionBlock.id == payload.block_id, CaptionBlock.clip_id == clip.id).first()
    if block is None:
        raise HTTPException(status_code=404, detail="Caption block not found")

    db.delete(block)
    db.commit()

    _rebuild_caption_indices(clip, db)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)


@router.post("/clips/{clip_id}/update-caption", response_model=ClipResponse)
def update_caption(clip_id: str, payload: UpdateCaptionRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    block = db.query(CaptionBlock).filter(CaptionBlock.id == payload.block_id, CaptionBlock.clip_id == clip.id).first()
    if block is None:
        raise HTTPException(status_code=404, detail="Caption block not found")

    if payload.text is not None:
        block.text = payload.text
    if payload.start_time is not None:
        block.start_time = payload.start_time
    if payload.end_time is not None:
        block.end_time = payload.end_time

    if block.end_time <= block.start_time:
        raise HTTPException(status_code=400, detail="Caption end_time must be after start_time")

    db.commit()
    _rebuild_caption_indices(clip, db)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)


@router.post("/clips/{clip_id}/split-caption", response_model=ClipResponse)
def split_caption(clip_id: str, payload: SplitCaptionRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    block = db.query(CaptionBlock).filter(CaptionBlock.id == payload.block_id, CaptionBlock.clip_id == clip.id).first()
    if block is None:
        raise HTTPException(status_code=404, detail="Caption block not found")
    if not (block.start_time < payload.split_at_time < block.end_time):
        raise HTTPException(status_code=400, detail="split_at_time must fall strictly within the block")

    first_dict, second_dict = caption_service.split_block(block.to_dict(), payload.split_at_time)

    block.start_time = first_dict["start_time"]
    block.end_time = first_dict["end_time"]
    block.text = first_dict["text"]

    new_block = CaptionBlock(
        clip_id=clip.id,
        order_index=second_dict["order_index"],
        start_time=second_dict["start_time"],
        end_time=second_dict["end_time"],
        text=second_dict["text"],
    )
    db.add(new_block)
    db.commit()

    _rebuild_caption_indices(clip, db)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)


@router.post("/clips/{clip_id}/merge-caption", response_model=ClipResponse)
def merge_caption(clip_id: str, payload: MergeCaptionRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)
    first = db.query(CaptionBlock).filter(CaptionBlock.id == payload.first_block_id, CaptionBlock.clip_id == clip.id).first()
    second = db.query(CaptionBlock).filter(CaptionBlock.id == payload.second_block_id, CaptionBlock.clip_id == clip.id).first()

    if first is None or second is None:
        raise HTTPException(status_code=404, detail="One or both caption blocks not found")
    if first.id == second.id:
        raise HTTPException(status_code=400, detail="Cannot merge a block with itself")

    merged = caption_service.merge_blocks(first.to_dict(), second.to_dict())
    first.start_time = merged["start_time"]
    first.end_time = merged["end_time"]
    first.text = merged["text"]

    db.delete(second)
    db.commit()

    _rebuild_caption_indices(clip, db)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)


@router.post("/clips/{clip_id}/apply-style", response_model=ClipResponse)
def apply_style(clip_id: str, payload: ApplyStyleRequest, db: Session = Depends(get_db)):
    clip = _get_clip_or_404(db, clip_id)

    if payload.custom_style:
        if clip.applied_style and not clip.applied_style.is_preset:
            style = style_service.update_style(db, clip.applied_style, payload.custom_style)
        else:
            data = {"name": payload.custom_style.get("name", f"{clip.title} custom style"), **payload.custom_style}
            style = style_service.create_style(db, data)
        clip.applied_style_id = style.id
    elif payload.style_id:
        style = style_service.get_style(db, payload.style_id)
        if style is None:
            raise HTTPException(status_code=404, detail="Style not found")
        clip.applied_style_id = style.id
    else:
        raise HTTPException(status_code=400, detail="Provide either style_id or custom_style")

    db.commit()
    if style.animation in {"kinetic", "word-pop"}:
        _rebuild_word_accurate_captions(db, clip)
    _reburn_clip(db, clip)

    db.refresh(clip)
    return _clip_to_response(clip)
