"""
api/library.py

Powers the "My Clips" sidebar page: a flat, most-recent-first list of
every clip ever generated, across all jobs, with enough summary data
for the dashboard grid (no need to join through jobs client-side).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.clip import Clip
from app.models.job import Job
from app.schemas.clip import ClipResponse
from app.utils.file_urls import to_media_url

router = APIRouter(tags=["library"])


@router.get("/library/clips", response_model=list[ClipResponse])
def list_all_clips(db: Session = Depends(get_db)):
    clips = (
        db.query(Clip)
        .options(joinedload(Clip.job), joinedload(Clip.caption_blocks))
        .join(Job)
        .order_by(Job.created_at.desc(), Clip.index_in_job.asc())
        .all()
    )

    results = []
    for clip in clips:
        summary = clip.to_summary_dict()
        results.append(
            ClipResponse(
                **summary,
                preview_url=to_media_url(clip.final_clip_path or clip.reframed_clip_path or clip.raw_clip_path),
                final_url=to_media_url(clip.final_clip_path),
                download_url=f"/clips/{clip.id}/download" if clip.final_clip_path else None,
                thumbnail_url=to_media_url(clip.thumbnail_path),
                caption_blocks=[b.to_dict() for b in sorted(clip.caption_blocks, key=lambda b: b.order_index)],
            )
        )
    return results
