"""
Caption-related models.

CaptionBlock: a single editable caption "block" belonging to a clip (the
unit the caption timeline editor operates on -- supports split/merge/
retime/edit-text).

CaptionStyle: a reusable visual style (font, color, outline, animation,
etc.) that can be one of the built-in presets ("TikTok Viral", "YouTube
Shorts Pro", ...) or a custom style created/edited by the user. Applying
a style to a clip just sets Clip.applied_style_id and triggers a re-burn.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CaptionBlock(Base):
    __tablename__ = "caption_blocks"

    id = Column(String, primary_key=True, default=_uuid)
    clip_id = Column(String, ForeignKey("clips.id"), nullable=False, index=True)

    order_index = Column(Integer, nullable=False, default=0)
    start_time = Column(Float, nullable=False)  # seconds, relative to clip start
    end_time = Column(Float, nullable=False)
    text = Column(String, nullable=False, default="")

    clip = relationship("Clip", back_populates="caption_blocks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_index": self.order_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
        }


class CaptionStyle(Base):
    __tablename__ = "caption_styles"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    is_preset = Column(Boolean, nullable=False, default=False)

    font_family = Column(String, nullable=False, default="Arial Black")
    font_size = Column(Integer, nullable=False, default=34)
    text_color = Column(String, nullable=False, default="#FFFFFF")       # hex
    highlight_color = Column(String, nullable=False, default="#39E75F")  # active-word highlight, hex
    outline_color = Column(String, nullable=False, default="#000000")
    outline_width = Column(Integer, nullable=False, default=3)
    shadow_strength = Column(Integer, nullable=False, default=0)  # 0-10
    background_box = Column(Boolean, nullable=False, default=False)
    background_opacity = Column(Integer, nullable=False, default=60)  # 0-100
    uppercase = Column(Boolean, nullable=False, default=True)
    bold = Column(Boolean, nullable=False, default=True)
    position = Column(String, nullable=False, default="bottom")  # top|middle|bottom
    animation = Column(String, nullable=False, default="pop")    # none|fade|pop|bounce
    words_per_block = Column(Integer, nullable=False, default=3)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "is_preset": self.is_preset,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "text_color": self.text_color,
            "highlight_color": self.highlight_color,
            "outline_color": self.outline_color,
            "outline_width": self.outline_width,
            "shadow_strength": self.shadow_strength,
            "background_box": self.background_box,
            "background_opacity": self.background_opacity,
            "uppercase": self.uppercase,
            "bold": self.bold,
            "position": self.position,
            "animation": self.animation,
            "words_per_block": self.words_per_block,
        }


PRESET_STYLES = [
    {
        "name": "TikTok Viral",
        "is_preset": True,
        "font_family": "Arial Black",
        "font_size": 46,
        "text_color": "#FFFFFF",
        "highlight_color": "#FFD400",
        "outline_color": "#000000",
        "outline_width": 4,
        "shadow_strength": 3,
        "background_box": False,
        "background_opacity": 0,
        "uppercase": True,
        "bold": True,
        "position": "middle",
        "animation": "kinetic",
        "words_per_block": 1,
    },
    {
        "name": "YouTube Shorts Pro",
        "is_preset": True,
        "font_family": "Impact",
        "font_size": 40,
        "text_color": "#FFFFFF",
        "highlight_color": "#3EA6FF",
        "outline_color": "#000000",
        "outline_width": 3,
        "shadow_strength": 2,
        "background_box": True,
        "background_opacity": 45,
        "uppercase": False,
        "bold": True,
        "position": "bottom",
        "animation": "word-pop",
        "words_per_block": 1,
    },
    {
        "name": "Podcast Clean",
        "is_preset": True,
        "font_family": "Avenir Next",
        "font_size": 32,
        "text_color": "#F5F5F5",
        "highlight_color": "#F5F5F5",
        "outline_color": "#000000",
        "outline_width": 1,
        "shadow_strength": 1,
        "background_box": True,
        "background_opacity": 55,
        "uppercase": False,
        "bold": False,
        "position": "bottom",
        "animation": "none",
        "words_per_block": 6,
    },
    {
        "name": "MrBeast Style Bold",
        "is_preset": True,
        "font_family": "Arial Rounded MT Bold",
        "font_size": 54,
        "text_color": "#FFFFFF",
        "highlight_color": "#FF2D2D",
        "outline_color": "#000000",
        "outline_width": 6,
        "shadow_strength": 4,
        "background_box": False,
        "background_opacity": 0,
        "uppercase": True,
        "bold": True,
        "position": "middle",
        "animation": "kinetic",
        "words_per_block": 1,
    },
    {
        "name": "Minimal Subtitles",
        "is_preset": True,
        "font_family": "Helvetica Neue",
        "font_size": 28,
        "text_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 1,
        "shadow_strength": 0,
        "background_box": False,
        "background_opacity": 0,
        "uppercase": False,
        "bold": False,
        "position": "bottom",
        "animation": "none",
        "words_per_block": 8,
    },
]
