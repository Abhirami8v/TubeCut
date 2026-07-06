"""
gemini_transcription_service.py
Transcribes audio using Gemini instead of Whisper.
"""

from __future__ import annotations

import json
import mimetypes
import time
import google.genai
import inspect

print("========== GEMINI DEBUG ==========")
print("google-genai version:", getattr(google.genai, "__version__", "unknown"))

client = genai.Client(api_key=GEMINI_API_KEY)

print("upload signature:", inspect.signature(client.files.upload))
print("==================================")
from typing import List

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"

    if logger:
        logger.debug(f"Uploading {audio_path} to Gemini")

    #uploaded_file = client.files.upload(path=audio_path)
    return[]
    print(uploaded_file)
    print(type(uploaded_file))
    print(uploaded_file.state)
    print(type(uploaded_file.state))
    poll_start = time.time()
    while uploaded_file.state == "PROCESSING":
        if time.time() - poll_start > 120:
            raise TimeoutError("Gemini file upload timed out")
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state != "ACTIVE":
        raise RuntimeError(f"Gemini file upload failed: {uploaded_file.state.name}")

    prompt = """
Transcribe this audio completely and accurately.

Break into natural segments (one sentence each, 3-12 words).
For each segment estimate start and end time in seconds.

Return ONLY valid JSON, no markdown, in this exact shape:
{
  "segments": [
    {"start": 0.0, "end": 3.2, "text": "exact spoken words"}
  ]
}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[uploaded_file, prompt],
    )

    text = (response.text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        if logger:
            logger.error(f"Gemini returned invalid JSON: {text[:500]}")
        raise RuntimeError(f"Gemini transcription returned invalid JSON: {exc}") from exc

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
        logger.info(f"Gemini transcription: {len(transcript)} segments, {total_words} words")

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