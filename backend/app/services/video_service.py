"""
video_service.py

Responsible for resolving a YouTube/video URL into a local source video
file using yt-dlp, plus lightweight metadata probing (duration) via
ffprobe so the rest of the pipeline can reason about the source.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import TypedDict

import yt_dlp

from app.core.config import DOWNLOADS_DIR


class DownloadResult(TypedDict):
    video_id: str
    title: str
    file_path: str
    duration: float


def download_video(url: str) -> DownloadResult:
    """
    Download the best available video+audio stream for `url` into
    DOWNLOADS_DIR and return metadata about the downloaded file.
    """
    ydl_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        # `bestvideo+bestaudio` became brittle as YouTube moved more
        # playback behind SABR/player-specific formats. The starred
        # selector also accepts a combined A/V stream and then falls back
        # through progressively broader choices.
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "concurrent_fragment_downloads": 4,
        "js_runtimes": {"node": {}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            requested = info.get("requested_downloads") or []
            if requested and requested[0].get("filepath"):
                file_path = requested[0]["filepath"]

            # Post-processing may change the extension. Resolve the actual
            # downloaded file instead of assuming that an .mp4 exists.
            if not Path(file_path).exists():
                video_id = str(info.get("id", ""))
                matches = sorted(
                    DOWNLOADS_DIR.glob(f"{video_id}.*"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                matches = [path for path in matches if path.suffix not in {".part", ".ytdl"}]
                if not matches:
                    raise RuntimeError("yt-dlp completed but no downloaded video file was found")
                file_path = str(matches[0])
    except yt_dlp.utils.DownloadError as exc:
        clean_message = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
        raise RuntimeError(
            f"Video download failed: {clean_message}. Update yt-dlp and try again."
        ) from exc

    duration = float(info.get("duration") or 0.0)

    return {
        "video_id": info["id"],
        "title": info.get("title", "Untitled video"),
        "file_path": file_path,
        "duration": duration,
    }


def probe_duration(file_path: str) -> float:
    """Return the duration (seconds) of a media file via ffprobe."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        file_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0.0))


def probe_dimensions(file_path: str) -> tuple[int, int]:
    """Return (width, height) of the first video stream."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        file_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        return (0, 0)
    return (int(streams[0].get("width", 0)), int(streams[0].get("height", 0)))
