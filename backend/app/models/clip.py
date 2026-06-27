"""
Clip model: one row per generated short clip belonging to a Job.

Stores the clip's time range within the source video, its transcript
text, the AI-derived scores (confidence + hook score), render state for
the underlying mp4 file, the current crop/trim window, and which caption
style is currently applied.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)

    index_in_job = Column(Integer, nullable=False, default=0)
    title = Column(String, nullable=False, default="Untitled Clip")

    # Time range within the ORIGINAL source video.
    source_start_time = Column(Float, nullable=False)
    source_end_time = Column(Float, nullable=False)

    # Current trim window, relative to the original source video. Starts
    # out equal to source_start_time/source_end_time and is narrowed by
    # the trim endpoint without ever exceeding the original bounds.
    trim_start_time = Column(Float, nullable=False)
    trim_end_time = Column(Float, nullable=False)

    transcript_text = Column(Text, nullable=False, default="")

    confidence_score = Column(Float, nullable=False, default=0.0)  # 0-100, AI confidence in clip-worthiness
    hook_score = Column(Float, nullable=False, default=0.0)        # 0-100, heuristic hook strength
    viral_score = Column(Float, nullable=False, default=0.0)       # 0-100, blended Gemini + heuristic
    ai_reason = Column(Text, nullable=True)

    # Rendering / file state
    render_status = Column(String, nullable=False, default="pending")  # pending|rendering|ready|failed
    raw_clip_path = Column(String, nullable=True)        # trimmed, uncaptioned, unreframed
    reframed_clip_path = Column(String, nullable=True)   # vertical 9:16 version (no captions)
    final_clip_path = Column(String, nullable=True)      # final render with captions burned in
    thumbnail_path = Column(String, nullable=True)

    is_vertical = Column(Boolean, nullable=False, default=False)
    applied_style_id = Column(String, ForeignKey("caption_styles.id"), nullable=True)

    job = relationship("Job", back_populates="clips")
    caption_blocks = relationship(
        "CaptionBlock",
        back_populates="clip",
        cascade="all, delete-orphan",
        order_by="CaptionBlock.order_index",
    )
    applied_style = relationship("CaptionStyle")

    def to_summary_dict(self) -> dict:
        return {
            "clip_id": self.id,
            "index": self.index_in_job,
            "title": self.title,
            "start_time": self.source_start_time,
            "end_time": self.source_end_time,
            "trim_start_time": self.trim_start_time,
            "trim_end_time": self.trim_end_time,
            "duration": round(self.trim_end_time - self.trim_start_time, 2),
            "transcript_text": self.transcript_text,
            "confidence_score": self.confidence_score,
            "hook_score": self.hook_score,
            "viral_score": self.viral_score,
            "ai_reason": self.ai_reason,
            "render_status": self.render_status,
            "is_vertical": self.is_vertical,
            "applied_style_id": self.applied_style_id,
        }
