"""
ffmpeg_utils.py
Shared subprocess wrapper for every ffmpeg/ffprobe invocation.
Memory-optimized to prevent log buffering in RAM.
"""

from __future__ import annotations

import subprocess
import time
from collections import deque

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
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,  # line buffered
    )

    is_probe = len(command) > 0 and "ffprobe" in command[0]

    if is_probe:
        # Probe commands write to stdout, are tiny, and exit quickly.
        stdout, stderr = process.communicate()
        stderr_str = stderr
    else:
        # FFmpeg encoding commands write verbosely to stderr.
        # We read line-by-line to prevent log buffer accumulation in RAM.
        stderr_deque = deque(maxlen=15)
        while True:
            line = process.stderr.readline()
            if not line:
                break
            stderr_deque.append(line)
        
        # Wait for the process to exit completely
        stdout, _ = process.communicate()
        stderr_str = "".join(stderr_deque)

    elapsed = time.time() - start
    returncode = process.returncode

    if returncode != 0:
        if logger:
            logger.ffmpeg_error(command, stderr_str)
        else:
            print(f"[ffmpeg_utils] {label} FAILED after {elapsed:.1f}s: {stderr_str[-2000:]}")
        raise FFmpegError(command, returncode, stderr_str)

    if logger:
        logger.debug(f"{label} completed in {elapsed:.1f}s")

    return stdout