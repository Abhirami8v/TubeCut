"""
gemini_service.py — Viral clip analysis using Groq Llama.
"""
from __future__ import annotations

import json
import os
from typing import List, TypedDict

from app.core.config import TARGET_CLIP_COUNT
from app.services.transcript_utils import text_in_range


class CandidateClip(TypedDict):
    start_time: float
    end_time: float
    confidence_score: float
    reason: str
    title: str


def get_target_duration(source_duration: float) -> float:
    """
    Scale clip lengths proportionally based on the source video duration.
    - Max clip duration: 60 seconds
    - Min clip duration: 15 seconds
    - Prefer clips between 30-60 seconds whenever possible
    - If source is 30s, generate approximately 15s clips
    - Never generate clips longer than the source video
    """
    if source_duration <= 15.0:
        return source_duration
    elif source_duration <= 30.0:
        return max(15.0, source_duration / 2.0)
    elif source_duration <= 60.0:
        # Scale between 15s and 30s
        return 15.0 + (source_duration - 30.0) * (15.0 / 30.0)
    elif source_duration <= 120.0:
        # Scale between 30s and 60s
        return 30.0 + (source_duration - 60.0) * (30.0 / 60.0)
    else:
        return 60.0


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

    total_duration = transcript[-1]["end"]
    target_len = get_target_duration(total_duration)
    transcript_json = json.dumps(transcript, indent=2)

    prompt = f"""You are a world-class short-form video editor identifying viral moments.

Analyze this transcript and identify the {count} MOST compelling moments
that would work as standalone short-form clips optimized for YouTube Shorts engagement.

Prioritize moments with:
1. Strong opening hooks that grab attention in the first 3 seconds
2. Curiosity gaps that make viewers keep watching
3. Emotional stories, shocking facts, or surprising revelations
4. Clear payoff or conclusion within the clip
5. Self-contained meaning without needing context
6. Complete, meaningful segments (avoid cutting sentences in half or splitting mid-phrase).

Rules:
- Return EXACTLY {count} clips.
- Each clip must be between 15.0 and 60.0 seconds (never exceed 60.0 seconds).
- Proportional scaling: The source video duration is {total_duration:.1f}s. Scale clip durations proportionally.
  * For this video, prefer clip lengths around {target_len:.1f} seconds.
- Never generate clips longer than the source video ({total_duration:.1f}s).
- No overlapping time ranges.
- Pick genuinely viral moments.

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
            "start_time":       round(start, 2),
            "end_time":         round(end, 2),
            "confidence_score": float(clip.get("confidence_score", 70)),
            "reason":           clip.get("reason", ""),
            "title":            clip.get("title",  "Untitled Clip"),
        })

    return candidates


def _fallback_segmentation(transcript: List[dict], count: int) -> List[CandidateClip]:
    if not transcript:
        return []

    total_duration = transcript[-1]["end"]
    target_duration = get_target_duration(total_duration)

    # Ensure min/max bounds
    target_duration = max(15.0, min(60.0, target_duration))
    if total_duration < 15.0:
        target_duration = total_duration

    candidates: List[CandidateClip] = []

    if count <= 1 or total_duration <= target_duration:
        start_time = transcript[0]["start"]
        end_time = transcript[-1]["end"]
        # If it's too long, align to segments and cut at target_duration
        if end_time - start_time > target_duration:
            accumulated_end = start_time
            for seg in transcript:
                if seg["end"] - start_time <= target_duration:
                    accumulated_end = seg["end"]
                else:
                    if accumulated_end - start_time < 15.0:
                        accumulated_end = seg["end"]  # ensure minimum 15s if possible
                    break
            end_time = accumulated_end

        candidates.append({
            "start_time":       round(start_time, 2),
            "end_time":         round(end_time, 2),
            "confidence_score": 75.0,
            "reason":           "Auto-segmented based on optimal Shorts duration.",
            "title":            "Shorts Highlight",
        })
        return candidates

    # If count > 1, space them out evenly across the video
    spacing = (total_duration - target_duration) / (count - 1)
    for c in range(count):
        target_start = c * spacing
        # Find the segment closest to target_start
        start_idx = 0
        min_diff = float("inf")
        for idx, seg in enumerate(transcript):
            diff = abs(seg["start"] - target_start)
            if diff < min_diff:
                min_diff = diff
                start_idx = idx

        start_time = transcript[start_idx]["start"]
        end_time = transcript[start_idx]["end"]

        # Accumulate segments until we reach target_duration (without exceeding 60s)
        for idx in range(start_idx, len(transcript)):
            seg = transcript[idx]
            current_len = seg["end"] - start_time
            if current_len <= target_duration:
                end_time = seg["end"]
            else:
                # If we exceed, check if we must stay below 60s
                if current_len <= 60.0:
                    end_time = seg["end"]
                break

        # Ensure it's at least 15 seconds by extending backward if necessary
        if end_time - start_time < 15.0 and start_idx > 0:
            for idx in range(start_idx - 1, -1, -1):
                start_time = transcript[idx]["start"]
                if end_time - start_time >= 15.0:
                    break

        # Strictly enforce maximum 60 seconds
        if end_time - start_time > 60.0:
            for idx in range(start_idx, len(transcript)):
                if transcript[idx]["end"] - start_time <= 60.0:
                    end_time = transcript[idx]["end"]
                else:
                    break

        # Avoid duplicates
        is_dup = False
        for existing in candidates:
            if abs(existing["start_time"] - start_time) < 2.0 and abs(existing["end_time"] - end_time) < 2.0:
                is_dup = True
                break

        if not is_dup and end_time > start_time:
            text = text_in_range(transcript, start_time, end_time)
            title = text[:40].strip() + "..." if len(text) > 40 else text
            candidates.append({
                "start_time":       round(start_time, 2),
                "end_time":         round(end_time, 2),
                "confidence_score": 70.0,
                "reason":           "Segmented for maximum engagement and clear sentence boundaries.",
                "title":            title or f"Highlight part {c + 1}",
            })

    return candidates