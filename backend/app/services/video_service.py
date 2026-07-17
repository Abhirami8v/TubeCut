"""
video_service.py
Downloads YouTube videos using pytubefix.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from pytubefix import YouTube

from app.core.config import DOWNLOADS_DIR
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg


class DownloadResult(TypedDict):
    video_id: str
    title: str
    file_path: str
    duration: float


def _extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/|shorts/|embed/)([^&?/]+)"
    ]

    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)

    raise ValueError(f"Invalid YouTube URL: {url}")


def download_video(url: str, logger: JobLogger | None = None) -> DownloadResult:
    from pytubefix import YouTube
    from pytubefix.cli import on_progress

    if logger:
        logger.info(f"Downloading via pytubefix with OAuth: {url}")

    try:
        yt = YouTube(
            url,
            on_progress_callback=on_progress,
            use_oauth=True,
            allow_oauth_cache=True,
            client="WEB",
        )

        title = yt.title
        duration = float(yt.length or 0)
        video_id = yt.video_id

        if logger:
            logger.info(f"Video found: '{title}' ({duration:.0f}s)")

        stream = (
            yt.streams
            .filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .last()
        )

        if not stream:
            stream = yt.streams.filter(file_extension="mp4").first()

        if not stream:
            raise RuntimeError("No downloadable stream found")

        output_path = DOWNLOADS_DIR / f"{video_id}.mp4"

        stream.download(
            output_path=str(DOWNLOADS_DIR),
            filename=f"{video_id}.mp4"
        )

        if logger:
            logger.info(f"Download complete: {output_path}")

        return {
            "video_id": video_id,
            "title": title,
            "file_path": str(output_path),
            "duration": duration,
        }

    except Exception as e:
        if logger:
            logger.error(f"pytubefix failed: {e}")

        # Fallback to yt-dlp
        if logger:
            logger.info("Trying yt-dlp fallback...")
        return _download_with_ytdlp(url, logger=logger)


def _download_with_ytdlp(url: str, logger: JobLogger | None = None) -> DownloadResult:
    import yt_dlp
    from app.core.config import PROXY_URL

    video_id = _extract_video_id(url)

    ydl_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }

    if PROXY_URL:
        ydl_opts["proxy"] = PROXY_URL
        if logger:
            logger.info(f"Using proxy for yt-dlp")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith(".mp4"):
            base = file_path.rpartition(".")[0]
            file_path = f"{base}.mp4"

    if logger:
        logger.info(f"yt-dlp download complete: {file_path}")

    return {
        "video_id": info["id"],
        "title": info.get("title", "Untitled"),
        "file_path": file_path,
        "duration": float(info.get("duration") or 0.0),
    }


def probe_duration(file_path: str, logger: JobLogger | None = None) -> float:
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

    stdout = run_ffmpeg(command, logger=logger, label="probe_duration")
    data = json.loads(stdout)

    return float(data.get("format", {}).get("duration", 0))


def probe_dimensions(file_path: str, logger: JobLogger | None = None):
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

    stdout = run_ffmpeg(command, logger=logger, label="probe_dimensions")
    data = json.loads(stdout)

    streams = data.get("streams", [])

    if not streams:
        return (0, 0)

    return (
        int(streams[0]["width"]),
        int(streams[0]["height"]),
    )


def probe_fps(file_path: str, logger: JobLogger | None = None):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "json",
        file_path,
    ]

    stdout = run_ffmpeg(command, logger=logger, label="probe_fps")
    data = json.loads(stdout)

    streams = data.get("streams", [])

    if not streams:
        return 30.0

    rate = streams[0]["r_frame_rate"]

    try:
        num, den = rate.split("/")
        return float(num) / float(den)
    except Exception:
        return 30.0