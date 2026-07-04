"""
transcript_utils.py
Engine-agnostic helpers for working with a transcript.
"""

from __future__ import annotations

from typing import List, TypedDict


class WordTimestamp(TypedDict):
    word: str
    start: float
    end: float


class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str
    words: List[WordTimestamp]


def flatten_words(transcript: List[TranscriptSegment]) -> List[WordTimestamp]:
    words: List[WordTimestamp] = []
    for segment in transcript:
        words.extend(segment.get("words", []))
    return words


def words_in_range(transcript: List[TranscriptSegment], start: float, end: float) -> List[WordTimestamp]:
    result: List[WordTimestamp] = []
    for word in flatten_words(transcript):
        if start <= word["start"] <= end:
            result.append({
                "word": word["word"],
                "start": round(word["start"] - start, 2),
                "end": round(word["end"] - start, 2),
            })
    return result


def text_in_range(transcript: List[TranscriptSegment], start: float, end: float) -> str:
    pieces = [
        segment["text"]
        for segment in transcript
        if segment["end"] >= start and segment["start"] <= end
    ]
    return " ".join(pieces).strip()