"""
gemini_transcription_service.py
Transcription via direct Gemini API using Files API for audio support.
"""
from __future__ import annotations

import json
import os
import time
from typing import List

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    from google import genai

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    if logger:
        logger.info(f"Reading audio: {audio_path}")

    file_size = os.path.getsize(audio_path)
    if logger:
        logger.info(f"Audio size: {file_size / (1024*1024):.1f} MB")

    client = genai.Client(api_key=GEMINI_API_KEY)

    if logger:
        logger.info("Uploading audio to Gemini Files API...")

    with open(audio_path, "rb") as f:
        audio_file = client.files.upload(
            file=f,
            config={
                "mime_type": "audio/mp3",
                "display_name": f"tubecut_{os.path.basename(audio_path)}",
            },
        )

    for _ in range(30):
        status = client.files.get(name=audio_file.name)
        if status.state.name == "ACTIVE":
            break
        if logger:
            logger.info("Waiting for file to become active...")
        time.sleep(2)
    else:
        raise RuntimeError("Gemini file upload did not become ACTIVE in time")

    prompt = """Transcribe this audio completely and accurately.

Return ONLY valid JSON, no markdown fences, in exactly this format:
{
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "exact spoken words here"
    }
  ]
}

Rules:
- Transcribe ALL spoken content, nothing skipped
- start/end are seconds from beginning of audio
- Split on natural sentence or phrase boundaries every 5-15 words
- Spoken words only, no music tags or sound effects
- Timestamps must increase monotonically"""

    if logger:
        logger.info("Sending to Gemini for transcription...")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[audio_file, prompt],
    )

    try:
        client.files.delete(name=audio_file.name)
    except Exception:
        pass

    raw_text = (response.text or "").strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    segments_data = json.loads(raw_text)
    raw_segments  = segments_data.get("segments", [])

    if not raw_segments:
        if logger:
            logger.warn("Gemini returned zero segments")
        return []

    transcript: List[TranscriptSegment] = []
    for seg in raw_segments:
        start = float(seg.get("start", 0.0))
        end   = float(seg.get("end",   0.0))
        text  = (seg.get("text") or "").strip()

        if end <= start or not text:
            continue

        words = _synthesize_word_timestamps(text, start, end)
        transcript.append({
            "start": round(start, 2),
            "end":   round(end,   2),
            "text":  text,
            "words": words,
        })

    transcript.sort(key=lambda s: s["start"])

    if logger:
        total_words = sum(len(s["words"]) for s in transcript)
        logger.info(f"Transcription complete: {len(transcript)} segments, {total_words} words")

    return transcript


def _synthesize_word_timestamps(
    text: str, start: float, end: float
) -> List[WordTimestamp]:
    words    = text.split()
    if not words:
        return []
    duration = max(0.01, end - start)
    step     = duration / len(words)
    return [
        {
            "word":  w,
            "start": round(start + i * step,       2),
            "end":   round(start + (i + 1) * step, 2),
        }
        for i, w in enumerate(words)
    ]