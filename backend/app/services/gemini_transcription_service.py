"""
gemini_transcription_service.py
Transcribes audio using Gemini instead of Whisper.
"""

from __future__ import annotations

import json
import mimetypes
import time
from typing import List



from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp
print("========== GEMINI FILE LOADED ==========")
print(__file__)

def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    
    from google import genai
    import inspect

    print("GENAI MODULE:", genai)
    print("GENAI FILE:", genai.__file__)
    print("GENAI VERSION:", getattr(genai, "__version__", "NO VERSION"))
    print("ENTERED transcribe_audio()")
    client = genai.Client(api_key=GEMINI_API_KEY)

    print("UPLOAD SIGNATURE:", inspect.signature(client.files.upload))
   
    mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"

    if logger:
        logger.debug(f"Uploading {audio_path} to Gemini")

    uploaded_file = client.files.upload(file=audio_path)
    print(uploaded_file)
   
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

    from google.genai import types
    import re

    max_attempts = 3
    result = None
    last_exc = None

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            text = (response.text or "").strip()
            
            # 1. Remove markdown code fences if present
            if "```" in text:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1).strip()
            
            # 2. Extract first complete JSON object
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace != -1 and last_brace != -1:
                text = text[first_brace:last_brace + 1]

            # 3. Parse JSON
            result = json.loads(text)
            break
        except Exception as e:
            last_exc = e
            if logger:
                logger.warn(f"Gemini transcription parsing failed (Attempt {attempt + 1}/{max_attempts}): {e}")
                raw_text = response.text if 'response' in locals() and response.text else ""
                snippet = raw_text[:500] + ("..." if len(raw_text) > 500 else "")
                logger.warn(f"Raw Gemini response snippet: {snippet}")
            time.sleep(2.0)

    if result is None:
        err_msg = str(last_exc)
        if "API_KEY_INVALID" in err_msg or "invalid api key" in err_msg.lower() or "401" in err_msg:
            raise RuntimeError(f"Invalid GEMINI_API_KEY: {last_exc}")
        raise RuntimeError(f"Gemini transcription JSON decoding failed after {max_attempts} attempts: {last_exc}")

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

    # Check if the timestamps are valid
    has_valid_timestamps = False
    if transcript:
        last_end = transcript[-1]["end"]
        # Valid if last segment end is substantial and starts are not all identical to 0
        if last_end > 2.0 and any(s["start"] != 0.0 for s in transcript):
            has_valid_timestamps = True

    if not has_valid_timestamps and transcript:
        from app.services import video_service
        try:
            # Probe wav audio duration
            duration = video_service.probe_duration(audio_path)
        except Exception:
            duration = len(transcript) * 10.0

        duration = duration or (len(transcript) * 10.0)
        step = duration / len(transcript)

        for i, seg in enumerate(transcript):
            start = i * step
            end = (i + 1) * step
            seg["start"] = round(start, 2)
            seg["end"] = round(end, 2)
            seg["words"] = _synthesize_word_timestamps(seg["text"], start, end)

        if logger:
            logger.info(f"Gemini returned invalid timestamps; linearly distributed segments over {duration:.1f}s")

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