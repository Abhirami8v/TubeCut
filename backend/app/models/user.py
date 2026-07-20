"""
User and UserSettings models.
"""

from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    styles = relationship("CaptionStyle", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    default_clip_count = Column(Integer, nullable=False, default=3)
    auto_reframe_default = Column(Boolean, nullable=False, default=True)

    # Caption style defaults
    caption_font_family = Column(String, nullable=False, default="Arial Black")
    caption_font_size = Column(Integer, nullable=False, default=34)
    caption_font_weight = Column(String, nullable=False, default="bold")
    caption_text_color = Column(String, nullable=False, default="#FFFFFF")
    caption_background_color = Column(String, nullable=False, default="#000000")
    caption_outline_color = Column(String, nullable=False, default="#000000")
    caption_outline_width = Column(Integer, nullable=False, default=3)
    caption_shadow_strength = Column(Integer, nullable=False, default=0)
    caption_position = Column(String, nullable=False, default="bottom")
    caption_animation = Column(String, nullable=False, default="pop")
    caption_safe_margins = Column(Integer, nullable=False, default=60)
    caption_words_per_block = Column(Integer, nullable=False, default=3)
    caption_background_box = Column(Boolean, nullable=False, default=False)
    caption_background_opacity = Column(Integer, nullable=False, default=60)
    caption_uppercase = Column(Boolean, nullable=False, default=True)
    caption_highlight_color = Column(String, nullable=False, default="#39E75F")

    user = relationship("User", back_populates="settings")
