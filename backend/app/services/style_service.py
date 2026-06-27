"""
style_service.py

Manages CaptionStyle records: seeding the five built-in presets on
first boot, and CRUD for user-created custom styles. Kept separate from
caption_service.py because styles are a reusable, independently-listed
resource (the "Caption Styles" sidebar section), while caption_service
is about the per-clip block content itself.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.caption import PRESET_STYLES, CaptionStyle


def seed_preset_styles(db: Session) -> None:
    """Insert presets and keep existing built-in presets in sync."""
    existing = {
        style.name: style
        for style in db.query(CaptionStyle).filter(CaptionStyle.is_preset.is_(True)).all()
    }

    for preset in PRESET_STYLES:
        style = existing.get(preset["name"])
        if style is None:
            db.add(CaptionStyle(**preset))
            continue
        for key, value in preset.items():
            setattr(style, key, value)

    db.commit()


def list_styles(db: Session) -> list[CaptionStyle]:
    return db.query(CaptionStyle).order_by(CaptionStyle.is_preset.desc(), CaptionStyle.name.asc()).all()


def get_style(db: Session, style_id: str) -> CaptionStyle | None:
    return db.query(CaptionStyle).filter(CaptionStyle.id == style_id).first()


def create_style(db: Session, data: dict) -> CaptionStyle:
    style = CaptionStyle(is_preset=False, **data)
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


def update_style(db: Session, style: CaptionStyle, data: dict) -> CaptionStyle:
    for key, value in data.items():
        if value is not None and hasattr(style, key):
            setattr(style, key, value)
    db.commit()
    db.refresh(style)
    return style


def delete_style(db: Session, style: CaptionStyle) -> None:
    db.delete(style)
    db.commit()


def get_default_style(db: Session) -> CaptionStyle:
    """Return the one-word kinetic preset as the system default."""
    default = db.query(CaptionStyle).filter(CaptionStyle.name == "TikTok Viral").first()
    if default:
        return default
    any_style = db.query(CaptionStyle).first()
    if any_style:
        return any_style
    fallback_data = next(p for p in PRESET_STYLES if p["name"] == "TikTok Viral")
    style = CaptionStyle(**fallback_data)
    db.add(style)
    db.commit()
    db.refresh(style)
    return style
