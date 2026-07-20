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
from app.api.auth_deps import get_current_user
from app.models.user import User
from app.models.caption import CaptionStyle

router = APIRouter(prefix="/styles", tags=["styles"])


@router.get("", response_model=list[CaptionStyleSchema])
def list_styles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    style_service.seed_preset_styles(db)
    # Filter to return presets OR user-specific custom styles
    styles = db.query(CaptionStyle).filter(
        (CaptionStyle.is_preset == True) | (CaptionStyle.user_id == current_user.id)
    ).order_by(CaptionStyle.is_preset.desc(), CaptionStyle.name.asc()).all()
    return [CaptionStyleSchema(**s.to_dict()) for s in styles]


@router.post("", response_model=CaptionStyleSchema)
def create_style(
    payload: CreateStyleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["user_id"] = current_user.id
    style = style_service.create_style(db, data)
    return CaptionStyleSchema(**style.to_dict())


@router.patch("/{style_id}", response_model=CaptionStyleSchema)
def update_style(
    style_id: str,
    payload: UpdateStyleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    style = style_service.get_style(db, style_id)
    if style is None:
        raise HTTPException(status_code=404, detail="Style not found")
    if style.is_preset:
        raise HTTPException(status_code=400, detail="Built-in presets cannot be modified; duplicate it instead")
    if style.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this style.")

    updated = style_service.update_style(db, style, payload.model_dump(exclude_unset=True))
    return CaptionStyleSchema(**updated.to_dict())


@router.delete("/{style_id}")
def delete_style(
    style_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    style = style_service.get_style(db, style_id)
    if style is None:
        raise HTTPException(status_code=404, detail="Style not found")
    if style.is_preset:
        raise HTTPException(status_code=400, detail="Built-in presets cannot be deleted")
    if style.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this style.")

    style_service.delete_style(db, style)
    return {"deleted": True, "style_id": style_id}
