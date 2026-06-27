"""
clip_service.py

Handles cutting individual clips out of the source video (trim/crop) via
ffmpeg, generating thumbnails, and re-rendering when the user adjusts
the trim window from the editor. This module never burns in captions --
that's caption_service.py's job, composed on top of whatever this module
produces (raw_clip_path or reframed_clip_path).
"""

from __future__ import annotations

import subprocess
import uuid

from app.core.config import CLIPS_DIR, THUMBNAILS_DIR


def render_raw_clip(source_video_path: str, start_time: float, end_time: float, clip_id: str | None = None) -> str:
    """
    Cut [start_time, end_time] out of `source_video_path` with re-encode
    (not stream-copy) so the cut lands on the exact requested boundary
    rather than the nearest keyframe. Returns the output file path.
    """
    suffix = clip_id or uuid.uuid4().hex[:8]
    output_path = CLIPS_DIR / f"clip_{suffix}.mp4"
    duration = max(0.1, end_time - start_time)

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_time:.3f}",
        "-i",
        source_video_path,
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-tag:v",
        "avc1",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    subprocess.run(command, check=True, capture_output=True)
    return str(output_path)


def retrim_clip(source_video_path: str, absolute_start: float, absolute_end: float, clip_id: str) -> str:
    """
    Re-render a clip's raw cut after the user adjusts the trim window in
    the editor. `absolute_start`/`absolute_end` are times within the
    ORIGINAL source video (i.e. job.source_start_time + per-clip trim
    offset), not relative to the previous cut.
    """
    return render_raw_clip(source_video_path, absolute_start, absolute_end, clip_id=f"{clip_id}_trim")


def generate_thumbnail(clip_path: str, clip_id: str, at_seconds: float = 0.5) -> str:
    """Grab a single frame from `clip_path` as a JPEG thumbnail."""
    output_path = THUMBNAILS_DIR / f"thumb_{clip_id}.jpg"

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{at_seconds:.3f}",
        "-i",
        clip_path,
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(output_path),
    ]

    subprocess.run(command, check=True, capture_output=True)
    return str(output_path)
