"""
Pydantic schemas for the job/generation endpoints.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GenerateClipsRequest(BaseModel):
    url: str = Field(..., description="YouTube or direct video URL to process")
    target_clip_count: Optional[int] = Field(
        default=None, ge=1, le=10, description="Override the number of clips to generate"
    )
    auto_reframe: bool = Field(
        default=True, description="Automatically reframe clips to vertical 9:16 using face/person tracking"
    )
    auto_caption_style_id: Optional[str] = Field(
        default=None, description="Caption style ID to auto-apply to all generated clips"
    )


class GenerateClipsResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStepStatus(BaseModel):
    key: str
    label: str
    state: str  # pending | active | done | failed


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: float
    current_step_label: str
    error_message: Optional[str] = None
    steps: List[JobStepStatus]
    source_title: Optional[str] = None
    source_duration: Optional[float] = None
    clips: List[dict] = []
