"""
gemini_service.py — Viral clip analysis using Groq Llama.
"""
from __future__ import annotations

import json
import os
from typing import List, TypedDict

from app.core.config import MAX_CLIP_SECONDS, MIN_CLIP_SECONDS, TARGET_CLIP_COUNT


class CandidateClip(TypedDict):
    start_time: float
    end_time: float
    confidence_score: float
    reason: str
    title: str


def analyze_transcript(
    transcript: List[dict], target_clip_count: int | None = None
) -> List[CandidateClip]:
    count = target_clip_count or TARGET_CLIP_COUNT

    if os.getenv("GROQ_API_KEY"):
        try:
            return _analyze_with_groq(transcript, count)
        except Exception as exc:
            print(f"[analysis] Groq failed, using fallback: {exc}")

    return _fallback_segmentation(transcript, count)


def _analyze_with_groq(transcript: List[dict], count: int) -> List[CandidateClip]:
    import httpx
    from groq import Groq

    client = Groq(
        api_key=os.getenv("GROQ_API_KEY", ""),
        http_client=httpx.Client(),
    )

    transcript_json = json.dumps(transcript, indent=2)

    prompt = f"""You are a world-class short-form video editor identifying viral moments.

Analyze this transcript and identify the {count} MOST compelling moments
that would work as standalone short-form clips (YouTube Shorts, TikTok, Reels).

Prioritize moments with:
1. Strong opening hooks that grab attention in the first 3 seconds
2. Curiosity gaps that make viewers keep watching
3. Emotional stories, shocking facts, or surprising revelations
4. Clear payoff or conclusion within the clip
5. Self-contained meaning without needing context

Rules:
- Return EXACTLY {count} clips
- Each clip must be between {MIN_CLIP_SECONDS} and {MAX_CLIP_SECONDS} seconds
- No overlapping time ranges
- Pick genuinely viral moments not just the beginning

Return ONLY valid JSON, no markdown, in this exact format:
{{
  "clips": [
    {{
      "start_time": 0.0,
      "end_time": 30.0,
      "confidence_score": 92,
      "reason": "Why this works as a viral clip",
      "title": "Short punchy title under 8 words"
    }}
  ]
}}

Transcript:
{transcript_json}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role":    "system",
                "content": "You are an expert viral video editor. Return valid JSON only, no markdown, no explanation.",
            },
            {
                "role":    "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    text = (response.choices[0].message.content or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    result = json.loads(text)
    clips  = result.get("clips", [])

    if not clips:
        raise ValueError("Groq returned zero clips")

    candidates: List[CandidateClip] = []
    for clip in clips:
        start = float(clip.get("start_time", 0))
        end   = float(clip.get("end_time",   0))
        if end <= start:
            continue
        candidates.append({
            "start_time":       start,
            "end_time":         end,
            "confidence_score": float(clip.get("confidence_score", 70)),
            "reason":           clip.get("reason", ""),
            "title":            clip.get("title",  "Untitled Clip"),
        })

    return candidates


def _fallback_segmentation(transcript: List[dict], count: int) -> List[CandidateClip]:
    if not transcript:
        return []

    total_duration  = transcript[-1]["end"]
    target_duration = min(
        MAX_CLIP_SECONDS,
        max(MIN_CLIP_SECONDS, total_duration / max(count, 1))
    )

    candidates: List[CandidateClip] = []
    current_start  = transcript[0]["start"]
    current_texts: List[str] = []

    for i, segment in enumerate(transcript):
        current_texts.append(segment["text"])
        elapsed = segment["end"] - current_start
        is_last = i == len(transcript) - 1

        if elapsed >= target_duration or is_last:
            candidates.append({
                "start_time":       round(current_start,  2),
                "end_time":         round(segment["end"], 2),
                "confidence_score": 60.0,
                "reason":           "Auto-segmented based on duration.",
                "title":            " ".join(current_texts)[:48].strip() or "Untitled Clip",
            })
            if len(candidates) >= count:
                break
            if i + 1 < len(transcript):
                current_start = transcript[i + 1]["start"]
            current_texts = []

    return candidates[:count]