"""
Authentication and User Settings API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.api.auth_deps import get_current_user, get_current_admin
from app.models.user import User, UserSettings

router = APIRouter(tags=["auth"])


class UserRegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=4)


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    email: str
    is_admin: bool


class UserSettingsSchema(BaseModel):
    default_clip_count: int
    auto_reframe_default: bool
    caption_font_family: str
    caption_font_size: int
    caption_font_weight: str
    caption_text_color: str
    caption_background_color: str
    caption_outline_color: str
    caption_outline_width: int
    caption_shadow_strength: int
    caption_position: str
    caption_animation: str
    caption_safe_margins: int
    caption_words_per_block: int
    caption_background_box: bool
    caption_background_opacity: int
    caption_uppercase: bool
    caption_highlight_color: str


class UserMeResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    settings: UserSettingsSchema


class UserSchema(BaseModel):
    id: str
    email: str
    is_admin: bool
    created_at: str


class UpdateUserSettingsRequest(BaseModel):
    default_clip_count: Optional[int] = Field(default=None, ge=1, le=10)
    auto_reframe_default: Optional[bool] = None
    caption_font_family: Optional[str] = None
    caption_font_size: Optional[int] = Field(default=None, ge=12, le=96)
    caption_font_weight: Optional[str] = None
    caption_text_color: Optional[str] = None
    caption_background_color: Optional[str] = None
    caption_outline_color: Optional[str] = None
    caption_outline_width: Optional[int] = Field(default=None, ge=0, le=12)
    caption_shadow_strength: Optional[int] = Field(default=None, ge=0, le=10)
    caption_position: Optional[str] = None
    caption_animation: Optional[str] = None
    caption_safe_margins: Optional[int] = Field(default=None, ge=0, le=200)
    caption_words_per_block: Optional[int] = Field(default=None, ge=1, le=12)
    caption_background_box: Optional[bool] = None
    caption_background_opacity: Optional[int] = Field(default=None, ge=0, le=100)
    caption_uppercase: Optional[bool] = None
    caption_highlight_color: Optional[str] = None


@router.post("/auth/register", response_model=TokenResponse)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists.",
        )

    # First user is automatically made admin (makes setup and testing extremely easy)
    is_first_user = db.query(User).count() == 0

    new_user = User(
        email=email_clean,
        hashed_password=hash_password(payload.password),
        is_admin=is_first_user,
    )
    db.add(new_user)
    db.flush()

    # Create default settings
    settings = UserSettings(user_id=new_user.id)
    db.add(settings)
    db.commit()

    token = create_access_token({"sub": new_user.id})
    return TokenResponse(token=token, email=new_user.email, is_admin=new_user.is_admin)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email address or password.",
        )

    token = create_access_token({"sub": user.id})
    return TokenResponse(token=token, email=user.email, is_admin=user.is_admin)


@router.get("/auth/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    # Guarantee settings exist
    if not current_user.settings:
        raise HTTPException(status_code=500, detail="User settings configuration missing.")

    s = current_user.settings
    settings_schema = UserSettingsSchema(
        default_clip_count=s.default_clip_count,
        auto_reframe_default=s.auto_reframe_default,
        caption_font_family=s.caption_font_family,
        caption_font_size=s.caption_font_size,
        caption_font_weight=s.caption_font_weight,
        caption_text_color=s.caption_text_color,
        caption_background_color=s.caption_background_color,
        caption_outline_color=s.caption_outline_color,
        caption_outline_width=s.caption_outline_width,
        caption_shadow_strength=s.caption_shadow_strength,
        caption_position=s.caption_position,
        caption_animation=s.caption_animation,
        caption_safe_margins=s.caption_safe_margins,
        caption_words_per_block=s.caption_words_per_block,
        caption_background_box=s.caption_background_box,
        caption_background_opacity=s.caption_background_opacity,
        caption_uppercase=s.caption_uppercase,
        caption_highlight_color=s.caption_highlight_color,
    )

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        is_admin=current_user.is_admin,
        settings=settings_schema,
    )


@router.post("/auth/settings", response_model=UserSettingsSchema)
def update_settings(
    payload: UpdateUserSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = current_user.settings
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.add(s)
        db.flush()

    for field, val in payload.model_dump(exclude_unset=True).items():
        if hasattr(s, field):
            setattr(s, field, val)

    db.commit()
    db.refresh(s)

    return UserSettingsSchema(
        default_clip_count=s.default_clip_count,
        auto_reframe_default=s.auto_reframe_default,
        caption_font_family=s.caption_font_family,
        caption_font_size=s.caption_font_size,
        caption_font_weight=s.caption_font_weight,
        caption_text_color=s.caption_text_color,
        caption_background_color=s.caption_background_color,
        caption_outline_color=s.caption_outline_color,
        caption_outline_width=s.caption_outline_width,
        caption_shadow_strength=s.caption_shadow_strength,
        caption_position=s.caption_position,
        caption_animation=s.caption_animation,
        caption_safe_margins=s.caption_safe_margins,
        caption_words_per_block=s.caption_words_per_block,
        caption_background_box=s.caption_background_box,
        caption_background_opacity=s.caption_background_opacity,
        caption_uppercase=s.caption_uppercase,
        caption_highlight_color=s.caption_highlight_color,
    )


# --- Admin Panel Endpoints ---

@router.get("/admin/users", response_model=List[UserSchema])
def list_users(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    res = []
    for u in users:
        res.append(UserSchema(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            created_at=u.created_at.isoformat() if u.created_at else "",
        ))
    return res


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    db.delete(user)
    db.commit()
    return {"deleted": True, "user_id": user_id}


@router.post("/admin/users/{user_id}/toggle-admin")
def toggle_admin(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own admin privileges.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    user.is_admin = not user.is_admin
    db.commit()
    return {"success": True, "user_id": user_id, "is_admin": user.is_admin}
