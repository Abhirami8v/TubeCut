"""
transcription_service.py
Transcribes audio using Groq Whisper API (whisper-large-v3-turbo).
Also re-exports transcript utility functions for pipeline compatibility.
"""

from __future__ import annotations

from typing import List

from app.core.logging_utils import JobLogger
from app.services.gemini_transcription_service import transcribe_audio
from app.services.transcript_utils import (
    TranscriptSegment,
    WordTimestamp,
    flatten_words,
    text_in_range,
    words_in_range,
)

__all__ = [
    "transcribe_audio",
    "TranscriptSegment",
    "WordTimestamp",
    "flatten_words",
    "text_in_range",
    "words_in_range",
]
