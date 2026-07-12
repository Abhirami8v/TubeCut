"""
clip_service.py

Handles cutting individual clips out of the source video (trim/crop) via
ffmpeg, generating thumbnails, and rendering final captioned clips in a
single FFmpeg pass.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

from app.core.config import (
    CLIPS_DIR,
    FINAL_DIR,
    THUMBNAILS_DIR,
    REFRAME_TARGET_HEIGHT,
    REFRAME_TARGET_WIDTH,
    FAST_ENCODE_PRESET,
    FINAL_ENCODE_PRESET,
)
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg


def render_raw_clip(source_video_path: str, start_time: float, end_time: float, clip_id: str | None = None) -> str:
    """
    Cut [start_time, end_time] out of `source_video_path` with re-encode
    (not stream-copy) so the cut lands on the exact requested boundary.
    Returns the output file path.
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
        FAST_ENCODE_PRESET,
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
    Re-render a clip's raw cut after the user adjusts the trim window in the editor.
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


def render_uncaptioned_clip(
    source_video_path: str,
    trim_start_time: float,
    trim_end_time: float,
    clip_id: str,
    auto_reframe: bool,
    logger: JobLogger | None = None,
) -> str:
    """
    Trims and crops/scales the clip from the original source video (uncaptioned).
    Returns the path to the uncaptioned video file.
    """
    duration = max(0.1, trim_end_time - trim_start_time)

    if auto_reframe:
        output_path = CLIPS_DIR / f"reframed_{clip_id}.mp4"
        from app.services import reframe_service
        crop_expr, crop_width = reframe_service.get_crop_expr_for_clip(
            clip_id, source_video_path, trim_start_time, duration, logger=logger
        )
        escaped_crop_expr = crop_expr.replace(",", "\\,")

        from app.services import video_service
        _, video_height = video_service.probe_dimensions(source_video_path, logger=logger)
        video_height = video_height or 1080

        filter_str = (
            f"crop={crop_width}:{video_height}:{escaped_crop_expr}:0,"
            f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
        )
    else:
        output_path = CLIPS_DIR / f"clip_{clip_id}.mp4"
        filter_str = ""

    command = [
        "ffmpeg", "-y",
        "-ss", f"{trim_start_time:.3f}",
        "-t", f"{duration:.3f}",
        "-i", source_video_path,
    ]
    if filter_str:
        command.extend(["-vf", filter_str])

    command.extend([
        "-c:v", "libx264",
        "-preset", FAST_ENCODE_PRESET,
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-tag:v", "avc1",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(output_path),
    ])

    run_ffmpeg(command, logger=logger, label=f"render_uncaptioned_clip[{clip_id}]")
    return str(output_path)


def render_captioned_only(
    uncaptioned_path: str,
    clip_id: str,
    applied_style: dict | None = None,
    caption_blocks: list[dict] | None = None,
    logger: JobLogger | None = None,
) -> str:
    """
    Burns captions on top of the already trimmed and cropped uncaptioned video.
    Returns the path to the final captioned video file.
    """
    output_path = FINAL_DIR / f"final_{clip_id}.mp4"

    has_captions = bool(applied_style and caption_blocks)
    if not has_captions:
        # If no captions, simply copy the uncaptioned clip
        import shutil
        try:
            shutil.copy2(uncaptioned_path, output_path)
            return str(output_path)
        except Exception as e:
            if logger:
                logger.error(f"Failed to copy uncaptioned clip: {e}")
            return uncaptioned_path

    # Get dimensions of uncaptioned video
    from app.services import video_service
    video_width, video_height = video_service.probe_dimensions(uncaptioned_path, logger=logger)
    video_width = video_width or REFRAME_TARGET_WIDTH
    video_height = video_height or REFRAME_TARGET_HEIGHT

    # Write ASS file
    from app.services import caption_burn_service, caption_service
    ass_content = caption_service.generate_ass_file(
        caption_blocks, applied_style, video_width, video_height
    )
    ass_path = caption_burn_service.write_ass_file(ass_content, clip_id)

    use_ass_filter = caption_burn_service._ffmpeg_has_filter("ass")

    if use_ass_filter:
        try:
            rel_path = Path(ass_path).relative_to(Path.cwd())
            escaped_ass_path = str(rel_path).replace("\\", "/")
            escaped_ass_path = escaped_ass_path.replace("'", "'\\\\''")
            filter_arg = f"ass=filename='{escaped_ass_path}'"
        except ValueError:
            escaped_ass_path = ass_path.replace("\\", "/")
            escaped_ass_path = escaped_ass_path.replace("'", "'\\\\''")
            escaped_ass_path = escaped_ass_path.replace(":", "\\:")
            filter_arg = f"ass=filename='{escaped_ass_path}'"

        command = [
            "ffmpeg", "-y",
            "-i", uncaptioned_path,
            "-vf", filter_arg,
            "-c:v", "libx264",
            "-preset", FINAL_ENCODE_PRESET,
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-tag:v", "avc1",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        run_ffmpeg(command, logger=logger, label=f"render_captioned_only[{clip_id}]")
        return str(output_path)
    else:
        # Pillow fallback
        return caption_burn_service._burn_with_image_overlays(
            uncaptioned_path,
            output_path,
            caption_blocks,
            applied_style,
            video_width,
            video_height,
            clip_id,
        )
