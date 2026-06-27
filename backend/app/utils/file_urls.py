"""
file_urls.py

Converts absolute filesystem paths under STORAGE_DIR into URLs the
frontend can fetch, given the backend serves STORAGE_DIR at /media via
StaticFiles (see app/main.py).
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import PUBLIC_BASE_URL, STORAGE_DIR


def to_media_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    try:
        relative = Path(file_path).resolve().relative_to(STORAGE_DIR.resolve())
    except ValueError:
        return None
    return f"{PUBLIC_BASE_URL}/media/{relative.as_posix()}"
