"""
kinetic_caption_service.py
Frame-by-frame kinetic captions using PIL + ffmpeg overlay.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from app.core.config import FALLBACK_FONT_PATH, FINAL_DIR, FONT_CANDIDATES, FRAMES_DIR
from app.core.logging_utils import JobLogger
from app.services.ffmpeg_utils import run_ffmpeg

ANIMATION_FRAME_COUNT = 6
OVERLAY_FPS = 24


def _resolve_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    if FALLBACK_FONT_PATH:
        try:
            return ImageFont.truetype(FALLBACK_FONT_PATH, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = (hex_color or "#FFFFFF").lstrip("#")
    if len(hex_color) != 6:
        hex_color = "FFFFFF"
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def _draw_text_with_outline(draw, position, text, font, fill, outline_color, outline_width, anchor="mm"):
    x, y = position
    if outline_width > 0:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _group_words(words: List[dict], words_per_group: int) -> List[dict]:
    groups = []
    for i in range(0, len(words), words_per_group):
        chunk = words[i: i + words_per_group]
        if not chunk:
            continue
        groups.append({
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "words": chunk,
        })
    return groups


def _render_group_frames(group, style, canvas_width, canvas_height, out_dir, group_index) -> List[Path]:
    font_size = int(style.get("font_size", 46))
    font = _resolve_font(font_size)
    text = " ".join(w["word"] for w in group["words"])
    if style.get("uppercase", True):
        text = text.upper()

    text_color = _hex_to_rgba(style.get("text_color", "#FFFFFF"))
    outline_color = _hex_to_rgba(style.get("outline_color", "#000000"))
    outline_width = max(1, int(style.get("outline_width", 3)))
    position = style.get("position", "bottom")
    y_frac = {"top": 0.15, "middle": 0.5, "bottom": 0.82}.get(position, 0.82)

    frame_paths: List[Path] = []

    for frame_idx in range(ANIMATION_FRAME_COUNT):
        progress = (frame_idx + 1) / ANIMATION_FRAME_COUNT
        scale = 0.6 + 0.4 * (1 - (1 - progress) ** 2)
        alpha = int(255 * min(1.0, progress * 1.6))

        frame_font_size = max(8, int(font_size * scale))
        frame_font = _resolve_font(frame_font_size)

        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        cx = canvas_width // 2
        cy = int(canvas_height * y_frac)

        _draw_text_with_outline(
            draw, (cx, cy), text, frame_font,
            fill=(*text_color[:3], alpha),
            outline_color=(*outline_color[:3], alpha),
            outline_width=outline_width,
            anchor="mm",
        )

        frame_path = out_dir / f"grp{group_index:03d}_f{frame_idx:02d}.png"
        canvas.save(frame_path)
        frame_paths.append(frame_path)

    return frame_paths


def render_kinetic_captions(
    video_path: str,
    words: List[dict],
    style: dict,
    canvas_width: int,
    canvas_height: int,
    clip_id: str,
    logger: JobLogger | None = None,
) -> str:
    suffix = clip_id or uuid.uuid4().hex[:8]
    work_dir = FRAMES_DIR / suffix
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    words_per_group = int(style.get("words_per_block", 3)) or 3
    groups = _group_words(words, words_per_group)

    if not groups:
        if logger:
            logger.warn(f"No word groups for clip {clip_id}, skipping captions")
        return video_path

    if logger:
        logger.info(f"Rendering {len(groups)} caption groups for clip {clip_id}")

    group_frame_paths = []
    for i, group in enumerate(groups):
        frames = _render_group_frames(group, style, canvas_width, canvas_height, work_dir, i)
        group_frame_paths.append(frames)

    inputs: List[str] = ["-i", video_path]
    for i in range(len(groups)):
        pattern = str(work_dir / f"grp{i:03d}_f%02d.png")
        inputs += ["-framerate", str(OVERLAY_FPS), "-i", pattern]

    input_indices = list(range(1, 1 + len(groups)))
    overlay_label = "0:v"
    filter_parts = []

    for i, (group, idx) in enumerate(zip(groups, input_indices)):
        next_label = f"v{i}"
        filter_parts.append(
            f"[{idx}:v]setpts=PTS-STARTPTS+{group['start']:.3f}/TB[ov{i}];"
            f"[{overlay_label}][ov{i}]overlay=0:0:"
            f"enable='between(t,{group['start']:.3f},{group['end']:.3f})'[{next_label}]"
        )
        overlay_label = next_label

    filter_complex = ";".join(filter_parts)
    output_path = FINAL_DIR / f"final_{suffix}.mp4"

    command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{overlay_label}]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        run_ffmpeg(command, logger=logger, label=f"kinetic_burn[{suffix}]")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return str(output_path)