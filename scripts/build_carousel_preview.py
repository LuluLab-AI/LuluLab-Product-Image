#!/usr/bin/env python3
"""Build a labeled contact sheet for final Carousel cards."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def build(images: list[Path], output: Path, columns: int = 3, thumb_width: int = 240) -> Path:
    if not images:
        raise ValueError("至少需要一张图片。")
    opened = [Image.open(path).convert("RGB") for path in images]
    ratio = opened[0].height / opened[0].width
    thumb_height = max(1, int(thumb_width * ratio))
    label_height = 36
    rows = math.ceil(len(opened) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "#181818")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(opened):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        thumb = item.copy()
        thumb.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        px = x + (thumb_width - thumb.width) // 2
        py = y + (thumb_height - thumb.height) // 2
        sheet.paste(thumb, (px, py))
        draw.text((x + 10, y + thumb_height + 10), f"CARD {index + 1:02d}", font=font, fill="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=3)
    args = parser.parse_args()
    try:
        if args.columns < 1:
            raise ValueError("columns 必须大于 0。")
        build(args.images, args.output, args.columns)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
