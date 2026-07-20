"""
caption_burn_service.py

Takes a rendered clip (raw or reframed) plus a generated .ass subtitle
file and burns the captions into the video via ffmpeg's `ass` filter,
producing the final deliverable file.
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from functools import lru_cache
from pathlib import Path

from app.core.config import CAPTIONS_DIR, FINAL_DIR


def write_ass_file(ass_content: str, clip_id: str) -> str:
    ass_path = CAPTIONS_DIR / f"captions_{clip_id}.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    return str(ass_path)


def burn_captions(
    video_path: str,
    ass_path: str,
    clip_id: str | None = None,
    *,
    blocks: list[dict] | None = None,
    style: dict | None = None,
    video_width: int | None = None,
    video_height: int | None = None,
) -> str:
    """
    Burn the subtitles at `ass_path` into `video_path` and return the
    path to the resulting final mp4.
    """
    suffix = clip_id or uuid.uuid4().hex[:8]
    output_path = FINAL_DIR / f"final_{suffix}.mp4"

    if not _ffmpeg_has_filter("ass"):
        if not blocks or not style or not video_width or not video_height:
            raise RuntimeError(
                "This FFmpeg build has no ASS subtitle filter and caption overlay data was not provided"
            )
        return _burn_with_image_overlays(
            video_path,
            output_path,
            blocks,
            style,
            video_width,
            video_height,
            suffix,
        )

    # ffmpeg's filter argument parser treats ':' and other special chars
    # in file paths specially, so the ass filename must be escaped.
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
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vf",
        filter_arg,
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

    _run_ffmpeg(command, "Caption rendering")
    return str(output_path)


@lru_cache(maxsize=8)
def _ffmpeg_has_filter(filter_name: str) -> bool:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return bool(re.search(rf"\b{re.escape(filter_name)}\b", result.stdout))


def _burn_with_image_overlays(
    video_path: str,
    output_path: Path,
    blocks: list[dict],
    style: dict,
    video_width: int,
    video_height: int,
    suffix: str,
) -> str:
    """Fallback for FFmpeg builds without libass: render text with Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    font_path = _resolve_font_path(style.get("font_family", "Arial"), bool(style.get("bold")))
    font_size = max(12, int(style.get("font_size", 34)))
    try:
        font = ImageFont.truetype(str(font_path), font_size)
        active_font = ImageFont.truetype(
            str(font_path),
            round(font_size * 1.16),
        )
    except Exception:
        print(f"Couldn't load {font_path}, using default font.")
        font = ImageFont.load_default()
        active_font = ImageFont.load_default()
    text_color = style.get("text_color", "#FFFFFF")
    highlight_color = style.get("highlight_color", "#FFD400")
    outline_color = style.get("outline_color", "#000000")
    outline_width = max(0, int(style.get("outline_width", 3)))
    position = style.get("position", "bottom")
    uppercase = bool(style.get("uppercase"))

    image_paths: list[Path] = []
    command = ["ffmpeg", "-y", "-i", video_path]
    filter_steps: list[str] = []
    previous = "[0:v]"

    overlay_index = 0
    for block in blocks:
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if uppercase:
            text = text.upper()

        start = max(0.0, float(block.get("start_time", 0)))
        end = max(start + 0.08, float(block.get("end_time", start + 0.08)))
        words = text.split()
        kinetic = style.get("animation") in {"kinetic", "word-pop"} and len(words) > 1
        events = []
        if kinetic:
            word_duration = (end - start) / len(words)
            events = [
                (start + i * word_duration, start + (i + 1) * word_duration, i)
                for i in range(len(words))
            ]
        else:
            events = [(start, end, None)]

        for event_start, event_end, active_index in events:
            overlay_index += 1
            display_words = [words[active_index]] if active_index is not None else words
            display_active_index = 0 if active_index is not None else None
            canvas = _render_caption_canvas(
                Image,
                ImageDraw,
                video_width,
                video_height,
                display_words,
                font,
                active_font,
                display_active_index,
                text_color,
                highlight_color,
                outline_color,
                outline_width,
                position,
                style,
            )
            image_path = CAPTIONS_DIR / f"overlay_{suffix}_{overlay_index}.png"
            canvas.save(image_path)
            image_paths.append(image_path)
            command.extend(["-loop", "1", "-framerate", "25", "-i", str(image_path)])

            output_label = f"[captioned{overlay_index}]"
            filter_steps.append(
                f"{previous}[{len(image_paths)}:v]overlay=0:0:"
                f"enable='between(t,{event_start:.3f},{event_end:.3f})'{output_label}"
            )
            previous = output_label

    if not image_paths:
        return video_path

    command.extend(
        [
            "-filter_complex",
            ";".join(filter_steps),
            "-map",
            previous,
            "-map",
            "0:a?",
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
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_ffmpeg(command, "Caption rendering")
    return str(output_path)


def _render_caption_canvas(
    Image,
    ImageDraw,
    video_width: int,
    video_height: int,
    words: list[str],
    font,
    active_font,
    active_index: int | None,
    text_color: str,
    highlight_color: str,
    outline_color: str,
    outline_width: int,
    position: str,
    style: dict,
):
    canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    max_width = int(video_width * 0.84)
    space_width = draw.textlength(" ", font=font)
    lines: list[list[tuple[int, str]]] = [[]]
    line_width = 0.0

    for index, word in enumerate(words):
        word_width = draw.textlength(word, font=font)
        candidate_width = line_width + (space_width if lines[-1] else 0) + word_width
        if lines[-1] and candidate_width > max_width:
            lines.append([])
            line_width = 0.0
        lines[-1].append((index, word))
        line_width += (space_width if len(lines[-1]) > 1 else 0) + word_width

    line_height = max(font.getbbox("Ag")[3], active_font.getbbox("Ag")[3])
    line_gap = max(5, line_height // 6)
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
    if position == "top":
        base_y = max(35, int(video_height * 0.08))
    elif position == "middle":
        base_y = (video_height - total_height) // 2
    else:
        base_y = max(20, int(video_height * 0.82) - total_height)

    measured_lines = []
    for line in lines:
        width = sum(
            draw.textlength(word, font=active_font if index == active_index else font)
            for index, word in line
        )
        width += space_width * max(0, len(line) - 1)
        measured_lines.append((line, width))

    if style.get("background_box"):
        opacity = max(0, min(100, int(style.get("background_opacity", 50))))
        alpha = round(255 * opacity / 100)
        widest = max((width for _, width in measured_lines), default=0)
        padding_x = max(12, font.size // 2)
        padding_y = max(8, font.size // 4)
        x0 = (video_width - widest) / 2 - padding_x

        bg_hex = style.get("background_color", "#000000").lstrip("#")
        if len(bg_hex) != 6:
            bg_hex = "000000"
        bg_r = int(bg_hex[0:2], 16)
        bg_g = int(bg_hex[2:4], 16)
        bg_b = int(bg_hex[4:6], 16)

        draw.rounded_rectangle(
            (x0, base_y - padding_y, x0 + widest + 2 * padding_x, base_y + total_height + padding_y),
            radius=max(8, font.size // 4),
            fill=(bg_r, bg_g, bg_b, alpha),
        )

    for line_number, (line, width) in enumerate(measured_lines):
        x = (video_width - width) / 2
        y = base_y + line_number * (line_height + line_gap)
        for index, word in line:
            is_active = index == active_index
            selected_font = active_font if is_active else font
            selected_color = highlight_color if is_active else text_color
            draw_y = y - (round(font.size * 0.12) if is_active else 0)
            draw.text(
                (x, draw_y),
                word,
                font=selected_font,
                fill=selected_color,
                stroke_width=outline_width,
                stroke_fill=outline_color,
            )
            x += draw.textlength(word, font=selected_font) + space_width
    return canvas


def _wrap_text(draw, text: str, font, max_width: int, stroke_width: int) -> str:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=stroke_width)
        if current and bbox[2] - bbox[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def _resolve_font_path(font_family: str, bold: bool) -> Path:
    project_root = Path(__file__).resolve().parents[3]

    frontend_fonts = (
        project_root /
        "frontend" /
        "public" /
        "fonts"
    )
    if os.name == 'nt':
        roots = [
            Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts"
        ]
    else:
        roots = [
            Path.home() / "Library" / "Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
        ]
    aliases = {
        "arial rounded mt bold": ["Arial Rounded Bold", "Arial Rounded Bold MT", "arlrdbld"],
        "avenir next": ["Avenir Next", "Avenir"],
        "helvetica neue": ["HelveticaNeue", "Helvetica Neue", "Helvetica"],
        "space grotesk": ["SpaceGrotesk", "Space Grotesk"],
        "times new roman": ["Times New Roman", "times"],
    }
    wanted = [font_family, *aliases.get(font_family.lower(), [])]
    if bold:
        wanted = [f"{name} Bold" for name in wanted] + wanted
        wanted = wanted + [f"{name}bd" for name in wanted] + [f"{name}b" for name in wanted]

    normalized_wanted = [re.sub(r"[^a-z0-9]", "", name.lower()) for name in wanted]
    candidates: list[Path] = []
    for root in roots:
        if root.exists():
            candidates.extend(root.glob("*"))
            candidates.extend(root.glob("*/*"))

    for path in candidates:
        if path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
            continue
        normalized_name = re.sub(r"[^a-z0-9]", "", path.stem.lower())
        if any(name in normalized_name or normalized_name in name for name in normalized_wanted):
            return path

    if os.name == 'nt':
        fallback = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts" / "arialbd.ttf"
        if not fallback.exists():
            fallback = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts" / "arial.ttf"
        return fallback

    fallback = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    if not fallback.exists():
        fallback = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    return fallback


def _run_ffmpeg(command: list[str], label: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        detail = "\n".join(message[-12:])
        raise RuntimeError(f"{label} failed:\n{detail}")
