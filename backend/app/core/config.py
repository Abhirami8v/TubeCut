from __future__ import annotations

import os
import platform
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
FRAMES_DIR = STORAGE_DIR / "frames"
LOGS_DIR = STORAGE_DIR / "logs"

for _dir in (
    DOWNLOADS_DIR,
    AUDIO_DIR,
    CLIPS_DIR,
    CAPTIONS_DIR,
    FINAL_DIR,
    THUMBNAILS_DIR,
    FRAMES_DIR,
    LOGS_DIR,
):
    _dir.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'tubecut.db'}")

# ---------------------------------------------------------------------------
# Server / CORS
# ---------------------------------------------------------------------------

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL","https://tubecut-production.up.railway.app")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://tube-cut.vercel.app",
    ).split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# AI / external services
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")



GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TRANSCRIPTION_ENGINE = os.getenv("TRANSCRIPTION_ENGINE", "groq").lower()
YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY", "")
PROXY_URL = os.getenv("PROXY_URL", "")
# yt-dlp configurations to bypass cloud host IP blocking
YT_DLP_COOKIES_CONTENT = os.getenv("YT_DLP_COOKIES_CONTENT", "")
YT_DLP_COOKIES_PATH = os.getenv("YT_DLP_COOKIES_PATH", "")
YT_DLP_PROXY = os.getenv("YT_DLP_PROXY", "") or os.getenv("PROXY_URL", "")
YT_DLP_PO_TOKEN = os.getenv("YT_DLP_PO_TOKEN", "")

COOKIES_FILE = None
if YT_DLP_COOKIES_CONTENT:
    cookies_file_path = STORAGE_DIR / "cookies.txt"
    try:
        # Auto-repair spaces to tabs if copy-pasted incorrectly
        lines = []
        for line in YT_DLP_COOKIES_CONTENT.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                lines.append(line)
                continue
            
            parts = stripped.split()
            if len(parts) >= 7:
                domain = parts[0]
                flag = parts[1]
                path = parts[2]
                secure = parts[3]
                expiration = parts[4]
                name = parts[5]
                value = " ".join(parts[6:])
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}")
            else:
                lines.append(line)
                
        standardized_content = "\n".join(lines)
        cookies_file_path.write_text(standardized_content, encoding="utf-8")
        COOKIES_FILE = str(cookies_file_path)
    except Exception as e:
        print(f"Failed to write YT_DLP_COOKIES_CONTENT to file: {e}")
elif YT_DLP_COOKIES_PATH:
    COOKIES_FILE = YT_DLP_COOKIES_PATH
else:
    # Auto-detect cookies.txt in storage/ or backend root
    local_cookies = STORAGE_DIR / "cookies.txt"
    if local_cookies.exists():
        COOKIES_FILE = str(local_cookies)
    else:
        root_cookies = BACKEND_DIR / "cookies.txt"
        if root_cookies.exists():
            COOKIES_FILE = str(root_cookies)

TRANSCRIPTION_ENGINE = os.getenv("TRANSCRIPTION_ENGINE", "gemini").lower()

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ---------------------------------------------------------------------------
# Pipeline tuning
# ---------------------------------------------------------------------------

MIN_CLIP_SECONDS = 15
MAX_CLIP_SECONDS = 90
TARGET_CLIP_COUNT = 3

# Auto vertical reframe
REFRAME_TARGET_WIDTH = int(os.getenv("REFRAME_TARGET_WIDTH", "720"))
MAX_REFRAME_KEYFRAMES = 10
REFRAME_TARGET_HEIGHT = int(os.getenv("REFRAME_TARGET_HEIGHT", "1280"))
REFRAME_DETECT_EVERY_N_FRAMES = 20
REFRAME_SMOOTHING_ALPHA = 0.15
YOLO_WEIGHTS_PATH = os.getenv("YOLO_WEIGHTS_PATH", str(BACKEND_DIR / "yolov8n.pt"))
YOLO_CONFIDENCE_THRESHOLD = 0.5
YOLO_DOWNSCALE_WIDTH = 640

# Caption rendering mode: "ass" (fast) or "kinetic" (animated but slower)
CAPTION_RENDER_MODE = os.getenv("CAPTION_RENDER_MODE", "ass").lower()

DEFAULT_CAPTION_CHUNK_SIZE = 3
DEFAULT_WORDS_PER_KINETIC_GROUP = 3

# ---------------------------------------------------------------------------
# Font resolution (cross-platform)
# ---------------------------------------------------------------------------

_SYSTEM = platform.system()

if _SYSTEM == "Windows":
    _FONT_CANDIDATES = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\Arial Bold.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
elif _SYSTEM == "Darwin":
    _FONT_CANDIDATES = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
else:
    # Linux (Render runs Linux)
    _FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]

FONT_CANDIDATES = [p for p in _FONT_CANDIDATES if os.path.exists(p)]
FALLBACK_FONT_PATH = os.getenv(
    "FALLBACK_FONT_PATH",
    FONT_CANDIDATES[0] if FONT_CANDIDATES else ""
)

# ---------------------------------------------------------------------------
# Performance / concurrency
# ---------------------------------------------------------------------------

MAX_PARALLEL_CLIP_RENDERS = int(os.getenv("MAX_PARALLEL_CLIP_RENDERS", "1"))

FAST_ENCODE_PRESET = os.getenv("FAST_ENCODE_PRESET", "ultrafast")
FINAL_ENCODE_PRESET = os.getenv("FINAL_ENCODE_PRESET", "veryfast")

VERBOSE_PIPELINE_LOGGING = os.getenv("VERBOSE_PIPELINE_LOGGING", "true").lower() == "true"