"""
Job model: one row per "paste a link and generate clips" request.

A Job tracks the long-running pipeline (download -> extract audio ->
transcribe -> analyze -> segment -> render) and exposes a `status` and
`progress` that the frontend polls to drive the step-by-step loading UI.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    SEGMENTING = "segmenting"
    RENDERING_CLIPS = "rendering_clips"
    COMPLETED = "completed"
    FAILED = "failed"


def _uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    source_url = Column(String, nullable=False)
    source_title = Column(String, nullable=True)
    source_duration = Column(Float, nullable=True)
    source_video_path = Column(String, nullable=True)
    source_audio_path = Column(String, nullable=True)

    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress_percent = Column(Float, default=0.0, nullable=False)
    current_step_label = Column(String, default="Queued", nullable=False)
    error_message = Column(Text, nullable=True)

    transcript_json = Column(Text, nullable=True)  # full transcript, JSON-encoded

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="jobs")
    clips = relationship("Clip", back_populates="job", cascade="all, delete-orphan")

    # Ordered list of pipeline steps used to render the step-by-step UI.
    STEP_ORDER = [
        JobStatus.QUEUED,
        JobStatus.DOWNLOADING,
        JobStatus.EXTRACTING_AUDIO,
        JobStatus.TRANSCRIBING,
        JobStatus.ANALYZING,
        JobStatus.SEGMENTING,
        JobStatus.RENDERING_CLIPS,
        JobStatus.COMPLETED,
    ]
