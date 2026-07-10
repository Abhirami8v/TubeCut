"""
reframe_service.py

Memory-efficient vertical reframe pipeline designed for 512MB RAM limit.

Pipeline:
  Python → YOLO (sample frames) → 10 crop positions → 10 tiny ffmpeg jobs → concat → finished

Key optimizations for 512MB:
- YOLO runs on heavily downscaled frames (320px wide)
- Only 10 sample points across the whole clip
- Each ffmpeg segment is tiny (processes only its own chunk)
- No frames loaded into memory simultaneously
- Concat is a simple ffmpeg demuxer (no re-encode)
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List, TypedDict

from app.core.config import (
    CLIPS_DIR,
    REFRAME_SMOOTHING_ALPHA,
    REFRAME_TARGET_HEIGHT,
    REFRAME_TARGET_WIDTH,
    STORAGE_DIR,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_WEIGHTS_PATH,
)
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import FFmpegError, run_ffmpeg
from app.services.video_service import probe_dimensions

_yolo_model = None

NUM_SAMPLE_POINTS = 10  # exactly 10 crop positions across the clip
YOLO_SAMPLE_WIDTH = 320  # tiny frames for YOLO — saves RAM dramatically


class CropKeyframe(TypedDict):
    time: float
    crop_x: int


class ReframeError(RuntimeError):
    pass


def _get_yolo_model(logger: JobLogger | None = None):
    global _yolo_model
    if _yolo_model is None:
        weights = Path(YOLO_WEIGHTS_PATH)
        if not weights.exists() and logger:
            logger.info(f"Downloading YOLO weights to {weights}")
        from ultralytics import YOLO
        _yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    return _yolo_model


def _sample_frames_with_ffmpeg(
    video_path: str,
    num_samples: int,
    duration: float,
    out_dir: Path,
    logger: JobLogger | None = None,
) -> List[Path]:
    """
    Extract exactly num_samples frames evenly spaced across the clip
    using ffmpeg. Frames are saved at YOLO_SAMPLE_WIDTH px wide to
    minimize memory usage. Returns list of frame paths.
    """
    frame_paths = []

    for i in range(num_samples):
        # Evenly space sample points across the clip
        t = (i / max(num_samples - 1, 1)) * duration
        t = min(t, duration - 0.1)

        frame_path = out_dir / f"frame_{i:03d}.jpg"

        command = [
            "ffmpeg", "-y",
            "-ss", f"{t:.3f}",
            "-i", video_path,
            "-frames:v", "1",
            "-vf", f"scale={YOLO_SAMPLE_WIDTH}:-1",
            "-q:v", "5",
            str(frame_path),
        ]

        try:
            run_ffmpeg(command, logger=logger, label=f"sample_frame_{i}")
            if frame_path.exists():
                frame_paths.append(frame_path)
        except FFmpegError:
            if logger:
                logger.warn(f"Could not extract frame at t={t:.2f}s")

    if logger:
        logger.info(f"Extracted {len(frame_paths)}/{num_samples} sample frames")

    return frame_paths


def _detect_crop_positions(
    frame_paths: List[Path],
    src_width: int,
    src_height: int,
    crop_width: int,
    duration: float,
    logger: JobLogger | None = None,
) -> List[CropKeyframe]:
    """
    Run YOLO on each sampled frame to find person position.
    Returns 10 crop keyframes with smoothed x positions.
    """
    from PIL import Image

    model = _get_yolo_model(logger)
    num_samples = len(frame_paths)

    raw_centers: List[float] = []

    for i, frame_path in enumerate(frame_paths):
        try:
            # Load tiny frame - minimal RAM usage
            img = Image.open(frame_path)
            frame_w, frame_h = img.size

            results = model.predict(
                str(frame_path),
                classes=[0],  # person only
                verbose=False,
                conf=YOLO_CONFIDENCE_THRESHOLD,
            )

            best_box = None
            best_area = 0.0

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    area = (x2 - x1) * (y2 - y1)
                    if area > best_area:
                        best_area = area
                        best_box = (x1, x2)

            if best_box is not None:
                x1, x2 = best_box
                # Normalize to 0-1 range based on sample frame width
                center_norm = ((x1 + x2) / 2.0) / frame_w
                raw_centers.append(center_norm)
            else:
                # No person found — use center
                raw_centers.append(0.5)

            # Delete frame immediately after use to free RAM
            img.close()
            try:
                os.remove(frame_path)
            except OSError:
                pass

        except Exception as e:
            if logger:
                logger.warn(f"YOLO detection failed on frame {i}: {e}")
            raw_centers.append(0.5)

    if logger:
        detected = sum(1 for c in raw_centers if c != 0.5)
        logger.info(f"YOLO: detected person in {detected}/{num_samples} frames")

    # Exponential smoothing to remove jitter
    smoothed = []
    current = raw_centers[0] if raw_centers else 0.5
    for center in raw_centers:
        current = REFRAME_SMOOTHING_ALPHA * center + (1 - REFRAME_SMOOTHING_ALPHA) * current
        smoothed.append(current)

    # Convert to pixel crop positions
    keyframes: List[CropKeyframe] = []
    for i, center_norm in enumerate(smoothed):
        t = (i / max(num_samples - 1, 1)) * duration
        t = min(t, duration - 0.1)

        center_px = center_norm * src_width
        crop_x = int(center_px - crop_width / 2)
        crop_x = max(0, min(src_width - crop_width, crop_x))

        keyframes.append({"time": round(t, 3), "crop_x": crop_x})

    return keyframes


def _render_segment(
    video_path: str,
    seg_start: float,
    seg_end: float,
    crop_x: int,
    crop_width: int,
    src_height: int,
    output_path: Path,
    logger: JobLogger | None = None,
) -> bool:
    """
    Render one tiny segment with a fixed crop position.
    Each segment is only 1/10th of the clip — tiny RAM footprint.
    """
    duration = seg_end - seg_start
    if duration <= 0:
        return False

    filter_str = (
        f"crop={crop_width}:{src_height}:{crop_x}:0,"
        f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
    )

    command = [
        "ffmpeg", "-y",
        "-ss", f"{seg_start:.3f}",
        "-i", video_path,
        "-t", f"{duration:.3f}",
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", "ultrafast",  # fastest encode, less RAM
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
    ]

    try:
        run_ffmpeg(command, logger=logger, label=f"render_segment")
        return output_path.exists() and output_path.stat().st_size > 0
    except FFmpegError as e:
        if logger:
            logger.error(f"Segment render failed: {e}")
        return False


def _concat_segments(
    segment_paths: List[Path],
    output_path: Path,
    work_dir: Path,
    logger: JobLogger | None = None,
) -> str:
    """
    Concatenate all segments using ffmpeg concat demuxer.
    This is a stream copy — no re-encode, instant, zero RAM overhead.
    """
    concat_list = work_dir / "concat_list.txt"

    with open(concat_list, "w") as f:
        for seg_path in segment_paths:
            f.write(f"file '{seg_path.as_posix()}'\n")

    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",  # stream copy — no re-encode
        "-movflags", "+faststart",
        str(output_path),
    ]

    run_ffmpeg(command, logger=logger, label="concat_segments")
    return str(output_path)


def render_vertical_reframe(
    video_path: str,
    duration: float,
    clip_id: str | None = None,
    logger: JobLogger | None = None,
) -> str:
    """
    Main entry point.

    Pipeline:
      Python → YOLO (10 sample frames) → 10 crop positions
      → 10 tiny ffmpeg jobs → concat → finished

    Designed to stay well within 512MB RAM limit.
    """
    suffix = clip_id or uuid.uuid4().hex[:8]
    work_dir = STORAGE_DIR / "frames" / suffix
    work_dir.mkdir(parents=True, exist_ok=True)

    output_path = CLIPS_DIR / f"reframed_{suffix}.mp4"

    try:
        # Step 1: Probe source dimensions
        src_width, src_height = probe_dimensions(video_path, logger=logger)
        if src_width == 0 or src_height == 0:
            if logger:
                logger.warn("Could not probe dimensions, using center crop fallback")
            return _center_crop_fallback(video_path, output_path, logger=logger)

        crop_width = int(src_height * (REFRAME_TARGET_WIDTH / REFRAME_TARGET_HEIGHT))
        crop_width = min(crop_width, src_width)

        if logger:
            logger.info(f"Source: {src_width}x{src_height}, crop_width: {crop_width}")

        # Step 2: Extract 10 tiny sample frames via ffmpeg
        if logger:
            logger.info(f"Step 1/4: Sampling {NUM_SAMPLE_POINTS} frames")
        frame_paths = _sample_frames_with_ffmpeg(
            video_path, NUM_SAMPLE_POINTS, duration, work_dir, logger=logger
        )

        if not frame_paths:
            if logger:
                logger.warn("No frames extracted, using center crop fallback")
            return _center_crop_fallback(video_path, output_path, logger=logger)

        # Step 3: Run YOLO on each frame → get 10 crop positions
        if logger:
            logger.info("Step 2/4: Running YOLO person detection")
        keyframes = _detect_crop_positions(
            frame_paths, src_width, src_height, crop_width, duration, logger=logger
        )

        # Step 4: Render 10 tiny ffmpeg segments
        if logger:
            logger.info("Step 3/4: Rendering 10 segments")
        segment_paths = []

        for i in range(len(keyframes)):
            seg_start = keyframes[i]["time"]
            seg_end = keyframes[i + 1]["time"] if i + 1 < len(keyframes) else duration
            crop_x = keyframes[i]["crop_x"]

            seg_path = work_dir / f"seg_{i:03d}.mp4"

            success = _render_segment(
                video_path,
                seg_start,
                seg_end,
                crop_x,
                crop_width,
                src_height,
                seg_path,
                logger=logger,
            )

            if success:
                segment_paths.append(seg_path)
                if logger:
                    logger.info(f"Segment {i+1}/{len(keyframes)}: {seg_start:.2f}s-{seg_end:.2f}s crop_x={crop_x}")

        if not segment_paths:
            if logger:
                logger.warn("No segments rendered, using center crop fallback")
            return _center_crop_fallback(video_path, output_path, logger=logger)

        # Step 5: Concat all segments (stream copy, instant)
        if logger:
            logger.info("Step 4/4: Concatenating segments")
        result = _concat_segments(segment_paths, output_path, work_dir, logger=logger)

        if logger:
            logger.info(f"Reframe complete: {output_path}")

        return result

    except Exception as exc:
        if logger:
            logger.error(f"Reframe failed: {exc}, falling back to center crop")
        return _center_crop_fallback(video_path, output_path, logger=logger)

    finally:
        # Clean up all temp files
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


def _center_crop_fallback(
    video_path: str,
    output_path: Path,
    logger: JobLogger | None = None,
) -> str:
    """
    Simple center crop fallback when YOLO detection fails.
    No YOLO, no tracking — just a static center crop to 9:16.
    """
    if logger:
        logger.info("Using center crop fallback")

    filter_str = (
        f"crop=ih*{REFRAME_TARGET_WIDTH}/{REFRAME_TARGET_HEIGHT}:ih:"
        f"(iw-ih*{REFRAME_TARGET_WIDTH}/{REFRAME_TARGET_HEIGHT})/2:0,"
        f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
    )

    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]

    try:
        run_ffmpeg(command, logger=logger, label="center_crop_fallback")
        return str(output_path)
    except FFmpegError as e:
        raise ReframeError(f"Center crop fallback also failed: {e}") from e