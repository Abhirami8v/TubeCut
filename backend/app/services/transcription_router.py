"""
transcription_router.py — Gemini only.
"""
from __future__ import annotations

from typing import List

from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment


def transcribe(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if logger:
        logger.info("Transcription engine: Gemini")

    from app.services import gemini_transcription_service
    return gemini_transcription_service.transcribe_audio(audio_path, logger=logger)