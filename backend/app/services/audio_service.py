"""
audio_service.py

Extracts a mono, 16kHz PCM WAV track from a source video for downstream
transcription. Whisper-family models expect this exact format, so the
ffmpeg flags below are intentionally fixed rather than configurable.
"""

from __future__ import annotations

import subprocess
import uuid

from app.core.config import AUDIO_DIR


def extract_audio(video_path: str, job_id: str | None = None) -> str:
    """
    Extract audio from `video_path` to a 16kHz mono WAV file and return
    its path. Each call gets a unique filename (keyed by job_id when
    provided) so concurrent jobs never clobber each other's audio.
    """
    suffix = job_id or uuid.uuid4().hex[:8]
    audio_path = AUDIO_DIR / f"audio_{suffix}.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]

    subprocess.run(command, check=True, capture_output=True)

    return str(audio_path)
