#!/usr/bin/env python3
"""Render accurate ad copy onto a generated visual with Pillow."""

from __future__ import annotations

import argparse
import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font_candidates(text: str) -> list[Path]:
    cjk = any('\u3400' <= char <= '\u9fff' for char in text)
    system = platform.system()
    values: list[str] = []
    if system == "Darwin":
        values += ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Helvetica.ttc"] if cjk else ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    elif system == "Windows":
        values += [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"] if cjk else [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]
    values += ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    return [Path(item) for item in values if Path(item).is_file()]


def load_font(text: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in font_candidates(text):
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str] | None:
    if not text:
        return []
    tokens = list(text) if any(ord(c) > 255 for c in text) and " " not in text else text.split()
    joiner = "" if tokens and len(tokens[0]) == 1 and any(ord(c) > 255 for c in text) else " "
    lines: list[str] = []
    current = ""
    for token in tokens:
        trial = token if not current else current + joiner + token
        if draw.textbbox((0, 0), trial, font=font, stroke_width=1)[2] <= max_width:
            current = trial
        else:
            if not current:
                return None
            lines.append(current)
            current = token
    if current:
        lines.append(current)
    return lines if len(lines) <= max_lines else None


def fit(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int, start: int, minimum: int):
    for size in range(start, minimum - 1, -2):
        font = load_font(text, size)
        lines = wrap(draw, text, font, max_width, max_lines)
        if lines is not None:
            return font, lines
    raise ValueError("文案无法在最大行数内排下，请缩短文案。")


def render(image_path: Path, output: Path, headline: str, subheadline: str = "", badge: str = "", layout: str = "top-title", style: str = "ugc") -> Path:
    image = Image.open(image_path).convert("RGBA")
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    margin = max(20, int(width * 0.055))
    safe_bottom = int(height * 0.15)
    max_width = int(width * (0.58 if layout == "left-title" else 0.88))
    hfont, hlines = fit(draw, headline, max_width, 3, max(32, int(width * 0.075)), 22)
    sfont, slines = fit(draw, subheadline, max_width, 3, max(22, int(width * 0.04)), 16) if subheadline else (None, [])
    line_gap = max(6, int(height * 0.006))
    def block_height(lines, font):
        return sum(draw.textbbox((0, 0), line, font=font, stroke_width=1)[3] for line in lines) + max(0, len(lines) - 1) * line_gap
    total = block_height(hlines, hfont) + (line_gap * 2 + block_height(slines, sfont) if slines and sfont else 0)
    if layout == "bottom-card":
        y = height - safe_bottom - total - margin * 2
    else:
        y = margin * 2
    x = margin
    box = (max(0, x - margin // 2), max(0, y - margin // 2), min(width, x + max_width + margin // 2), min(height - safe_bottom, y + total + margin // 2))
    if style == "panel":
        draw.rounded_rectangle(box, radius=max(12, width // 40), fill=(0, 0, 0, 122))
    if badge:
        bfont = load_font(badge, max(16, int(width * 0.035)))
        bbox = draw.textbbox((0, 0), badge, font=bfont)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        by = max(margin // 2, y - bh - margin)
        draw.rounded_rectangle((x, by, x + bw + margin, by + bh + margin // 2), radius=bh // 2, fill=(255, 70, 70, 235))
        draw.text((x + margin // 2, by + margin // 5), badge, font=bfont, fill="white")
    for line in hlines:
        draw.text((x, y), line, font=hfont, fill="white", stroke_width=max(1, width // 360), stroke_fill=(0, 0, 0, 210))
        y += draw.textbbox((0, 0), line, font=hfont, stroke_width=1)[3] + line_gap
    if slines and sfont:
        y += line_gap
        for line in slines:
            draw.text((x, y), line, font=sfont, fill=(245, 245, 245, 255), stroke_width=1, stroke_fill=(0, 0, 0, 180))
            y += draw.textbbox((0, 0), line, font=sfont, stroke_width=1)[3] + line_gap
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(output, quality=95)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--headline", required=True)
    parser.add_argument("--subheadline", default="")
    parser.add_argument("--badge", default="")
    parser.add_argument("--layout", choices=("top-title", "left-title", "bottom-card"), default="top-title")
    parser.add_argument("--style", choices=("ugc", "panel"), default="ugc")
    args = parser.parse_args()
    try:
        render(args.image, args.output, args.headline, args.subheadline, args.badge, args.layout, args.style)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
