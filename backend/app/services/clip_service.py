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


def render_clip_final(
    source_video_path: str,
    trim_start_time: float,
    trim_end_time: float,
    clip_id: str,
    auto_reframe: bool,
    applied_style: dict | None = None,
    caption_blocks: list[dict] | None = None,
    logger: JobLogger | None = None,
) -> str:
    """
    Renders the final trimmed, reframed, and captioned video in a single FFmpeg pass.
    Bypasses any intermediate file writes and minimizes decoding.
    """
    duration = max(0.1, trim_end_time - trim_start_time)
    output_path = FINAL_DIR / f"final_{clip_id}.mp4"

    from app.services import video_service
    video_width, video_height = video_service.probe_dimensions(source_video_path, logger=logger)
    video_width = video_width or 1920
    video_height = video_height or 1080

    target_width, target_height = video_width, video_height
    if auto_reframe:
        target_width, target_height = REFRAME_TARGET_WIDTH, REFRAME_TARGET_HEIGHT

    # 1. Handle reframing coordinates
    crop_expr = None
    crop_width = video_width
    if auto_reframe:
        from app.services import reframe_service
        crop_expr, crop_width = reframe_service.get_crop_expr_for_clip(
            clip_id, source_video_path, trim_start_time, duration, logger=logger
        )

    # 2. Handle subtitles/captions
    has_captions = bool(applied_style and caption_blocks)
    use_ass_filter = False
    ass_path = None

    if has_captions:
        from app.services import caption_burn_service, caption_service
        ass_content = caption_service.generate_ass_file(
            caption_blocks, applied_style, target_width, target_height
        )
        ass_path = caption_burn_service.write_ass_file(ass_content, clip_id)
        use_ass_filter = caption_burn_service._ffmpeg_has_filter("ass")

    # 3. Construct filter complex
    filter_complex = []
    if auto_reframe and crop_expr:
        filter_complex.append(f"crop={crop_width}:{video_height}:{crop_expr}:0")
        filter_complex.append(f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}")

    if has_captions and use_ass_filter and ass_path:
        # Escape ASS path for FFmpeg
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
        filter_complex.append(filter_arg)

    filter_str = ",".join(filter_complex)

    # 4. Standard path: Single-pass FFmpeg run
    if not has_captions or use_ass_filter:
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
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-tag:v", "avc1",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            str(output_path),
        ])

        run_ffmpeg(command, logger=logger, label=f"render_clip_final[{clip_id}]")
        return str(output_path)

    # 5. Fallback path: libass is missing, burn overlays with Pillow
    else:
        from app.services import caption_burn_service
        temp_output = CLIPS_DIR / f"temp_{clip_id}.mp4"

        # Step 1: Render the video crop/scale
        command = [
            "ffmpeg", "-y",
            "-ss", f"{trim_start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-i", source_video_path,
        ]
        if filter_complex:
            # Join only reframe filters
            reframe_filter = ",".join(filter_complex)
            command.extend(["-vf", reframe_filter])

        command.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-tag:v", "avc1",
            "-c:a", "aac",
            "-b:a", "160k",
            str(temp_output),
        ])
        run_ffmpeg(command, logger=logger, label=f"render_clip_fallback_trim[{clip_id}]")

        # Step 2: Burn Pillow overlays on the trimmed video
        final_path = caption_burn_service._burn_with_image_overlays(
            str(temp_output),
            output_path,
            caption_blocks,
            applied_style,
            target_width,
            target_height,
            clip_id,
        )

        # Clean up temp
        try:
            os.remove(temp_output)
        except OSError:
            pass

        return final_path
