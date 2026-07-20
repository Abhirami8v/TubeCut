"""
caption_service.py

Owns the caption "block" model that the frontend's timeline editor
operates on (create from word timestamps, edit text, retime, split,
merge), plus conversion of those blocks into Advanced SubStation Alpha
(.ass) subtitle files for burning into the final render.

Caption blocks are intentionally simple (id, start, end, text) at the
DB layer; all the visual styling (font, color, animation, etc.) lives
in CaptionStyle and is applied at ASS-generation time, so the same
blocks can be re-rendered in any style without touching their content.
"""

from __future__ import annotations

from typing import List

from app.core.config import DEFAULT_CAPTION_CHUNK_SIZE


def build_blocks_from_words(words: List[dict], words_per_block: int = DEFAULT_CAPTION_CHUNK_SIZE) -> List[dict]:
    """
    Group word-timestamp dicts ({"word", "start", "end"}, all relative
    to clip start) into caption blocks of `words_per_block` words each.
    Returns dicts with order_index/start_time/end_time/text, ready to be
    persisted as CaptionBlock rows.
    """
    blocks: List[dict] = []
    if not words:
        return blocks

    for i in range(0, len(words), words_per_block):
        chunk = words[i : i + words_per_block]
        if not chunk:
            continue
        blocks.append(
            {
                "order_index": len(blocks),
                "start_time": chunk[0]["start"],
                "end_time": chunk[-1]["end"],
                "text": " ".join(w["word"] for w in chunk).strip(),
            }
        )

    return blocks


def split_block(block: dict, split_at_time: float) -> tuple[dict, dict]:
    """
    Split a single caption block dict into two blocks at `split_at_time`
    (absolute clip time). Text is split proportionally by word count
    since we don't retain per-word timing once blocks are formed.
    """
    words = block["text"].split()
    duration = max(0.01, block["end_time"] - block["start_time"])
    fraction = max(0.0, min(1.0, (split_at_time - block["start_time"]) / duration))

    split_word_idx = max(1, min(len(words) - 1, round(len(words) * fraction))) if len(words) > 1 else 1

    first_text = " ".join(words[:split_word_idx]) or block["text"]
    second_text = " ".join(words[split_word_idx:]) or ""

    first = {
        "order_index": block["order_index"],
        "start_time": block["start_time"],
        "end_time": split_at_time,
        "text": first_text,
    }
    second = {
        "order_index": block["order_index"] + 1,
        "start_time": split_at_time,
        "end_time": block["end_time"],
        "text": second_text,
    }
    return first, second


def merge_blocks(first: dict, second: dict) -> dict:
    """Merge two adjacent caption block dicts into one."""
    return {
        "order_index": min(first["order_index"], second["order_index"]),
        "start_time": min(first["start_time"], second["start_time"]),
        "end_time": max(first["end_time"], second["end_time"]),
        "text": f"{first['text'].strip()} {second['text'].strip()}".strip(),
    }


# ---------------------------------------------------------------------------
# ASS export
# ---------------------------------------------------------------------------

_ASS_POSITION_ALIGN = {
    "bottom": 2,  # bottom-center
    "middle": 5,  # mid-center
    "top": 8,     # top-center
}

_ASS_ANIMATION_TAGS = {
    "none": "",
    "fade": r"\fad(150,80)",
    "pop": r"\t(0,120,\fscx115\fscy115)\t(120,220,\fscx100\fscy100)",
    "bounce": r"\t(0,100,\fscy130)\t(100,200,\fscy90)\t(200,280,\fscy105)\t(280,360,\fscy100)",
    "kinetic": "",
    "word-pop": "",
}


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert '#RRGGBB' to ASS's '&HBBGGRR&' format."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        hex_color = "FFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{b}{g}{r}&".upper()


def generate_ass_file(blocks: List[dict], style: dict, video_width: int, video_height: int) -> str:
    """
    Render `blocks` (list of {start_time, end_time, text}) into a
    complete .ass subtitle document string using `style` (a
    CaptionStyle.to_dict()-shaped dict).
    """
    align = _ASS_POSITION_ALIGN.get(style.get("position", "bottom"), 2)
    margin_v = style.get("safe_margins", 60) if align != 5 else 0

    primary_color = _hex_to_ass_color(style.get("text_color", "#FFFFFF"))
    highlight_color = _hex_to_ass_color(style.get("highlight_color", "#FFD400"))
    outline_color = _hex_to_ass_color(style.get("outline_color", "#000000"))
    
    bg_color_hex = style.get("background_color", "#000000")
    back_color = (
        "&H80000000"
        if not style.get("background_box")
        else _opacity_to_ass_back_color(bg_color_hex, style.get("background_opacity", 50))
    )

    bold_flag = -1 if style.get("bold") else 0
    border_style = 3 if style.get("background_box") else 1

    header = f"""[Script Info]
Title: TubeCut Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.get('font_family', 'Arial')},{style.get('font_size', 34)},{primary_color},{highlight_color},{outline_color},{back_color},{bold_flag},0,0,0,100,100,0,0,{border_style},{style.get('outline_width', 3)},{style.get('shadow_strength', 0)},{align},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    animation_tag = _ASS_ANIMATION_TAGS.get(style.get("animation", "none"), "")
    uppercase = style.get("uppercase", False)

    lines = []
    for block in blocks:
        text = block["text"].strip()
        if uppercase:
            text = text.upper()
        # Treat user text as text, not as arbitrary ASS override tags.
        text = (
            text.replace("\\", r"\\")
            .replace("{", r"\{")
            .replace("}", r"\}")
            .replace("\n", r"\N")
        )

        block_start = float(block["start_time"])
        block_end = max(float(block["end_time"]), block_start + 0.08)
        start = _seconds_to_ass_timestamp(block_start)
        end = _seconds_to_ass_timestamp(block_end)
        animation = style.get("animation", "none")
        if animation in {"kinetic", "word-pop"}:
            words = text.split()
            word_duration = (block_end - block_start) / len(words)
            for active_index in range(len(words)):
                word_start = block_start + active_index * word_duration
                word_end = block_start + (active_index + 1) * word_duration
                parts = []
                for idx, w in enumerate(words):
                    if idx == active_index:
                        parts.append(rf"{{\c{highlight_color}\fscx118\fscy118}}{w}{{\r}}")
                    else:
                        parts.append(w)
                rendered_line = " ".join(parts)
                lines.append(
                    "Dialogue: 0,"
                    f"{_seconds_to_ass_timestamp(word_start)},"
                    f"{_seconds_to_ass_timestamp(word_end)},"
                    f"Default,,0,0,0,,{rendered_line}"
                )
            continue
        override = f"{{{animation_tag}}}" if animation_tag else ""
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{override}{text}")

    return header + "\n".join(lines) + "\n"


def _opacity_to_ass_back_color(hex_color: str, opacity_percent: int) -> str:
    """Convert hex_color '#RRGGBB' to ASS's '&HAABBGGRR' format with given opacity."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        hex_color = "000000"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    alpha = int(255 * (1 - opacity_percent / 100.0))
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _seconds_to_ass_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        centis = 0
        secs += 1
    return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centis:02d}"
