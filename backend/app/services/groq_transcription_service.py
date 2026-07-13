"""
groq_transcription_service.py
Transcribes audio using Groq Whisper API (whisper-large-v3-turbo)
via the official groq Python SDK with real word-level timestamps.
"""

from __future__ import annotations

import os
from typing import List

from app.core.config import GROQ_API_KEY
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    if logger:
        logger.info(f"Reading audio file: {audio_path}")

    file_size = os.path.getsize(audio_path)
    if logger:
        logger.info(f"Audio file size: {file_size} bytes")

    # Groq's API accepts the file directly. We open the file and pass the stream.
    with open(audio_path, "rb") as audio_file:
        if logger:
            logger.info("Sending audio to Groq Whisper API for transcription")

        try:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        except Exception as exc:
            if logger:
                logger.error(f"Groq API call failed: {exc}")
            raise RuntimeError(
                f"Groq Whisper transcription failed: {exc}. Please verify that your GROQ_API_KEY is valid."
            ) from exc

    if logger:
        logger.debug(f"Groq response received, type: {type(transcription).__name__}")

    # Extract segments and word timestamps from Groq's response
    # The verbose_json response has:
    #   transcription.text       -> full text
    #   transcription.segments   -> list of segment dicts with start, end, text
    #   transcription.words      -> list of word dicts with word, start, end

    raw_segments = getattr(transcription, "segments", None)
    raw_words = getattr(transcription, "words", None)

    # Build a word map: for each word, we have {word, start, end}
    word_list: List[WordTimestamp] = []
    if raw_words:
        for w in raw_words:
            word_text = (getattr(w, "word", "") or "").strip()
            if not word_text:
                continue
            word_start = float(getattr(w, "start", 0.0))
            word_end = float(getattr(w, "end", word_start + 0.1))
            if word_end <= word_start:
                word_end = word_start + 0.1
            word_list.append({
                "word": word_text,
                "start": round(word_start, 2),
                "end": round(word_end, 2),
            })

    if not raw_segments:
        if logger:
            logger.warn("Groq returned zero segments")
        return []

    transcript: List[TranscriptSegment] = []
    for seg in raw_segments:
        seg_start = float(getattr(seg, "start", 0.0))
        seg_end = float(getattr(seg, "end", seg_start + 1.0))
        seg_text = (getattr(seg, "text", "") or "").strip()
        if seg_end <= seg_start:
            seg_end = seg_start + 0.5
        if not seg_text:
            continue

        # Filter words that belong to this segment based on time range
        seg_words = [
            w for w in word_list
            if seg_start - 0.05 <= w["start"] <= seg_end + 0.05
        ]

        # If no words matched (edge case), fall back to synthesizing
        if not seg_words:
            seg_words = _synthesize_word_timestamps(seg_text, seg_start, seg_end)

        transcript.append({
            "start": round(seg_start, 2),
            "end": round(seg_end, 2),
            "text": seg_text,
            "words": seg_words,
        })

    transcript.sort(key=lambda s: s["start"])

    if logger:
        total_words = sum(len(s["words"]) for s in transcript)
        logger.info(
            f"Transcription complete: {len(transcript)} segments, "
            f"{total_words} words"
        )

    return transcript


def _synthesize_word_timestamps(
    text: str, start: float, end: float
) -> List[WordTimestamp]:
    """Fallback: evenly distribute word timestamps when real ones are unavailable."""
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