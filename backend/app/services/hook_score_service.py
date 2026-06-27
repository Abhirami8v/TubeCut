"""
hook_score_service.py

A transparent, deterministic "hook score" (0-100) computed entirely
locally -- no API call, no black box. This runs alongside Gemini's
confidence_score so the two can be blended into a final viral_score,
and so a hook score is always available even if Gemini is unreachable.

The heuristic looks at signals known to correlate with strong short-form
hooks: how the clip opens, pacing, question/number/emotional-word
density, and a penalty for dead air at the very start (the single
biggest killer of short-form retention).
"""

from __future__ import annotations

import re
from typing import List, TypedDict

QUESTION_WORDS = {
    "what", "why", "how", "who", "when", "where", "which",
}

HOOK_OPENERS = (
    "imagine", "what if", "did you know", "here's why", "here's how",
    "the truth is", "nobody tells you", "stop", "wait", "listen",
    "this is why", "you won't believe", "the secret", "i used to",
    "the biggest mistake", "never", "always",
)

EMOTIONAL_WORDS = {
    "shocking", "secret", "never", "always", "mistake", "truth", "lie",
    "scared", "afraid", "amazing", "insane", "crazy", "best", "worst",
    "free", "warning", "danger", "love", "hate", "fear", "win", "lose",
    "fail", "success", "money", "rich", "poor", "die", "death", "life",
    "changed", "transform", "broke", "destroy", "secretly", "exposed",
}

NUMBER_PATTERN = re.compile(r"\b\d+\b")


class HookScoreBreakdown(TypedDict):
    total: float
    opening_hook: float
    pacing: float
    keyword_density: float
    silence_penalty: float


def compute_hook_score(
    text: str,
    words: List[dict] | None = None,
) -> HookScoreBreakdown:
    """
    Compute a 0-100 hook score for a clip's transcript text.

    `words` (optional) is the word-timestamp list relative to clip start,
    used to detect dead air before the first spoken word.
    """
    text = (text or "").strip()
    if not text:
        return {
            "total": 0.0,
            "opening_hook": 0.0,
            "pacing": 0.0,
            "keyword_density": 0.0,
            "silence_penalty": 0.0,
        }

    lower = text.lower()
    first_words = " ".join(lower.split()[:8])

    # --- Opening hook strength (0-40) -------------------------------------
    opening_score = 10.0  # baseline
    if any(first_words.startswith(opener) or opener in first_words for opener in HOOK_OPENERS):
        opening_score += 20.0
    first_word = lower.split()[0].strip(".,!?") if lower.split() else ""
    if first_word in QUESTION_WORDS or text.strip().endswith("?") or "?" in text[:60]:
        opening_score += 10.0
    opening_score = min(40.0, opening_score)

    # --- Pacing: shorter average sentence length reads as punchier (0-20) -
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if sentences:
        avg_words_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences)
        # Sweet spot ~6-14 words/sentence for short-form delivery.
        if 6 <= avg_words_per_sentence <= 14:
            pacing_score = 20.0
        elif avg_words_per_sentence < 6:
            pacing_score = 14.0
        else:
            # Penalize long run-on sentences.
            overflow = avg_words_per_sentence - 14
            pacing_score = max(4.0, 20.0 - overflow * 1.2)
    else:
        pacing_score = 8.0

    # --- Keyword density: numbers + emotional/curiosity words (0-30) -----
    word_tokens = re.findall(r"[a-zA-Z']+", lower)
    total_words = max(len(word_tokens), 1)
    emotional_hits = sum(1 for w in word_tokens if w in EMOTIONAL_WORDS)
    number_hits = len(NUMBER_PATTERN.findall(text))
    density = (emotional_hits + number_hits) / total_words
    keyword_score = min(30.0, density * 220.0)

    # --- Silence penalty: dead air before first word (0 to -15) ----------
    silence_penalty = 0.0
    if words:
        first_word_start = words[0].get("start", 0.0)
        if first_word_start > 1.5:
            silence_penalty = -min(15.0, (first_word_start - 1.5) * 5.0)

    total = opening_score + pacing_score + keyword_score + silence_penalty
    total = max(0.0, min(100.0, total))

    return {
        "total": round(total, 1),
        "opening_hook": round(opening_score, 1),
        "pacing": round(pacing_score, 1),
        "keyword_density": round(keyword_score, 1),
        "silence_penalty": round(silence_penalty, 1),
    }


def blend_scores(confidence_score: float, hook_score: float) -> float:
    """
    Blend Gemini's confidence_score with the local hook_score into a
    single viral_score. Weighted slightly toward the hook score, since
    it directly measures retention-driving signal, while confidence
    captures whether the content is substantively clip-worthy at all.
    """
    blended = (confidence_score * 0.45) + (hook_score * 0.55)
    return round(max(0.0, min(100.0, blended)), 1)
