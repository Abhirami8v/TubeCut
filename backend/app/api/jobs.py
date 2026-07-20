"""
api/jobs.py

POST /generate-clips kicks off the full pipeline as a background task
and returns immediately with a job_id. GET /jobs/{job_id} is polled by
the frontend to drive the step-by-step progress UI and, once complete,
to fetch the generated clip list.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.schemas.job import GenerateClipsRequest, GenerateClipsResponse, JobStatusResponse, JobStepStatus
from app.services import pipeline_service, style_service
from app.utils.file_urls import to_media_url
from app.api.auth_deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["jobs"])

STEP_LABELS = {
    JobStatus.QUEUED: "Queued",
    JobStatus.DOWNLOADING: "Downloading video",
    JobStatus.EXTRACTING_AUDIO: "Extracting audio",
    JobStatus.TRANSCRIBING: "Transcribing speech",
    JobStatus.ANALYZING: "Analyzing for hooks",
    JobStatus.SEGMENTING: "Scoring clips",
    JobStatus.RENDERING_CLIPS: "Rendering clips",
    JobStatus.COMPLETED: "Done",
}


@router.post("/generate-clips", response_model=GenerateClipsResponse)
def generate_clips(
    payload: GenerateClipsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="A video URL is required")

    style_service.seed_preset_styles(db)

    job = Job(
        source_url=payload.url,
        status=JobStatus.QUEUED,
        current_step_label="Queued",
        user_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        pipeline_service.run_pipeline,
        job.id,
        payload.url,
        payload.target_clip_count,
        payload.auto_reframe,
        payload.auto_caption_style_id,
    )

    return GenerateClipsResponse(job_id=job.id, status=job.status.value, message="Clip generation started")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id and job.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You do not have permission to access this job.")

    steps = []
    current_index = Job.STEP_ORDER.index(job.status) if job.status in Job.STEP_ORDER else -1
    for i, step in enumerate(Job.STEP_ORDER):
        if job.status == JobStatus.FAILED:
            state = "failed" if i == max(current_index, 0) else ("done" if i < current_index else "pending")
        elif i < current_index:
            state = "done"
        elif i == current_index:
            state = "done" if job.status == JobStatus.COMPLETED else "active"
        else:
            state = "pending"
        steps.append(JobStepStatus(key=step.value, label=STEP_LABELS[step], state=state))

    clips_payload = []
    if job.status == JobStatus.COMPLETED:
        import time
        timestamp = int(time.time())
        for clip in sorted(job.clips, key=lambda c: c.index_in_job):
            summary = clip.to_summary_dict()
            preview_path = clip.final_clip_path or clip.raw_clip_path
            summary["preview_url"] = f"{to_media_url(preview_path)}?t={timestamp}" if preview_path else None
            summary["download_url"] = f"/clips/{clip.id}/download?t={timestamp}" if clip.final_clip_path else None
            summary["thumbnail_url"] = f"{to_media_url(clip.thumbnail_path)}?t={timestamp}" if clip.thumbnail_path else None
            clips_payload.append(summary)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        progress_percent=job.progress_percent,
        current_step_label=job.current_step_label,
        error_message=job.error_message,
        steps=steps,
        source_title=job.source_title,
        source_duration=job.source_duration,
        clips=clips_payload,
    )
