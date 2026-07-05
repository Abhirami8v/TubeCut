"""
transcription_service.py

Wraps faster-whisper for speech-to-text with word-level timestamps. The
model is loaded lazily (on first use) so importing this module -- e.g.
during API route registration -- doesn't pay model-load cost at import
time, and so the whole backend can boot even if model weights aren't
downloaded yet.
"""

from __future__ import annotations

import json

from typing import List, TypedDict

from app.core.config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_SIZE

_model = None


class WordTimestamp(TypedDict):
    word: str
    start: float
    end: float


class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str
    words: List[WordTimestamp]


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _model


def _transcribe_with_gemini(audio_path: str) -> List[TranscriptSegment]:
    """
    Fallback transcription service using Google's Gemini API.
    Uploads the audio track to Gemini, prompts the model to transcribe with
    exact word-level timestamps in structured JSON, and deletes the uploaded audio file.
    """
    from google import genai
    from google.genai import types
    from app.core.config import GEMINI_API_KEY, GEMINI_MODEL

    if not GEMINI_API_KEY:
        raise ValueError("Whisper transcription failed, and no GEMINI_API_KEY is configured for fallback.")

    print(f"[transcription_service] Whisper failed or is unavailable. Falling back to Gemini transcription for {audio_path}...")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print(f"[transcription_service] Uploading audio file to Gemini...")
    uploaded_file = client.files.upload(file=audio_path)
    
    try:
        prompt = """
        You are a highly accurate audio transcription tool.
        Analyze the audio track and transcribe it into text with exact word-level timestamps.
        You must output ONLY valid JSON matching this exact structure, with no markdown fences, no backticks, and no extra text:
        
        {
          "segments": [
            {
              "start": 0.0,
              "end": 2.5,
              "text": "Hello world",
              "words": [
                {"word": "Hello", "start": 0.0, "end": 1.2},
                {"word": "world", "start": 1.2, "end": 2.5}
              ]
            }
          ]
        }
        
        Ensure that segment start/end times cover the words inside them, and every word has a start and end timestamp.
        """
        
        print(f"[transcription_service] Generating transcription content using {GEMINI_MODEL}...")
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        text = response.text.strip()
        result = json.loads(text)
        segments_raw = result.get("segments", [])
        
        transcript: List[TranscriptSegment] = []
        for segment in segments_raw:
            words: List[WordTimestamp] = []
            for w in segment.get("words", []):
                words.append({
                    "word": str(w["word"]).strip(),
                    "start": round(float(w["start"]), 2),
                    "end": round(float(w["end"]), 2),
                })
            transcript.append({
                "start": round(float(segment["start"]), 2),
                "end": round(float(segment["end"]), 2),
                "text": str(segment.get("text", "")).strip(),
                "words": words
            })
            
        print(f"[transcription_service] Gemini transcription completed successfully with {len(transcript)} segments.")
        return transcript
        
    except Exception as gemini_exc:
        print(f"[transcription_service] Gemini transcription fallback failed: {gemini_exc}")
        raise gemini_exc
    finally:
        try:
            print(f"[transcription_service] Cleaning up uploaded file {uploaded_file.name} from Gemini...")
            client.files.delete(name=uploaded_file.name)
        except Exception as delete_exc:
            print(f"[transcription_service] Failed to delete uploaded file from Gemini storage: {delete_exc}")


def transcribe_audio(audio_path: str, 
                     logger:None,) -> List[TranscriptSegment]:
    """
    Transcribe the audio file at `audio_path` and return a list of
    segments, each with word-level timestamps.
    """
    try:
        model = _get_model()

        segments, _info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 1000},
        )

        transcript: List[TranscriptSegment] = []

        for segment in segments:
            words: List[WordTimestamp] = [
                {
                    "word": word.word.strip(),
                    "start": round(word.start, 2),
                    "end": round(word.end, 2),
                }
                for word in (segment.words or [])
            ]

            # Fallback: if Whisper returned segment-level text but somehow no
            # word-level timestamps (can happen on some audio), synthesize
            # evenly-spaced word timings from the segment span so downstream
            # caption-block building still has something to work with instead
            # of silently dropping this segment's captions.
            if not words and segment.text.strip():
                words = _synthesize_word_timestamps(segment.text.strip(), segment.start, segment.end)

            transcript.append(
                {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "words": words,
                }
            )

        if not transcript:
            print(
                f"[transcription_service] WARNING: Whisper returned zero segments for {audio_path}. "
                "No captions will be generated for clips from this video. This usually means VAD "
                "filtered out the whole track, or the audio is silent/corrupted."
            )

        return transcript

    except Exception as exc:
        print(f"[transcription_service] Whisper transcription failed: {exc}")
        try:
            return _transcribe_with_gemini(audio_path)
        except Exception as gemini_exc:
            print(f"[transcription_service] Both Whisper and Gemini fallback failed: {gemini_exc}")
            raise gemini_exc


def _synthesize_word_timestamps(text: str, start: float, end: float) -> List[WordTimestamp]:
    """Evenly distribute words across [start, end] when Whisper gives us text but no word timings."""
    words = text.split()
    if not words:
        return []
    duration = max(0.01, end - start)
    step = duration / len(words)
    result: List[WordTimestamp] = []
    for i, w in enumerate(words):
        result.append(
            {
                "word": w,
                "start": round(start + i * step, 2),
                "end": round(start + (i + 1) * step, 2),
            }
        )
    return result


def flatten_words(transcript: List[TranscriptSegment]) -> List[WordTimestamp]:
    """Flatten all word timestamps across every segment into one list."""
    words: List[WordTimestamp] = []
    for segment in transcript:
        words.extend(segment.get("words", []))
    return words


def words_in_range(transcript: List[TranscriptSegment], start: float, end: float) -> List[WordTimestamp]:
    """
    Return word timestamps that fall within [start, end] of the original
    source video, re-based so `start` becomes time zero. Useful for
    building per-clip caption data from a full-video transcript.
    """
    result: List[WordTimestamp] = []
    for word in flatten_words(transcript):
        if start <= word["start"] <= end:
            result.append(
                {
                    "word": word["word"],
                    "start": round(word["start"] - start, 2),
                    "end": round(word["end"] - start, 2),
                }
            )
    return result


def text_in_range(transcript: List[TranscriptSegment], start: float, end: float) -> str:
    """Return the concatenated transcript text overlapping [start, end]."""
    pieces = [
        segment["text"]
        for segment in transcript
        if segment["end"] >= start and segment["start"] <= end
    ]
    return " ".join(pieces).strip()
