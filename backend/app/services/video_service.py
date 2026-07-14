"""
video_service.py

Downloads YouTube videos using YouTube Data API v3 to get
stream URLs, then ffmpeg to download directly.
This bypasses yt-dlp's YouTube blocking issues on cloud servers.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import TypedDict

from app.core.config import DOWNLOADS_DIR, YOUTUBE_DATA_API_KEY
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg


class DownloadResult(TypedDict):
    video_id: str
    title: str
    file_path: str
    duration: float


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from any YouTube URL format."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([^&?\n/]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).strip()
    raise ValueError(f"Could not extract video ID from: {url}")


def _get_video_metadata(video_id: str, logger: JobLogger | None = None) -> dict:
    """Get video title and duration from YouTube Data API v3."""
    if not YOUTUBE_DATA_API_KEY:
        raise RuntimeError(
            "YOUTUBE_DATA_API_KEY is not set. "
            "Get one from https://console.cloud.google.com"
        )

    api_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={video_id}"
        f"&part=snippet,contentDetails"
        f"&key={YOUTUBE_DATA_API_KEY}"
    )

    if logger:
        logger.info(f"Fetching metadata from YouTube Data API for {video_id}")

    try:
        with urllib.request.urlopen(api_url, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        raise RuntimeError(f"YouTube Data API request failed: {e}")

    items = data.get("items", [])
    if not items:
        raise RuntimeError(
            f"Video {video_id} not found. "
            "It may be private, deleted, or region restricted."
        )

    item = items[0]
    title = item["snippet"]["title"]
    duration = _parse_iso_duration(item["contentDetails"]["duration"])

    if logger:
        logger.info(f"Video found: '{title}' ({duration:.0f}s)")

    return {"title": title, "duration": duration}


def _parse_iso_duration(duration_str: str) -> float:
    """Convert ISO 8601 duration PT1H2M3S to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0.0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


def _download_with_ytdlp(url: str, logger: JobLogger | None = None) -> dict:
    """Try yt-dlp with multiple client strategies."""
    import yt_dlp

    strategies = [
        {
            "extractor_args": {
                "youtube": {"player_client": ["android"]}
            }
        },
        {
            "extractor_args": {
                "youtube": {"player_client": ["ios"]}
            }
        },
        {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr"],
                    "player_skip": ["webpage"],
                }
            }
        },
        {
            "extractor_args": {
                "youtube": {"player_client": ["android_testsuite"]}
            }
        },
    ]

    video_id = _extract_video_id(url)
    output_path = DOWNLOADS_DIR / f"{video_id}.mp4"

    last_error = None
    for i, strategy in enumerate(strategies):
        if logger:
            logger.info(f"yt-dlp strategy {i+1}/{len(strategies)}: {strategy['extractor_args']['youtube']['player_client']}")

        ydl_opts = {
            "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
            "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            **strategy,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                if not file_path.endswith(".mp4"):
                    base = file_path.rpartition(".")[0]
                    file_path = f"{base}.mp4"

            if logger:
                logger.info(f"yt-dlp strategy {i+1} succeeded")

            return {
                "video_id": info["id"],
                "title": info.get("title", "Untitled"),
                "file_path": file_path,
                "duration": float(info.get("duration") or 0.0),
            }
        except Exception as e:
            last_error = e
            if logger:
                logger.warn(f"yt-dlp strategy {i+1} failed: {e}")
            continue

    raise RuntimeError(f"All yt-dlp strategies failed. Last error: {last_error}")


def _download_with_ffmpeg_direct(
    url: str,
    video_id: str,
    metadata: dict,
    logger: JobLogger | None = None,
) -> DownloadResult:
    """
    Use yt-dlp ONLY to get the direct stream URL (no download),
    then use ffmpeg to download it directly.
    This sometimes works when yt-dlp download is blocked.
    """
    import yt_dlp

    if logger:
        logger.info("Trying ffmpeg direct stream download strategy")

    ydl_opts = {
        "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,  # Don't download, just get URL
        "extractor_args": {
            "youtube": {"player_client": ["android", "ios"]}
        },
    }

    stream_url = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")
        if not stream_url and info.get("formats"):
            # Pick best format
            formats = [f for f in info["formats"] if f.get("url")]
            if formats:
                stream_url = formats[-1]["url"]

    if not stream_url:
        raise RuntimeError("Could not extract stream URL")

    output_path = DOWNLOADS_DIR / f"{video_id}.mp4"

    command = [
        "ffmpeg", "-y",
        "-user_agent", "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
        "-i", stream_url,
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]

    if logger:
        logger.info(f"Downloading stream via ffmpeg to {output_path}")

    run_ffmpeg(command, logger=logger, label="ffmpeg_stream_download")

    return {
        "video_id": video_id,
        "title": metadata["title"],
        "file_path": str(output_path),
        "duration": metadata["duration"],
    }


def download_video(url: str, logger: JobLogger | None = None) -> DownloadResult:
    from pytubefix import YouTube
    from pytubefix.cli import on_progress
    from app.core.config import PROXY_URL
    import yt_dlp
    from app.core.config import COOKIES_FILE, YT_DLP_PROXY
    if logger:
        logger.info(f"Downloading via pytubefix: {url}")

    try:
        # Build proxies dict if proxy is configured
        proxies = None
        if PROXY_URL:
            proxies = {
                "http": PROXY_URL,
                "https": PROXY_URL,
            }
            if logger:
                logger.info(f"Using proxy: {PROXY_URL}")

        yt = YouTube(
            url,
            on_progress_callback=on_progress,
            use_oauth=False,
            allow_oauth_cache=True,
            proxies=proxies,
        )

        title = yt.title
        duration = float(yt.length or 0)
        video_id = yt.video_id

        if logger:
            logger.info(f"Video found: '{title}' ({duration:.0f}s)")

        # Get best progressive stream (video + audio combined)
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

        if logger:
            logger.info(f"Downloading: {stream.resolution}")

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
        raise RuntimeError(f"Could not download video: {e}")


def probe_duration(file_path: str, logger: JobLogger | None = None) -> float:
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path,
    ]
    stdout = run_ffmpeg(command, logger=logger, label="probe_duration")
    data = json.loads(stdout)
    return float(data.get("format", {}).get("duration", 0.0))


def probe_dimensions(file_path: str, logger: JobLogger | None = None) -> tuple[int, int]:
    command = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        file_path,
    ]
    stdout = run_ffmpeg(command, logger=logger, label="probe_dimensions")
    data = json.loads(stdout)
    streams = data.get("streams", [])
    if not streams:
        return (0, 0)
    return (int(streams[0].get("width", 0)), int(streams[0].get("height", 0)))


def probe_fps(file_path: str, logger: JobLogger | None = None) -> float:
    command = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "json",
        file_path,
    ]
    stdout = run_ffmpeg(command, logger=logger, label="probe_fps")
    data = json.loads(stdout)
    streams = data.get("streams", [])
    if not streams:
        return 30.0
    rate_str = streams[0].get("r_frame_rate", "30/1")
    try:
        num, den = rate_str.split("/")
        return float(num) / float(den) if float(den) != 0 else 30.0
    except (ValueError, ZeroDivisionError):
        return 30.0