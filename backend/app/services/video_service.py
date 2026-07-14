"""
video_service.py
Downloads YouTube videos using yt-dlp with proxy + cookies.
pytubefix completely removed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import TypedDict

from app.core.config import DOWNLOADS_DIR
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg


class DownloadResult(TypedDict):
    video_id: str
    title: str
    file_path: str
    duration: float


def _extract_video_id(url: str) -> str:
    patterns = [r'(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([^&?\n/]+)']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).strip()
    raise ValueError(f"Could not extract video ID from: {url}")


def download_video(url: str, logger: JobLogger | None = None) -> DownloadResult:
    import yt_dlp
    from app.core.config import COOKIES_FILE, YT_DLP_PROXY

    if logger:
        logger.info(f"Downloading: {url}")
        logger.info(f"Proxy: {YT_DLP_PROXY or 'none'}")
        logger.info(f"Cookies: {COOKIES_FILE or 'none'}")

    base_opts = {
        "outtmpl":             str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format":              "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist":          True,
        "quiet":               True,
        "no_warnings":         True,
        "retries":             5,
        "fragment_retries":    5,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        },
    }

    if YT_DLP_PROXY:
        base_opts["proxy"] = YT_DLP_PROXY

    if COOKIES_FILE:
        base_opts["cookiefile"] = COOKIES_FILE

    strategies = [
        {"extractor_args": {"youtube": {"player_client": ["web"]}}},
        {"extractor_args": {"youtube": {"player_client": ["android"]}}},
        {"extractor_args": {"youtube": {"player_client": ["ios"]}}},
        {"extractor_args": {"youtube": {"player_client": ["android_vr"]}}},
        {"extractor_args": {"youtube": {"player_client": ["android_testsuite"]}}},
        {},
    ]

    last_error = None

    for i, strategy in enumerate(strategies):
        ydl_opts = {**base_opts, **strategy}
        client = strategy.get("extractor_args", {}).get("youtube", {}).get("player_client", ["default"])[0] if strategy else "default"

        if logger:
            logger.info(f"Attempt {i+1}/{len(strategies)} — client: {client}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info      = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                if not file_path.endswith(".mp4"):
                    base      = file_path.rpartition(".")[0]
                    file_path = f"{base}.mp4"

                if not os.path.isfile(file_path):
                    raise RuntimeError(f"File not found after download: {file_path}")

                if logger:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    logger.info(f"Download complete: {file_path} ({size_mb:.1f} MB)")

                return {
                    "video_id":  info["id"],
                    "title":     info.get("title", "Untitled"),
                    "file_path": file_path,
                    "duration":  float(info.get("duration") or 0.0),
                }

        except Exception as e:
            last_error = e
            if logger:
                logger.warn(f"Attempt {i+1} failed: {e}")
            continue

    raise RuntimeError(
        f"All download strategies failed. "
        f"Make sure YT_DLP_PROXY is set in Railway variables. "
        f"Last error: {last_error}"
    )


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