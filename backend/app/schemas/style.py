"""
Pydantic schemas for caption style CRUD.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CaptionStyleSchema(BaseModel):
    id: str
    name: str
    is_preset: bool
    font_family: str
    font_size: int
    text_color: str
    highlight_color: str
    outline_color: str
    outline_width: int
    shadow_strength: int
    background_box: bool
    background_opacity: int
    uppercase: bool
    bold: bool
    position: str
    animation: str
    words_per_block: int
    background_color: str
    safe_margins: int


class CreateStyleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    font_family: str = "Inter"
    font_size: int = Field(default=34, ge=12, le=96)
    text_color: str = "#FFFFFF"
    highlight_color: str = "#FFD400"
    outline_color: str = "#000000"
    outline_width: int = Field(default=3, ge=0, le=12)
    shadow_strength: int = Field(default=1, ge=0, le=10)
    background_box: bool = False
    background_opacity: int = Field(default=50, ge=0, le=100)
    uppercase: bool = True
    bold: bool = True
    position: str = Field(default="bottom", pattern="^(top|middle|bottom)$")
    animation: str = Field(default="kinetic", pattern="^(none|fade|pop|bounce|kinetic|word-pop)$")
    words_per_block: int = Field(default=3, ge=1, le=12)
    background_color: str = "#000000"
    safe_margins: int = Field(default=60, ge=0, le=200)


class UpdateStyleRequest(BaseModel):
    name: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = Field(default=None, ge=12, le=96)
    text_color: Optional[str] = None
    highlight_color: Optional[str] = None
    outline_color: Optional[str] = None
    outline_width: Optional[int] = Field(default=None, ge=0, le=12)
    shadow_strength: Optional[int] = Field(default=None, ge=0, le=10)
    background_box: Optional[bool] = None
    background_opacity: Optional[int] = Field(default=None, ge=0, le=100)
    uppercase: Optional[bool] = None
    bold: Optional[bool] = None
    position: Optional[str] = Field(default=None, pattern="^(top|middle|bottom)$")
    animation: Optional[str] = Field(default=None, pattern="^(none|fade|pop|bounce|kinetic|word-pop)$")
    words_per_block: Optional[int] = Field(default=None, ge=1, le=12)
    background_color: Optional[str] = None
    safe_margins: Optional[int] = Field(default=None, ge=0, le=200)
