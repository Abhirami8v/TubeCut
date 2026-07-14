"""
transcription_service.py
Legacy Whisper transcription engine - kept as fallback.
"""

from __future__ import annotations

from typing import List

from app.core.config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_SIZE
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import (
    TranscriptSegment,
    WordTimestamp,
    flatten_words,
    text_in_range,
    words_in_range,
)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _model


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    model = _get_model()

    segments, _info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 1000},
    )

    transcript: List[TranscriptSegment] = []

    for segment in segments:
        words: List[WordTimestamp] = [
            {
                "word": word.word.strip(),
                "start": round(word.start, 2),
                "end": round(word.end, 2),
            }
            for word in (segment.words or [])
        ]

        if not words and segment.text.strip():
            words = _synthesize_word_timestamps(
                segment.text.strip(), segment.start, segment.end
            )

        transcript.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
            "words": words,
        })

    if not transcript and logger:
        logger.warn(f"Whisper returned zero segments for {audio_path}")

    return transcript


def _synthesize_word_timestamps(
    text: str, start: float, end: float
) -> List[WordTimestamp]:
    words = text.split()
    if not words:
        return []
    duration = max(0.01, end - start)
    step = duration / len(words)
    return [
        {
            "word": w,
            "start": round(start + i * step, 2),
            "end": round(start + (i + 1) * step, 2),
        }
        for i, w in enumerate(words)
    ]