"""
Cleanup service for deleting old source videos and temporary files to optimize disk space.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.core.config import DOWNLOADS_DIR, AUDIO_DIR, LOGS_DIR


def cleanup_old_files() -> None:
    """
    Scans storage directories and removes downloaded source videos that are older
    than CLEANUP_DAYS. Also cleans up temporary files and old logs.
    """
    cleanup_days = int(os.getenv("CLEANUP_DAYS", "3"))
    now = time.time()
    max_age_seconds = cleanup_days * 24 * 3600

    print(f"[Cleanup] Running storage cleanup (threshold: {cleanup_days} days)...")

    # 1. Clean up old downloaded source videos
    if DOWNLOADS_DIR.exists():
        for path in DOWNLOADS_DIR.glob("*"):
            if path.is_file():
                # Avoid deleting cookies or system files
                if path.name == "cookies.txt":
                    continue
                file_age = now - path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        path.unlink()
                        print(f"[Cleanup] Deleted old source video: {path.name}")
                    except Exception as e:
                        print(f"[Cleanup] Error deleting source video {path.name}: {e}")

    # 2. Clean up temporary audio files (should be deleted immediately, but keep as fallback)
    if AUDIO_DIR.exists():
        for path in AUDIO_DIR.glob("*"):
            if path.is_file():
                file_age = now - path.stat().st_mtime
                if file_age > 3600 * 2:  # 2 hours
                    try:
                        path.unlink()
                    except Exception:
                        pass

    # 3. Clean up log files older than 7 days
    if LOGS_DIR.exists():
        for path in LOGS_DIR.glob("*"):
            if path.is_file():
                file_age = now - path.stat().st_mtime
                if file_age > 7 * 24 * 3600:
                    try:
                        path.unlink()
                    except Exception:
                        pass
