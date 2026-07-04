"""
ffmpeg_utils.py
Shared subprocess wrapper for every ffmpeg/ffprobe invocation.
"""

from __future__ import annotations

import subprocess
import time

from app.core.logging_utils import JobLogger


class FFmpegError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        tail = "\n".join(stderr.strip().splitlines()[-15:])
        super().__init__(f"ffmpeg exited {returncode}: {tail}")


def run_ffmpeg(command: list[str], logger: JobLogger | None = None, label: str = "ffmpeg") -> str:
    start = time.time()
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        if logger:
            logger.ffmpeg_error(command, result.stderr)
        else:
            print(f"[ffmpeg_utils] {label} FAILED after {elapsed:.1f}s: {result.stderr[-2000:]}")
        raise FFmpegError(command, result.returncode, result.stderr)

    if logger:
        logger.debug(f"{label} completed in {elapsed:.1f}s")

    return result.stdout