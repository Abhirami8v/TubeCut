"""
video_service.py

Downloads YouTube videos using yt-dlp with multiple fallback strategies
to handle cloud server IP blocking by YouTube.

Strategy order:
1. Try yt-dlp with android client (works on most servers)
2. Try yt-dlp with web client + po_token workaround
3. Try YouTube Data API v3 to get direct stream URL
4. Raise clear error explaining the situation
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import TypedDict

import yt_dlp

from app.core.config import DOWNLOADS_DIR, YOUTUBE_DATA_API_KEY, COOKIES_FILE, YT_DLP_PROXY, YT_DLP_PO_TOKEN
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg


def _build_ydl_opts(base_opts: dict, logger: JobLogger | None = None) -> dict:
    ydl_opts = base_opts.copy()
    
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE
        if logger:
            logger.info(f"Using cookies file: {COOKIES_FILE}")
            
    if YT_DLP_PROXY:
        ydl_opts["proxy"] = YT_DLP_PROXY
        if logger:
            logger.info(f"Using proxy: {YT_DLP_PROXY}")

    if YT_DLP_PO_TOKEN:
        if "extractor_args" not in ydl_opts:
            ydl_opts["extractor_args"] = {}
        if "youtube" not in ydl_opts["extractor_args"]:
            ydl_opts["extractor_args"]["youtube"] = {}
        
        ydl_opts["extractor_args"]["youtube"]["po_token"] = YT_DLP_PO_TOKEN
        # If PO token is used, web client is often necessary
        if "player_client" not in ydl_opts["extractor_args"]["youtube"]:
            ydl_opts["extractor_args"]["youtube"]["player_client"] = ["web", "android"]
        elif "web" not in ydl_opts["extractor_args"]["youtube"]["player_client"]:
            ydl_opts["extractor_args"]["youtube"]["player_client"].append("web")
            
        if logger:
            logger.info("Using configured PO Token for yt-dlp")
            
    return ydl_opts


class DownloadResult(TypedDict):
    video_id: str
    title: str
    file_path: str
    duration: float


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/)([^&?\n]+)',
        r'(?:youtube\.com/shorts/)([^&?\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def _get_video_info_from_api(video_id: str, logger: JobLogger | None = None) -> dict:
    """
    Get video metadata (title, duration) from YouTube Data API v3.
    """
    if not YOUTUBE_DATA_API_KEY:
        raise RuntimeError("YOUTUBE_DATA_API_KEY is not set in environment variables")

    api_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={video_id}"
        f"&part=snippet,contentDetails"
        f"&key={YOUTUBE_DATA_API_KEY}"
    )

    if logger:
        logger.debug(f"Fetching video info from YouTube Data API for video_id={video_id}")

    with urllib.request.urlopen(api_url) as response:
        data = json.loads(response.read().decode())

    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"Video {video_id} not found via YouTube Data API")

    item = items[0]
    title = item["snippet"]["title"]

    # Parse ISO 8601 duration (PT1H2M3S format)
    duration_str = item["contentDetails"]["duration"]
    duration = _parse_iso_duration(duration_str)

    return {"title": title, "duration": duration}


def _parse_iso_duration(duration_str: str) -> float:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0.0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


def _download_with_ytdlp(
    url: str,
    extra_opts: dict | None = None,
    logger: JobLogger | None = None
) -> dict:
    """Try downloading with yt-dlp, returns info dict or raises."""
    base_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }

    if extra_opts:
        # Merge dictionary objects like extractor_args instead of simple overwrite
        if "extractor_args" in extra_opts and "extractor_args" in base_opts:
            for k, v in extra_opts["extractor_args"].items():
                if k in base_opts["extractor_args"]:
                    base_opts["extractor_args"][k].update(v)
                else:
                    base_opts["extractor_args"][k] = v
            # Copy other keys
            for k, v in extra_opts.items():
                if k != "extractor_args":
                    base_opts[k] = v
        else:
            base_opts.update(extra_opts)

    ydl_opts = _build_ydl_opts(base_opts, logger=logger)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith(".mp4"):
            base = file_path.rpartition(".")[0]
            file_path = f"{base}.mp4"

    return {
        "video_id": info["id"],
        "title": info.get("title", "Untitled"),
        "file_path": file_path,
        "duration": float(info.get("duration") or 0.0),
    }


def _download_via_api_stream(
    url: str,
    video_id: str,
    logger: JobLogger | None = None
) -> DownloadResult:
    """
    Get video info from YouTube Data API, then use yt-dlp just for
    the actual stream extraction (more reliable on cloud servers than
    full yt-dlp metadata extraction).
    """
    if logger:
        logger.info("Trying YouTube Data API strategy for metadata + yt-dlp for stream")

    # Get metadata from API
    api_info = _get_video_info_from_api(video_id, logger=logger)

    # Use yt-dlp with aggressive client fallbacks just for downloading
    base_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "android", "ios", "web"],
                "player_skip": ["webpage"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
        },
    }

    ydl_opts = _build_ydl_opts(base_opts, logger=logger)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith(".mp4"):
            base = file_path.rpartition(".")[0]
            file_path = f"{base}.mp4"

    return {
        "video_id": video_id,
        "title": api_info["title"],
        "file_path": file_path,
        "duration": api_info["duration"] or float(info.get("duration") or 0.0),
    }


def download_video(url: str, logger: JobLogger | None = None) -> DownloadResult:
    """
    Download YouTube video with multiple fallback strategies.
    Tries each strategy in order until one succeeds.
    """
    video_id = _extract_video_id(url)

    # Strategy 1: Standard yt-dlp with android client
    if logger:
        logger.info(f"Strategy 1: yt-dlp android client for video_id={video_id}")
    try:
        result = _download_with_ytdlp(url, logger=logger)
        if logger:
            logger.info(f"Strategy 1 succeeded: {result['title']}")
        return result
    except Exception as e1:
        if logger:
            logger.warn(f"Strategy 1 failed: {e1}")

    # Strategy 2: yt-dlp with different player clients
    if logger:
        logger.info("Strategy 2: yt-dlp with ios + android_vr clients")
    try:
        result = _download_with_ytdlp(url, extra_opts={
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android_vr", "android_testsuite"],
                }
            }
        }, logger=logger)
        if logger:
            logger.info(f"Strategy 2 succeeded: {result['title']}")
        return result
    except Exception as e2:
        if logger:
            logger.warn(f"Strategy 2 failed: {e2}")

    # Strategy 3: YouTube Data API + yt-dlp stream
    if logger:
        logger.info("Strategy 3: YouTube Data API + yt-dlp stream extraction")
    try:
        result = _download_via_api_stream(url, video_id, logger=logger)
        if logger:
            logger.info(f"Strategy 3 succeeded: {result['title']}")
        return result
    except Exception as e3:
        if logger:
            logger.warn(f"Strategy 3 failed: {e3}")

    # All strategies failed
    raise RuntimeError(
        f"All download strategies failed for {url}.\n"
        f"Strategy 1 (android): {e1}\n"
        f"Strategy 2 (ios/vr): {e2}\n"
        f"Strategy 3 (API+stream): {e3}\n"
        "This usually means YouTube is blocking downloads from this server's IP address. "
        "Consider using a proxy or accepting video file uploads instead."
    )


def probe_duration(file_path: str, logger: JobLogger | None = None) -> float:
    """Return the duration (seconds) of a media file via ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path,
    ]
    stdout = run_ffmpeg(command, logger=logger, label="probe_duration")
    data = json.loads(stdout)
    return float(data.get("format", {}).get("duration", 0.0))


def probe_dimensions(file_path: str, logger: JobLogger | None = None) -> tuple[int, int]:
    """Return (width, height) of the first video stream."""
    command = [
        "ffprobe",
        "-v", "error",
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
    """Return the frame rate of the first video stream."""
    command = [
        "ffprobe",
        "-v", "error",
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