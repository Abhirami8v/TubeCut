"""
transcription_router.py
AssemblyAI for transcription, Groq for analysis.
"""
from __future__ import annotations

from typing import List

from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment


def transcribe(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if logger:
        logger.info("Transcription engine: AssemblyAI")

    from app.services import assemblyai_transcription_service
    return assemblyai_transcription_service.transcribe_audio(audio_path, logger=logger)