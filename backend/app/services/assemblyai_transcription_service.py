"""
assemblyai_transcription_service.py
Transcription via AssemblyAI.
"""
from __future__ import annotations

import os
import time
from typing import List

from app.core.logging_utils import JobLogger
from app.services.transcript_utils import TranscriptSegment, WordTimestamp

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
UPLOAD_URL         = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_URL     = "https://api.assemblyai.com/v2/transcript"


def transcribe_audio(audio_path: str, logger: JobLogger | None = None) -> List[TranscriptSegment]:
    import httpx

    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set.")

    file_size = os.path.getsize(audio_path)
    if logger:
        logger.info(f"Audio size: {file_size / (1024*1024):.1f} MB")

    # Step 1 — Upload
    if logger:
        logger.info("Uploading audio to AssemblyAI...")

    with open(audio_path, "rb") as f:
        upload_response = httpx.post(
            UPLOAD_URL,
            headers={"authorization": ASSEMBLYAI_API_KEY},
            content=f.read(),
            timeout=120.0,
        )

    if upload_response.status_code != 200:
        raise RuntimeError(f"AssemblyAI upload failed: {upload_response.text}")

    audio_url = upload_response.json()["upload_url"]
    if logger:
        logger.info("Upload complete, starting transcription...")

    # Step 2 — Request transcription
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type":  "application/json",
    }

    transcript_response = httpx.post(
        TRANSCRIPT_URL,
        headers=headers,
        json={
            "audio_url":   audio_url,
            "punctuate":   True,
            "format_text": True,
        },
        timeout=30.0,
    )

    if transcript_response.status_code != 200:
        raise RuntimeError(f"AssemblyAI request failed: {transcript_response.text}")

    transcript_id = transcript_response.json()["id"]
    if logger:
        logger.info(f"Transcription job started: {transcript_id}")

    # Step 3 — Poll until done
    polling_url = f"{TRANSCRIPT_URL}/{transcript_id}"
    max_wait    = 600
    waited      = 0

    while waited < max_wait:
        poll = httpx.get(polling_url, headers=headers, timeout=30.0)

        if poll.status_code != 200:
            raise RuntimeError(f"AssemblyAI polling failed: {poll.text}")

        result = poll.json()
        status = result.get("status")

        if logger:
            logger.info(f"AssemblyAI status: {status}")

        if status == "completed":
            return _parse_result(result, logger)
        elif status == "error":
            raise RuntimeError(f"AssemblyAI error: {result.get('error')}")

        time.sleep(5)
        waited += 5

    raise RuntimeError("AssemblyAI timed out after 10 minutes")


def _parse_result(
    result: dict, logger: JobLogger | None = None
) -> List[TranscriptSegment]:
    raw_words = result.get("words") or []

    if not raw_words:
        if logger:
            logger.warn("AssemblyAI returned no words")
        return []

    word_list: List[WordTimestamp] = []
    for w in raw_words:
        word_text  = (w.get("text") or "").strip()
        word_start = float(w.get("start", 0)) / 1000.0
        word_end   = float(w.get("end",   0)) / 1000.0
        if not word_text:
            continue
        if word_end <= word_start:
            word_end = word_start + 0.1
        word_list.append({
            "word":  word_text,
            "start": round(word_start, 2),
            "end":   round(word_end,   2),
        })

    if not word_list:
        return []

    transcript: List[TranscriptSegment] = []
    chunk_size = 10

    for i in range(0, len(word_list), chunk_size):
        chunk = word_list[i : i + chunk_size]
        if not chunk:
            continue
        transcript.append({
            "start": round(chunk[0]["start"], 2),
            "end":   round(chunk[-1]["end"],  2),
            "text":  " ".join(w["word"] for w in chunk).strip(),
            "words": chunk,
        })

    if logger:
        logger.info(f"Parsed {len(transcript)} segments, {len(word_list)} words")

    return transcript