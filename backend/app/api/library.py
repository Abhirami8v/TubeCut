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
from app.api.auth_deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["library"])


@router.get("/library/clips", response_model=list[ClipResponse])
def list_all_clips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Clip)
        .options(joinedload(Clip.job), joinedload(Clip.caption_blocks))
        .join(Job)
    )

    if not current_user.is_admin:
        query = query.filter(Job.user_id == current_user.id)

    clips = query.order_by(Job.created_at.desc(), Clip.index_in_job.asc()).all()

    import time
    timestamp = int(time.time())

    results = []
    for clip in clips:
        summary = clip.to_summary_dict()
        preview_path = clip.final_clip_path or clip.reframed_clip_path or clip.raw_clip_path
        preview_url = f"{to_media_url(preview_path)}?t={timestamp}" if preview_path else None
        final_url = f"{to_media_url(clip.final_clip_path)}?t={timestamp}" if clip.final_clip_path else None
        download_url = f"/clips/{clip.id}/download?t={timestamp}" if clip.final_clip_path else None
        thumbnail_url = f"{to_media_url(clip.thumbnail_path)}?t={timestamp}" if clip.thumbnail_path else None

        results.append(
            ClipResponse(
                **summary,
                preview_url=preview_url,
                final_url=final_url,
                download_url=download_url,
                thumbnail_url=thumbnail_url,
                caption_blocks=[b.to_dict() for b in sorted(clip.caption_blocks, key=lambda b: b.order_index)],
            )
        )
    return results
