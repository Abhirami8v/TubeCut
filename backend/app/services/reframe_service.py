"""
reframe_service.py

Highly optimized, memory-efficient vertical reframe pipeline.
Bypasses intermediate file writes and multiple FFmpeg subprocesses.
Uses OpenCV for in-memory frame extraction and batch YOLOv8 prediction.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
import cv2
import numpy as np

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

_yolo_model = None

NUM_SAMPLE_POINTS = 10      # sample points across the clip
YOLO_SAMPLE_WIDTH = 320     # small resolution for YOLO to minimize memory usage


def _get_yolo_model(logger: JobLogger | None = None):
    global _yolo_model
    if _yolo_model is None:
        weights = Path(YOLO_WEIGHTS_PATH)
        if not weights.exists() and logger:
            logger.info(f"Downloading YOLO weights to {weights}")
        from ultralytics import YOLO
        _yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    return _yolo_model


def get_crop_expr_for_clip(
    clip_id: str,
    video_path: str,
    start_time: float,
    duration: float,
    logger: JobLogger | None = None,
) -> tuple[str, int]:
    """
    Get the compiled FFmpeg crop expression for a clip.
    If cached on disk, loads it from the cache file.
    Otherwise, extracts frames using OpenCV, runs batch YOLO,
    computes smoothed crop coordinates, compiles it, caches it, and returns it.
    Returns (crop_expr_str, crop_width).
    """
    cache_path = CLIPS_DIR / f"crop_{clip_id}.json"
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return data["crop_expr"], data["crop_width"]
        except Exception:
            pass

    # Determine video dimensions
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        if logger:
            logger.error(f"OpenCV could not open video for reframing: {video_path}")
        return "0", REFRAME_TARGET_WIDTH
    
    src_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if src_width == 0 or src_height == 0:
        return "0", REFRAME_TARGET_WIDTH

    crop_width = int(src_height * (REFRAME_TARGET_WIDTH / REFRAME_TARGET_HEIGHT))
    crop_width = min(crop_width, src_width)

    # 1. Sample times across the clip duration
    times = []
    for i in range(NUM_SAMPLE_POINTS):
        t = start_time + (i / max(NUM_SAMPLE_POINTS - 1, 1)) * duration
        t = min(t, start_time + duration - 0.05)
        times.append(t)

    # 2. Extract frames using OpenCV in-memory
    frames = []
    cap = cv2.VideoCapture(video_path)
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret or frame is None:
            # Fallback seek to frame index
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ret, frame = cap.read()
            
        if ret and frame is not None:
            # Downscale for memory efficiency and speed
            h, w = frame.shape[:2]
            new_w = YOLO_SAMPLE_WIDTH
            new_h = int(h * (new_w / w))
            resized = cv2.resize(frame, (new_w, new_h))
            frames.append(resized)
        else:
            if logger:
                logger.warn(f"Frame extraction failed at {t:.2f}s")
    cap.release()

    if not frames:
        # Fallback: static center crop
        center_x = (src_width - crop_width) // 2
        return str(center_x), crop_width

    # 3. Batch predict YOLO
    model = _get_yolo_model(logger)
    # ultralytics accept list of numpy BGR frames directly
    results = model.predict(
        frames,
        classes=[0],  # person only
        verbose=False,
        conf=YOLO_CONFIDENCE_THRESHOLD,
    )

    # 4. Extract centers
    raw_centers = []
    for idx, result in enumerate(results):
        frame_w = frames[idx].shape[1]
        best_box = None
        best_area = 0.0

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best_box = (x1, x2)

        if best_box is not None:
            x1, x2 = best_box
            center_norm = ((x1 + x2) / 2.0) / frame_w
            raw_centers.append(center_norm)
        else:
            raw_centers.append(0.5)

    # 5. Smooth crop positions to prevent jitter
    smoothed = []
    current = raw_centers[0] if raw_centers else 0.5
    for center in raw_centers:
        current = REFRAME_SMOOTHING_ALPHA * center + (1 - REFRAME_SMOOTHING_ALPHA) * current
        smoothed.append(current)

    # 6. Build nested crop expression relative to clip start (t=0)
    sorted_kfs = []
    for i, center_norm in enumerate(smoothed):
        t_rel = (i / max(NUM_SAMPLE_POINTS - 1, 1)) * duration
        t_rel = min(t_rel, duration - 0.05)

        center_px = center_norm * src_width
        crop_x = int(center_px - crop_width / 2)
        crop_x = max(0, min(src_width - crop_width, crop_x))
        sorted_kfs.append({"time": round(t_rel, 3), "crop_x": crop_x})

    if len(sorted_kfs) == 1:
        expr = str(sorted_kfs[0]["crop_x"])
    else:
        expr = str(sorted_kfs[-1]["crop_x"])
        for i in range(len(sorted_kfs) - 2, -1, -1):
            kf = sorted_kfs[i]
            next_kf = sorted_kfs[i + 1]
            expr = f"if(lt(t,{next_kf['time']:.3f}),{kf['crop_x']},{expr})"

    # Save to cache
    try:
        cache_path.write_text(json.dumps({"crop_expr": expr, "crop_width": crop_width}), encoding="utf-8")
    except Exception as e:
        if logger:
            logger.warn(f"Failed to cache crop expression: {e}")

    return expr, crop_width


def render_vertical_reframe(
    video_path: str,
    duration: float,
    clip_id: str | None = None,
    logger: JobLogger | None = None,
) -> str:
    """
    Legacy wrapper for rendering vertical reframe to a separate video file.
    Uses the optimized single-pass FFmpeg crop expression instead of segment-concat.
    """
    suffix = clip_id or uuid.uuid4().hex[:8]
    output_path = CLIPS_DIR / f"reframed_{suffix}.mp4"
    
    try:
        crop_expr, crop_width = get_crop_expr_for_clip(
            suffix, video_path, 0.0, duration, logger
        )
        
        # Probe height of the source video
        src_height = REFRAME_TARGET_HEIGHT
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            src_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
        filter_str = (
            f"crop={crop_width}:{src_height}:{crop_expr}:0,"
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
        
        run_ffmpeg(command, logger=logger, label="legacy_reframe")
        return str(output_path)
        
    except Exception as exc:
        if logger:
            logger.error(f"Legacy vertical reframe failed: {exc}, falling back to static center crop")
        return _center_crop_fallback(video_path, output_path, logger=logger)


def _center_crop_fallback(
    video_path: str,
    output_path: Path,
    logger: JobLogger | None = None,
) -> str:
    """
    Static center crop fallback when YOLO/OpenCV fails.
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
        raise RuntimeError(f"Center crop fallback also failed: {e}") from e