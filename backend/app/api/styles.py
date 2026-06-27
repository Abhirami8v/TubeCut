"""
api/styles.py

CRUD for caption styles. GET /styles returns the 5 built-in presets
plus any custom styles the user has created, for the "Caption Styles"
sidebar page and the style picker inside the clip editor.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.style import CaptionStyleSchema, CreateStyleRequest, UpdateStyleRequest
from app.services import style_service

router = APIRouter(prefix="/styles", tags=["styles"])


@router.get("", response_model=list[CaptionStyleSchema])
def list_styles(db: Session = Depends(get_db)):
    style_service.seed_preset_styles(db)
    styles = style_service.list_styles(db)
    return [CaptionStyleSchema(**s.to_dict()) for s in styles]


@router.post("", response_model=CaptionStyleSchema)
def create_style(payload: CreateStyleRequest, db: Session = Depends(get_db)):
    style = style_service.create_style(db, payload.model_dump())
    return CaptionStyleSchema(**style.to_dict())


@router.patch("/{style_id}", response_model=CaptionStyleSchema)
def update_style(style_id: str, payload: UpdateStyleRequest, db: Session = Depends(get_db)):
    style = style_service.get_style(db, style_id)
    if style is None:
        raise HTTPException(status_code=404, detail="Style not found")
    if style.is_preset:
        raise HTTPException(status_code=400, detail="Built-in presets cannot be modified; duplicate it instead")

    updated = style_service.update_style(db, style, payload.model_dump(exclude_unset=True))
    return CaptionStyleSchema(**updated.to_dict())


@router.delete("/{style_id}")
def delete_style(style_id: str, db: Session = Depends(get_db)):
    style = style_service.get_style(db, style_id)
    if style is None:
        raise HTTPException(status_code=404, detail="Style not found")
    if style.is_preset:
        raise HTTPException(status_code=400, detail="Built-in presets cannot be deleted")

    style_service.delete_style(db, style)
    return {"deleted": True, "style_id": style_id}
