"""
logging_utils.py

Lightweight structured logging for the pipeline.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

from app.core.config import LOGS_DIR, VERBOSE_PIPELINE_LOGGING


class JobLogger:
    """Per-job logger that writes to both stdout and a dedicated log file."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.log_path = LOGS_DIR / f"{job_id}.log"

    def _write(self, level: str, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] [{self.job_id[:8]}] {message}"
        print(line, flush=True)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warn(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def debug(self, message: str) -> None:
        if VERBOSE_PIPELINE_LOGGING:
            self._write("DEBUG", message)

    @contextmanager
    def step(self, step_name: str):
        start = time.time()
        self.info(f"START  {step_name}")
        try:
            yield
        except Exception as exc:
            elapsed = time.time() - start
            self.error(f"FAILED {step_name} after {elapsed:.1f}s -- {type(exc).__name__}: {exc}")
            raise
        else:
            elapsed = time.time() - start
            self.info(f"DONE   {step_name} in {elapsed:.1f}s")

    def ffmpeg_error(self, command: list[str], stderr: str) -> None:
        self.error(f"ffmpeg command failed: {' '.join(command)}")
        tail_lines = stderr.strip().splitlines()[-40:]
        for line in tail_lines:
            self.error(f"  ffmpeg: {line}")