"""
Pydantic schemas for clip-level endpoints: detail responses, trimming,
caption editing (update/split/merge), and style application.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ClipResponse(BaseModel):
    clip_id: str
    index: int
    title: str
    start_time: float
    end_time: float
    trim_start_time: float
    trim_end_time: float
    duration: float
    transcript_text: str
    confidence_score: float
    hook_score: float
    viral_score: float
    ai_reason: Optional[str] = None
    render_status: str
    is_vertical: bool
    applied_style_id: Optional[str] = None
    preview_url: Optional[str] = None
    final_url: Optional[str] = None
    download_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    caption_blocks: List[dict] = []


class TrimClipRequest(BaseModel):
    trim_start_time: float = Field(..., ge=0, description="New trim start, seconds, relative to original clip start")
    trim_end_time: float = Field(..., gt=0, description="New trim end, seconds, relative to original clip start")


class UpdateCaptionRequest(BaseModel):
    block_id: str
    text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class SplitCaptionRequest(BaseModel):
    block_id: str
    split_at_time: float = Field(..., description="Absolute time within the clip to split the block at")


class MergeCaptionRequest(BaseModel):
    first_block_id: str
    second_block_id: str


class CreateCaptionRequest(BaseModel):
    start_time: float = Field(..., ge=0, description="Start time, seconds, relative to clip start")
    end_time: float = Field(..., gt=0, description="End time, seconds, relative to clip start")
    text: str = Field(default="New caption", description="Initial caption text")


class DeleteCaptionRequest(BaseModel):
    block_id: str


class ApplyStyleRequest(BaseModel):
    style_id: Optional[str] = Field(default=None, description="Existing style/preset ID to apply")
    custom_style: Optional[dict] = Field(
        default=None, description="Inline style overrides; creates/updates a custom style for this clip"
    )


class TrimRenderResponse(BaseModel):
    clip_id: str
    trim_start_time: float
    trim_end_time: float
    render_status: str
    preview_url: Optional[str] = None
