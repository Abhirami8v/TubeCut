"""
Application-wide configuration.

All filesystem paths, tunable pipeline constants, and environment-derived
settings live here so that no service has to hardcode a path or guess
where to read/write a file.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BACKEND_DIR / "storage"

DOWNLOADS_DIR = STORAGE_DIR / "downloads"
AUDIO_DIR = STORAGE_DIR / "audio"
CLIPS_DIR = STORAGE_DIR / "clips"
CAPTIONS_DIR = STORAGE_DIR / "captions"
FINAL_DIR = STORAGE_DIR / "final"
THUMBNAILS_DIR = STORAGE_DIR / "thumbnails"

for _dir in (
    DOWNLOADS_DIR,
    AUDIO_DIR,
    CLIPS_DIR,
    CAPTIONS_DIR,
    FINAL_DIR,
    THUMBNAILS_DIR,
):
    _dir.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'tubecut.db'}")

# ---------------------------------------------------------------------------
# Server / CORS
# ---------------------------------------------------------------------------

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# AI / external services
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY", "")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ---------------------------------------------------------------------------
# Pipeline tuning
# ---------------------------------------------------------------------------

MIN_CLIP_SECONDS = 15
MAX_CLIP_SECONDS = 90
TARGET_CLIP_COUNT = 3

# Auto vertical reframe
REFRAME_TARGET_WIDTH = 1080
REFRAME_TARGET_HEIGHT = 1920
REFRAME_DETECT_EVERY_N_FRAMES = 10
REFRAME_SMOOTHING_ALPHA = 0.15  # exponential smoothing factor for camera pan
YOLO_WEIGHTS_PATH = os.getenv("YOLO_WEIGHTS_PATH", str(BACKEND_DIR / "yolov8n.pt"))
YOLO_CONFIDENCE_THRESHOLD = 0.5

# Caption defaults
DEFAULT_CAPTION_CHUNK_SIZE = 3  # words per caption block when auto-generating
