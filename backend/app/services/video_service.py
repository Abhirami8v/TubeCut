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
    Download the best available video+audio stream for `url`
    into DOWNLOADS_DIR and return metadata.
    """

    base_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        # Retry configuration
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 10,

        # Network
        "socket_timeout": 30,
        "http_chunk_size": 10485760,
        "geo_bypass": True,

        # Browser-like headers
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    clients = ["android", "web", "ios"]

    info = None
    last_error = None

    for client in clients:
        opts = dict(base_opts)
        opts["extractor_args"] = {
            "youtube": {
                "player_client": [client]
            }
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                file_path = ydl.prepare_filename(info)

                requested = info.get("requested_downloads") or []

                if requested and requested[0].get("filepath"):
                    file_path = requested[0]["filepath"]

                if not Path(file_path).exists():
                    video_id = str(info.get("id", ""))

                    matches = sorted(
                        DOWNLOADS_DIR.glob(f"{video_id}.*"),
                        key=lambda path: path.stat().st_mtime,
                        reverse=True,
                    )

                    matches = [
                        p for p in matches
                        if p.suffix not in {".part", ".ytdl"}
                    ]

                    if not matches:
                        raise RuntimeError(
                            "yt-dlp completed but no downloaded file was found."
                        )

                    file_path = str(matches[0])

                duration = float(info.get("duration") or 0.0)

                return {
                    "video_id": info["id"],
                    "title": info.get("title", "Untitled video"),
                    "file_path": file_path,
                    "duration": duration,
                }

        except Exception as e:
            last_error = e

    clean_message = re.sub(r"\x1b\[[0-9;]*m", "", str(last_error))

    if "not a bot" in clean_message.lower():
        raise RuntimeError(
            "YouTube blocked this download. "
            "Try another public video or configure YouTube cookies."
        ) from last_error

    raise RuntimeError(
        f"Video download failed: {clean_message}"
    ) from last_error


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

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

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

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    streams = data.get("streams", [])

    if not streams:
        return (0, 0)

    return (
        int(streams[0].get("width", 0)),
        int(streams[0].get("height", 0)),
    )