"""
gemini_transcription_service.py — Transcription via OpenRouter (Gemini models)
"""
from __future__ import annotations

import json
import os
import base64
from typing import List

from app.core.config import GEMINI_MODEL
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    import httpx

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    if logger:
        logger.info(f"Reading audio: {audio_path}")

    file_size = os.path.getsize(audio_path)
    if logger:
        logger.info(f"Audio size: {file_size / (1024*1024):.1f} MB")

    # Read and base64 encode the audio file
    with open(audio_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")

    if logger:
        logger.info("Sending audio to OpenRouter for transcription...")

    prompt = """Transcribe this audio completely and accurately.

Return ONLY valid JSON, no markdown, in exactly this format:
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
- Split on natural sentence or phrase boundaries
- Spoken words only, no music tags or sound effects
- Timestamps must increase monotonically"""

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:audio/mp3;base64,{audio_data}"
                        }
                    }
                ]
            }
        ]
    }

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tubecut.app",
            "X-Title": "TubeCut",
        },
        json=payload,
        timeout=120.0,
    )

    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {response.status_code}: {response.text}")

    data     = response.json()
    raw_text = data["choices"][0]["message"]["content"].strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    segments_data = json.loads(raw_text)
    raw_segments  = segments_data.get("segments", [])

    if not raw_segments:
        if logger:
            logger.warn("OpenRouter returned zero segments")
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


def _synthesize_word_timestamps(text: str, start: float, end: float) -> List[WordTimestamp]:
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