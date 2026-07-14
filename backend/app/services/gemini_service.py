"""
gemini_service.py
Uses Gemini to find viral clip moments from transcript.
"""

from __future__ import annotations

import json
from typing import List, TypedDict

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_CLIP_SECONDS, MIN_CLIP_SECONDS, TARGET_CLIP_COUNT


class CandidateClip(TypedDict):
    start_time: float
    end_time: float
    confidence_score: float
    reason: str
    title: str


def analyze_transcript(transcript: List[dict], target_clip_count: int | None = None) -> List[CandidateClip]:
    count = target_clip_count or TARGET_CLIP_COUNT

    if GEMINI_API_KEY:
        try:
            return _analyze_with_gemini(transcript, count)
        except Exception as exc:
            print(f"[gemini_service] Gemini analysis failed, using fallback: {exc}")

    return _fallback_segmentation(transcript, count)


def _analyze_with_gemini(transcript: List[dict], count: int) -> List[CandidateClip]:
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)

    transcript_json = json.dumps(transcript, indent=2)

    prompt = f"""
You are a world-class short-form video editor identifying viral moments.

Analyze this transcript and identify the {count} MOST compelling moments
that would work as standalone short-form clips.

Prioritize moments with:
1. Strong opening hooks
2. Curiosity gaps
3. Emotional stories or shocking facts
4. Clear payoff within the clip
5. Self-contained meaning

Rules:
- Return EXACTLY {count} clips
- Each clip must be between {MIN_CLIP_SECONDS} and {MAX_CLIP_SECONDS} seconds
- No overlapping time ranges

Return ONLY valid JSON, no markdown backticks, in this exact format:
{{
  "clips": [
    {{
      "start_time": 0,
      "end_time": 30,
      "confidence_score": 92,
      "reason": "Why this works as a standalone clip",
      "title": "Short punchy title"
    }}
  ]
}}

Transcript:
{transcript_json}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    text = (response.text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    result = json.loads(text)
    clips = result.get("clips", [])

    candidates: List[CandidateClip] = []
    for clip in clips:
        candidates.append({
            "start_time": float(clip.get("start_time", 0)),
            "end_time": float(clip.get("end_time", 0)),
            "confidence_score": float(clip.get("confidence_score", 70)),
            "reason": clip.get("reason", ""),
            "title": clip.get("title", "Untitled Clip"),
        })

    if not candidates:
        raise ValueError("Gemini returned zero clips")

    return candidates


def _fallback_segmentation(transcript: List[dict], count: int) -> List[CandidateClip]:
    if not transcript:
        return []

    total_duration = transcript[-1]["end"]
    target_duration = min(
        MAX_CLIP_SECONDS,
        max(MIN_CLIP_SECONDS, total_duration / max(count, 1))
    )

    candidates: List[CandidateClip] = []
    current_start = transcript[0]["start"]
    current_text_segments: List[str] = []

    for i, segment in enumerate(transcript):
        current_text_segments.append(segment["text"])
        elapsed = segment["end"] - current_start
        is_last = i == len(transcript) - 1

        if elapsed >= target_duration or is_last:
            candidates.append({
                "start_time": round(current_start, 2),
                "end_time": round(segment["end"], 2),
                "confidence_score": 60.0,
                "reason": "Auto-segmented based on transcript pacing.",
                "title": " ".join(current_text_segments)[:48].strip() or "Untitled Clip",
            })

            if len(candidates) >= count:
                break

            if i + 1 < len(transcript):
                current_start = transcript[i + 1]["start"]
            current_text_segments = []

    return candidates[:count]