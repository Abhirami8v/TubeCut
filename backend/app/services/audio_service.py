"""
audio_service.py
Extracts audio from video, compressed to mp3 to stay under Groq's 25MB limit.
"""

from __future__ import annotations

import os
import subprocess
import uuid

from app.core.config import AUDIO_DIR


def extract_audio(video_path: str, job_id: str | None = None) -> str:
    suffix     = job_id or uuid.uuid4().hex[:8]
    audio_path = AUDIO_DIR / f"audio_{suffix}.mp3"

    command = [
        "ffmpeg",
        "-y",
        "-i",    video_path,
        "-vn",                  # no video
        "-ar",   "16000",       # 16kHz — Whisper optimal
        "-ac",   "1",           # mono
        "-b:a",  "32k",         # 32kbps — keeps file tiny, fine for speech
        str(audio_path),
    ]

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr}")

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"[audio_service] Extracted audio: {audio_path} ({file_size_mb:.1f} MB)")

    # Warn if still over Groq's limit
    if file_size_mb > 24:
        print(f"[audio_service] WARNING: audio is {file_size_mb:.1f}MB — over Groq's 25MB limit, transcription may fail")

    return str(audio_path)