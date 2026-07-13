"""
transcription_router.py
Picks transcription engine based on config.
"""

from __future__ import annotations

from typing import List

from app.core.config import TRANSCRIPTION_ENGINE
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment


def transcribe(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if TRANSCRIPTION_ENGINE == "whisper":
        if logger:
            logger.info("Transcription engine: Whisper")
        from app.services import transcription_service
        return transcription_service.transcribe_audio(audio_path, logger=logger)

    if logger:
        logger.info("Transcription engine: Groq")

    try:
        from app.services import groq_transcription_service
        return groq_transcription_service.transcribe_audio(audio_path, logger=logger)
    except Exception as exc:
        if logger:
            logger.error(f"Groq transcription failed: {exc}")
        # Do not fall back to Whisper on cloud hosts as it triggers OOM restarts
        raise RuntimeError(
            f"Groq transcription failed: {exc}. Please verify that your GROQ_API_KEY environment variable is valid."
        )
