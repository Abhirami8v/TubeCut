"""
reframe_service.py (face/person tracking + auto vertical reframe)

Converts a landscape clip into a vertical 9:16 clip that follows the
speaker, instead of a naive center-crop. Pipeline:

  1. Run YOLOv8 person detection every N frames (full-rate detection is
     unnecessary and slow; we interpolate between detections).
  2. Pick the most prominent detection per sampled frame (largest box,
     tie-broken toward frame center) as the subject.
  3. Convert each detection's center-x into a target crop-window
     center, exponentially smoothed across frames so the resulting pan
     is a gentle glide instead of a jittery snap.
  4. Render the result with ffmpeg using a piecewise-linear crop-x
     expression interpolated between keyframes, then scale to the
     target vertical resolution.

If no person is ever detected (e.g. a slideshow/B-roll clip), this
degrades gracefully to a stationary center crop.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from typing import List, TypedDict

from app.core.config import (
    REFRAME_DETECT_EVERY_N_FRAMES,
    REFRAME_SMOOTHING_ALPHA,
    REFRAME_TARGET_HEIGHT,
    REFRAME_TARGET_WIDTH,
    STORAGE_DIR,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_WEIGHTS_PATH,
)
from app.services.video_service import probe_dimensions

_yolo_model = None


class CropKeyframe(TypedDict):
    time: float
    crop_x: int  # left edge of the crop window, in source pixels


def _get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO

        _yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    return _yolo_model


def _detect_subject_centers(video_path: str, src_width: int, src_height: int) -> List[tuple[float, float]]:
    """
    Sample frames from `video_path` and return a list of (timestamp,
    normalized_center_x in [0,1]) for the most prominent detected
    person in each sampled frame. Frames with no detection are skipped
    (we interpolate/hold over gaps later).
    """
    import cv2

    model = _get_yolo_model()
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    centers: List[tuple[float, float]] = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx % REFRAME_DETECT_EVERY_N_FRAMES == 0:
            results = model.predict(frame, classes=[0], verbose=False, conf=YOLO_CONFIDENCE_THRESHOLD)
            best_box = None
            best_area = 0.0

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    area = (x2 - x1) * (y2 - y1)
                    if area > best_area:
                        best_area = area
                        best_box = (x1, y1, x2, y2)

            if best_box is not None:
                x1, _y1, x2, _y2 = best_box
                center_x_norm = ((x1 + x2) / 2.0) / src_width
                timestamp = frame_idx / fps
                centers.append((timestamp, center_x_norm))

        frame_idx += 1

    cap.release()
    return centers


def _smooth_centers(centers: List[tuple[float, float]], duration: float) -> List[tuple[float, float]]:
    """
    Exponentially smooth the raw detection centers and fill gaps so we
    have a continuous, jitter-free pan curve covering [0, duration].
    Falls back to a fixed center (0.5) if no detections were found.
    """
    if not centers:
        return [(0.0, 0.5), (duration, 0.5)]

    smoothed: List[tuple[float, float]] = []
    current = centers[0][1]

    for timestamp, raw_center in centers:
        current = REFRAME_SMOOTHING_ALPHA * raw_center + (1 - REFRAME_SMOOTHING_ALPHA) * current
        smoothed.append((timestamp, current))

    if smoothed[0][0] > 0.0:
        smoothed.insert(0, (0.0, smoothed[0][1]))
    if smoothed[-1][0] < duration:
        smoothed.append((duration, smoothed[-1][1]))

    return smoothed


def build_crop_keyframes(video_path: str, duration: float) -> List[CropKeyframe]:
    """
    Build a list of (time, crop_x_pixels) keyframes describing how the
    9:16 crop window should pan across `video_path` over its duration.
    """
    src_width, src_height = probe_dimensions(video_path)
    if src_width == 0 or src_height == 0:
        return [{"time": 0.0, "crop_x": 0}]

    crop_width = int(src_height * (REFRAME_TARGET_WIDTH / REFRAME_TARGET_HEIGHT))
    crop_width = min(crop_width, src_width)

    centers = _detect_subject_centers(video_path, src_width, src_height)
    smoothed = _smooth_centers(centers, duration)

    keyframes: List[CropKeyframe] = []
    for timestamp, center_norm in smoothed:
        center_px = center_norm * src_width
        crop_x = int(center_px - crop_width / 2)
        crop_x = max(0, min(src_width - crop_width, crop_x))
        keyframes.append({"time": round(timestamp, 2), "crop_x": crop_x})

    return keyframes


def render_vertical_reframe(video_path: str, duration: float, clip_id: str | None = None) -> str:
    """
    Render a 9:16 vertical version of `video_path` that pans to follow
    the detected subject, using a piecewise-linear crop-x expression
    built from smoothed detection keyframes.
    """
    suffix = clip_id or uuid.uuid4().hex[:8]
    output_path = STORAGE_DIR / "clips" / f"reframed_{suffix}.mp4"

    src_width, src_height = probe_dimensions(video_path)
    if src_width == 0 or src_height == 0:
        return _render_stationary_vertical(video_path, output_path)

    crop_width = int(src_height * (REFRAME_TARGET_WIDTH / REFRAME_TARGET_HEIGHT))
    crop_width = min(crop_width, src_width)

    try:
        keyframes = build_crop_keyframes(video_path, duration)
    except Exception as exc:  # noqa: BLE001
        print(f"[reframe_service] subject detection failed, falling back to center crop: {exc}")
        keyframes = [{"time": 0.0, "crop_x": max(0, (src_width - crop_width) // 2)}]

    return _render_segmented_pan(video_path, output_path, keyframes, crop_width, src_height)


def _render_segmented_pan(
    video_path: str,
    output_path: Path,
    keyframes: List[CropKeyframe],
    crop_width: int,
    src_height: int,
) -> str:
    """
    Render the vertical pan using a single ffmpeg `crop` filter whose
    x-offset is a piecewise-linear function of time built from the
    smoothed detection keyframes, followed by a scale pass to the
    target vertical resolution.
    """
    if len(keyframes) == 1:
        crop_x = keyframes[0]["crop_x"]
        filter_str = (
            f"crop={crop_width}:{src_height}:{crop_x}:0,"
            f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
        )
    else:
        expr_terms = []
        for i in range(len(keyframes) - 1):
            t0, x0 = keyframes[i]["time"], keyframes[i]["crop_x"]
            t1, x1 = keyframes[i + 1]["time"], keyframes[i + 1]["crop_x"]
            t1 = max(t1, t0 + 0.001)
            slope = (x1 - x0) / (t1 - t0)
            expr_terms.append((t0, t1, x0, slope))

        def build_expr(idx: int) -> str:
            if idx >= len(expr_terms):
                return str(keyframes[-1]["crop_x"])
            t0, t1, x0, slope = expr_terms[idx]
            inner = build_expr(idx + 1)
            return f"if(between(t,{t0:.2f},{t1:.2f}),{x0:.1f}+(t-{t0:.2f})*{slope:.2f},{inner})"

        x_expr = build_expr(0)
        filter_str = (
            f"crop={crop_width}:{src_height}:'{x_expr}':0,"
            f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
        )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vf",
        filter_str,
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


def _render_stationary_vertical(video_path: str, output_path: Path) -> str:
    """Fallback: plain center-crop to 9:16 with no panning."""
    filter_str = (
        f"crop=ih*{REFRAME_TARGET_WIDTH}/{REFRAME_TARGET_HEIGHT}:ih:"
        f"(iw-ih*{REFRAME_TARGET_WIDTH}/{REFRAME_TARGET_HEIGHT})/2:0,"
        f"scale={REFRAME_TARGET_WIDTH}:{REFRAME_TARGET_HEIGHT}"
    )
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vf",
        filter_str,
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
