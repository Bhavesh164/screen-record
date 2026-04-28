from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from screen_record.models import TimelineSegment


def _load_font(font_name: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(font_name, font_size)
    except OSError:
        return ImageFont.load_default()


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
    font = _load_font(str(style.get("font_name", "DejaVuSans.ttf")), int(style.get("font_size", 28)))
    padding = int(style.get("padding", 20))
    margin_bottom = int(style.get("margin_bottom", 64))
    text_color = str(style.get("text_color", "#F5F7FA"))
    fill = str(style.get("card_fill", "#161B22"))
    outline = str(style.get("card_outline", "#283041"))

    bbox = draw.textbbox((0, 0), segment.text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    card_width = text_width + padding * 2
    card_height = text_height + padding * 2
    left = max(16, (width - card_width) // 2)
    top = max(16, height - margin_bottom - card_height)
    right = left + card_width
    bottom = top + card_height

    draw.rounded_rectangle((left, top, right, bottom), radius=18, fill=fill, outline=outline, width=2)
    draw.text((left + padding, top + padding), segment.text, font=font, fill=text_color)
    image.save(output_path)
