"""
gemini_service.py

Uses Gemini to analyze a full transcript and identify the most
"clip-worthy" moments (meaningful segmentation rather than fixed-length
chopping). Returns structured candidate clips with a start/end time, an
AI confidence score, and the model's stated reasoning.

If the Gemini call fails for any reason (missing key, network, bad
JSON), we fall back to a simple silence/sentence-boundary segmenter so
the pipeline still produces usable clips instead of erroring out.
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
    """
    Identify the most clip-worthy moments in `transcript` using Gemini.
    Falls back to a heuristic segmenter if the API call fails.
    """
    count = target_clip_count or TARGET_CLIP_COUNT

    if GEMINI_API_KEY:
        try:
            return _analyze_with_gemini(transcript, count)
        except Exception as exc:  # noqa: BLE001
            print(f"[gemini_service] Gemini analysis failed, using fallback: {exc}")

    return _fallback_segmentation(transcript, count)


def _analyze_with_gemini(transcript: List[dict], count: int) -> List[CandidateClip]:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)

    simple_transcript = [
        {
            "start": s["start"],
            "end": s["end"],
            "text": s["text"],
        }
         for s in transcript
    ]

    transcript_json = json.dumps(simple_transcript, ensure_ascii=False)

    prompt = f"""
You are a world-class short-form video editor identifying viral moments.

Analyze this transcript and identify the {count} MOST compelling, self-contained moments
that would work as standalone short-form clips.

Prioritize moments with:
1. Strong opening hooks (a question, bold claim, or surprising statement in the first 3 seconds)
2. Curiosity gaps that make viewers want to keep watching
3. Emotional stories, transformations, or shocking facts
4. Clear payoff / resolution within the clip
5. Self-contained meaning (a viewer with no other context understands it)

Avoid:
- Greetings, intros, outros, sponsor reads, filler, dead air
- Cutting off mid-sentence or mid-thought
- Overlapping time ranges between clips

Rules:
- Return EXACTLY {count} clips
- Each clip must be between {MIN_CLIP_SECONDS} and {MAX_CLIP_SECONDS} seconds
- Use ONLY timestamps that appear in the transcript
- Start as close to the hook as possible, end on a natural sentence boundary
- confidence_score is 0-100: how confident you are this is genuinely clip-worthy content

Return ONLY valid JSON, no markdown fences, in this exact shape:
{{
  "clips": [
    {{
      "start_time": 0,
      "end_time": 30,
      "confidence_score": 92,
      "reason": "Why this moment works as a standalone clip",
      "title": "Short, punchy title for this clip"
    }}
  ]
}}

Transcript:
{transcript_json}
"""

    response = client.models.generate_content(
        model=f"models/{GEMINI_MODEL}",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
    
        ),
    )   

    text = (response.text or "").strip()
    
    # Robust JSON extraction: locate the JSON object bounding braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        text = text[first_brace:last_brace + 1]

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print("========== RAW GEMINI RESPONSE ==========")
        print(text)
        raise
    clips = result.get("clips", [])
    if not isinstance(clips, list):
        raise ValueError("Gemini returned an invalid clips format.")
    candidates: List[CandidateClip] = []
    for clip in clips:
        candidates.append(
            {
                "start_time": float(clip.get("start_time", 0)),
                "end_time": float(clip.get("end_time", 0)),
                "confidence_score": float(clip.get("confidence_score", 70)),
                "reason": clip.get("reason", ""),
                "title": clip.get("title", "Untitled Clip"),
            }
        )

    if not candidates:
        raise ValueError("Gemini returned zero clips")

    return candidates


def _fallback_segmentation(transcript: List[dict], count: int) -> List[CandidateClip]:
    """
    Deterministic fallback: build exactly `count` clips of engaging
    short-form length (25-45 seconds) spaced evenly across the video.
    """
    if not transcript:
        return []

    total_duration = transcript[-1]["end"]
    
    import random
    candidates: List[CandidateClip] = []
    segment_duration = total_duration / max(count, 1)

    for idx in range(count):
        ideal_start = idx * segment_duration
        
        # Find closest start segment
        start_seg = min(transcript, key=lambda s: abs(s["start"] - ideal_start))
        start_time = start_seg["start"]

        # Target end time: random engaging duration between 25.0 and 55.0 seconds
        min_dur = min(25.0, total_duration)
        max_dur = min(55.0, total_duration)
        if min_dur >= max_dur:
            target_duration = total_duration
        else:
            target_duration = random.uniform(min_dur, max_dur)

        ideal_end = start_time + target_duration
        end_seg = min(transcript, key=lambda s: abs(s["end"] - ideal_end))
        end_time = end_seg["end"]

        if end_time <= start_time:
            end_time = start_time + target_duration

        # Accumulate text for clip title
        text_pieces = []
        for s in transcript:
            if start_time <= s["start"] <= end_time:
                text_pieces.append(s["text"])

        title = " ".join(text_pieces)[:40].strip() or f"Highlight Moment {idx + 1}"

        candidates.append(
            {
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "confidence_score": 60.0,
                "reason": f"Auto-segmented fallback moment from part {idx + 1} of the video.",
                "title": title,
            }
        )

    return candidates
