"""
gemini_transcription_service.py
Transcribes audio using Google Gemini via google-genai library.
"""

from __future__ import annotations

import json
import time
from typing import List

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    if logger:
        logger.info(f"Uploading audio to Gemini: {audio_path}")

    # Upload audio file
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/wav",
            ),
            """Transcribe this audio completely and accurately.

Break into natural segments of one sentence each.
For each segment estimate start and end time in seconds.

Return ONLY valid JSON, no markdown backticks, in this exact format:
{
  "segments": [
    {"start": 0.0, "end": 3.2, "text": "exact spoken words here"}
  ]
}

Cover the entire audio from start to finish."""
        ],
    )

    text = (response.text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    if logger:
        logger.debug(f"Gemini response preview: {text[:200]}")

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        if logger:
            logger.error(f"Failed to parse Gemini JSON: {text[:500]}")
        raise RuntimeError(f"Gemini returned invalid JSON: {exc}") from exc

    raw_segments = result.get("segments", [])
    if not raw_segments:
        if logger:
            logger.warn("Gemini returned zero segments")
        return []

    transcript: List[TranscriptSegment] = []
    for seg in raw_segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 1.0))
        seg_text = (seg.get("text") or "").strip()
        if end <= start:
            end = start + 0.5
        if not seg_text:
            continue
        words = _synthesize_word_timestamps(seg_text, start, end)
        transcript.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": seg_text,
            "words": words,
        })

    transcript.sort(key=lambda s: s["start"])

    if logger:
        total_words = sum(len(s["words"]) for s in transcript)
        logger.info(f"Transcription complete: {len(transcript)} segments, {total_words} words")

    return transcript


def _synthesize_word_timestamps(text: str, start: float, end: float) -> List[WordTimestamp]:
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