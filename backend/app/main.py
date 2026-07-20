"""
main.py

FastAPI application entrypoint. Wires up the database, mounts the
storage directory for static media serving, registers all routers, and
configures CORS for the Vite dev server frontend.
"""

from __future__ import annotations

import os

# Prepend standard macOS package managers paths so ffmpeg/ffprobe can always be found
for path in ["/opt/homebrew/bin", "/usr/local/bin"]:
    if path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{path}{os.pathsep}{os.environ.get('PATH', '')}"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, clips, jobs, library, styles
from app.core.config import COOKIES_FILE, GEMINI_API_KEY, STORAGE_DIR
from app.core.database import init_db
from app.services.cleanup_service import cleanup_old_files

app = FastAPI(
    title="TubeCut API",
    description="AI-powered video clipping, captioning, and short-form editing backend.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(STORAGE_DIR)), name="media")

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(clips.router)
app.include_router(styles.router)
app.include_router(library.router)


@app.on_event("startup")
def on_startup():
    """Create all database tables on every boot.

    Render uses an ephemeral filesystem — the SQLite file is wiped on
    every deploy/restart, so we must recreate it each time.
    """
    init_db()
    print("[startup] Database tables created/verified.")
    try:
        cleanup_old_files()
    except Exception as e:
        print(f"[startup] Cleanup failed: {e}")




@app.get("/")
def root():
    return {"status": "ok", "service": "TubeCut API", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/deployment")
def deployment_health():
    """Quick checklist for Render/Vercel deploy issues (no secrets exposed)."""
    import shutil
    from pathlib import Path

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    cookies_path = Path(COOKIES_FILE) if COOKIES_FILE else None

    checks = {
        "ffmpeg_installed": ffmpeg_path is not None,
        "ffprobe_installed": ffprobe_path is not None,
        "cookies_configured": bool(cookies_path and cookies_path.is_file()),
        "gemini_key_configured": bool(GEMINI_API_KEY),
        "youtube_download_ready": bool(
            ffmpeg_path and cookies_path and cookies_path.is_file()
        ),
    }
    checks["status"] = "ready" if checks["youtube_download_ready"] and checks["gemini_key_configured"] else "misconfigured"
    return checks
