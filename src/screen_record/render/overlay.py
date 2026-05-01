from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from screen_record.models import TimelineSegment

_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _load_font(font_name: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (font_name, font_size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = [
        font_name,
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Keyboard.ttf",
    ]
    for path in candidates:
        try:
            font = ImageFont.truetype(path, font_size)
            _FONT_CACHE[key] = font
            return font
        except OSError:
            continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _render_key_pill(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    key_text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    is_modifier: bool,
    style: dict[str, object],
) -> float:
    pill_h_padding = int(style.get("key_pill_h_padding", 16))
    pill_v_padding = int(style.get("key_pill_v_padding", 10))
    pill_radius = int(style.get("key_pill_radius", 10))
    modifier_fill = str(style.get("modifier_fill", "#2D5A3D"))
    modifier_outline = str(style.get("modifier_outline", "#4ADE80"))
    modifier_text_color = str(style.get("modifier_text_color", "#BBF7D0"))
    text_color = str(style.get("text_color", "#F5F7FA"))
    card_fill = str(style.get("key_fill", "#1E293B"))
    card_outline = str(style.get("key_outline", "#334155"))

    bbox = draw.textbbox((0, 0), key_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_y_offset = bbox[1]

    pill_w = text_w + pill_h_padding * 2
    pill_h = text_h + pill_v_padding * 2

    fill = modifier_fill if is_modifier else card_fill
    outline = modifier_outline if is_modifier else card_outline
    color = modifier_text_color if is_modifier else text_color
    outline_w = 2 if is_modifier else 1

    x0, y0 = int(x), int(y)
    x1, y1 = int(x + pill_w), int(y + pill_h)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=pill_radius, fill=fill, outline=outline, width=outline_w)

    text_x = x0 + pill_h_padding
    text_y = y0 + pill_v_padding - text_y_offset
    draw.text((text_x, int(text_y)), key_text, font=font, fill=color)

    return pill_w


def render_segment_overlay(
    *,
    output_path: Path,
    width: int,
    height: int,
    segment: TimelineSegment,
    style: dict[str, object],
) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    font_size = int(style.get("font_size", 28))
    font = _load_font(str(style.get("font_name", "HelveticaNeue.ttc")), font_size)
    key_gap = int(style.get("key_gap", 10))
    margin_bottom = int(style.get("margin_bottom", 80))
    key_pill_v_padding = int(style.get("key_pill_v_padding", 10))

    keys = segment.keys if segment.keys else [segment.text]
    modifier_names = {"Shift", "Ctrl", "Option", "Cmd", "Alt", "Caps Lock", "Fn", "Super", "Enter", "Space", "Tab", "Backspace", "Esc", "Delete", "Home", "End", "Page Up", "Page Down", "Up", "Down", "Left", "Right"}

    pill_widths = []
    pill_height = 0
    for key in keys:
        bbox = draw.textbbox((0, 0), key, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pill_w = tw + int(style.get("key_pill_h_padding", 16)) * 2
        pill_h = th + int(style.get("key_pill_v_padding", 10)) * 2
        pill_widths.append(pill_w)
        pill_height = max(pill_height, pill_h)

    total_width = sum(pill_widths) + key_gap * (len(keys) - 1)

    group_padding = int(style.get("group_padding", 14))
    group_v_padding = int(style.get("group_v_padding", 14))
    card_width = total_width + group_padding * 2
    card_height = pill_height + group_v_padding * 2
    card_radius = int(style.get("card_radius", 16))

    container_fill = str(style.get("card_fill", "#0F172A"))
    container_outline = str(style.get("card_outline", "#1E293B"))

    max_left = width - card_width - 20
    left = max(20, min((width - card_width) // 2, max_left))
    top = max(20, height - margin_bottom - card_height)

    draw.rounded_rectangle(
        (left, top, left + card_width, top + card_height),
        radius=card_radius,
        fill=container_fill,
        outline=container_outline,
        width=1,
    )

    key_x = left + group_padding
    key_y = top + group_v_padding

    for i, key in enumerate(keys):
        is_modifier = key in modifier_names
        pill_w = _render_key_pill(
            draw, key_x, key_y, key, font, is_modifier, style
        )
        key_x += pill_w + key_gap

    overlay_alpha = image.split()[3]
    blurred_alpha = overlay_alpha.filter(ImageFilter.GaussianBlur(radius=0))
    image.putalpha(blurred_alpha)
    image.save(output_path)