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

from app.api import clips, jobs, library, styles
from app.core.config import CORS_ORIGINS, STORAGE_DIR
from app.core.database import init_db

app = FastAPI(
    title="TubeCut API",
    description="AI-powered video clipping, captioning, and short-form editing backend.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(STORAGE_DIR)), name="media")

app.include_router(jobs.router)
app.include_router(clips.router)
app.include_router(styles.router)
app.include_router(library.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    try:
        from app.utils.download_fonts import download_and_install_fonts
        download_and_install_fonts()
    except Exception as e:
        print(f"[main] Failed to run font downloading routine: {e}")


@app.get("/")
def root():
    return {"status": "ok", "service": "TubeCut API", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
