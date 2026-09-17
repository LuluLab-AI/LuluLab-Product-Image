#!/usr/bin/env python3
"""Split a grid6 or grid9 image into exact 9:16 cards without stretching."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageOps


LAYOUTS = {
    6: (3, 2),
    9: (3, 3),
}


def _infer_card_count(width: int, height: int) -> int:
    if width <= 0 or height <= 0:
        raise ValueError("源图片尺寸无效。")
    ratio = width / height
    expected = {
        6: 27 / 32,
        9: 9 / 16,
    }
    return min(expected, key=lambda count: abs(ratio - expected[count]))


def _validate_boxes(boxes: Sequence[Sequence[int]], count: int, width: int, height: int) -> None:
    if len(boxes) != count:
        raise ValueError(f"需要 {count} 个按阅读顺序排列的像素框。")
    for box in boxes:
        if len(box) != 4 or not all(isinstance(value, int) and not isinstance(value, bool) for value in box):
            raise ValueError("边界必须是四个整数。")
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError("边界超出原图。")


def _axis_samples(image: Image.Image, axis: str):
    """Return per-line luminance values on a bounded perpendicular sample."""
    gray = image.convert("L")
    width, height = gray.size
    if axis == "x":
        sample = gray.resize((width, min(height, 512)), Image.Resampling.BILINEAR)
        return [list(sample.crop((x, 0, x + 1, sample.height)).tobytes()) for x in range(width)]
    sample = gray.resize((min(width, 512), height), Image.Resampling.BILINEAR)
    return [list(sample.crop((0, y, sample.width, y + 1)).tobytes()) for y in range(height)]


def _line_mean(values):
    return sum(values) / len(values)


def _line_std(values, mean=None):
    mean = _line_mean(values) if mean is None else mean
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _mean_abs_difference(first, second):
    return sum(abs(a - b) for a, b in zip(first, second)) / len(first)


def _detect_seam_bands(image: Image.Image, divisions: int, axis: str):
    """Detect separator bands or hard panel transitions near expected divisions.

    Returns half-open [start, end) bands. A zero-width band means a clean hard
    transition with no gutter pixels to discard.
    """
    lines = _axis_samples(image, axis)
    length = len(lines)
    means = [_line_mean(line) for line in lines]
    stds = [_line_std(line, mean) for line, mean in zip(lines, means)]
    adjacent = [0.0] + [
        _mean_abs_difference(lines[index - 1], lines[index])
        for index in range(1, length)
    ]
    bands = []
    diagnostics = []

    for division in range(1, divisions):
        expected = division * length / divisions
        radius = max(4, round(length / divisions * 0.12))
        lower = max(1, round(expected) - radius)
        upper = min(length - 1, round(expected) + radius)
        local_stds = stds[lower:upper + 1]
        local_diffs = adjacent[lower:upper + 1]
        std_threshold = min(18.0, max(4.0, statistics.median(local_stds) * 0.45))

        runs = []
        start = None
        for coordinate in range(lower, upper + 1):
            if stds[coordinate] <= std_threshold:
                start = coordinate if start is None else start
            elif start is not None:
                runs.append((start, coordinate))
                start = None
        if start is not None:
            runs.append((start, upper + 1))

        best_run = None
        best_score = float("-inf")
        for start, end in runs:
            if end - start > max(12, round(length / divisions * 0.08)):
                continue
            before = statistics.mean(means[max(lower, start - 3):start]) if start > lower else means[start]
            after = statistics.mean(means[end:min(upper + 1, end + 3)]) if end <= upper else means[end - 1]
            run_mean = statistics.mean(means[start:end])
            contrast = abs(run_mean - before) + abs(run_mean - after)
            distance = abs(((start + end) / 2) - expected)
            score = contrast + (std_threshold - statistics.mean(stds[start:end])) * 2 - distance * 0.2
            if contrast >= 12 and score > best_score:
                best_score = score
                best_run = (start, end, contrast)

        if best_run is not None:
            start, end, confidence = best_run
            bands.append([start, end])
            diagnostics.append({"expected": round(expected, 2), "band": [start, end], "kind": "separator", "confidence": round(confidence, 2)})
            continue

        peak = max(range(lower, upper + 1), key=lambda coordinate: adjacent[coordinate])
        median_diff = statistics.median(local_diffs)
        confidence = adjacent[peak]
        if confidence < max(8.0, median_diff * 3.0):
            raise ValueError(
                f"无法可靠识别{axis}轴第 {division} 条网格分隔线；"
                "请传入 --bounds 的实际像素框，或在人工确认网格精确等分后使用 --equal-grid。"
            )
        bands.append([peak, peak])
        diagnostics.append({"expected": round(expected, 2), "band": [peak, peak], "kind": "hard-transition", "confidence": round(confidence, 2)})

    return bands, diagnostics


def _boxes_from_seams(width: int, height: int, columns: int, rows: int, image: Image.Image):
    vertical, vertical_diagnostics = _detect_seam_bands(image, columns, "x")
    horizontal, horizontal_diagnostics = _detect_seam_bands(image, rows, "y")
    x_ranges = list(zip([0] + [band[1] for band in vertical], [band[0] for band in vertical] + [width]))
    y_ranges = list(zip([0] + [band[1] for band in horizontal], [band[0] for band in horizontal] + [height]))
    boxes = [[left, top, right, bottom] for top, bottom in y_ranges for left, right in x_ranges]
    return boxes, {"vertical": vertical_diagnostics, "horizontal": horizontal_diagnostics}


def split(
    source,
    output,
    bounds=None,
    width=1080,
    card_count=None,
    equal_grid=False,
    min_cell_width=720,
):
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0 or width % 9:
        raise ValueError("width 必须是 9 的正整数倍。")

    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    source_width, source_height = image.size
    if card_count is None:
        card_count = len(bounds) if bounds is not None else _infer_card_count(source_width, source_height)
    if card_count not in LAYOUTS:
        raise ValueError("card_count 必须为 6 或 9。")
    columns, rows = LAYOUTS[card_count]

    seam_detection = None
    if bounds is not None:
        boxes = bounds
        crop_mode = "explicit-bounds"
    elif equal_grid:
        boxes = [
            [
                round(column * source_width / columns),
                round(row * source_height / rows),
                round((column + 1) * source_width / columns),
                round((row + 1) * source_height / rows),
            ]
            for row in range(rows)
            for column in range(columns)
        ]
        crop_mode = "confirmed-equal-grid"
    else:
        boxes, seam_detection = _boxes_from_seams(
            source_width, source_height, columns, rows, image
        )
        crop_mode = "detected-seams"
    _validate_boxes(boxes, card_count, source_width, source_height)
    if isinstance(min_cell_width, bool) or not isinstance(min_cell_width, int) or min_cell_width < 0:
        raise ValueError("min_cell_width 必须为非负整数。")
    if min_cell_width:
        low_resolution = [
            (index, right - left, bottom - top)
            for index, (left, top, right, bottom) in enumerate(boxes, 1)
            if right - left < min_cell_width
        ]
        if low_resolution:
            summary = ", ".join(
                f"c{index}={cell_width}x{cell_height}"
                for index, cell_width, cell_height in low_resolution
            )
            raise ValueError(
                f"网格源分辨率不足（最低每格宽度 {min_cell_width}px）: {summary}。"
                "终稿必须改用更高分辨率网格或 individual 逐张生成。"
            )

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    output_height = width // 9 * 16
    records = []
    for index, box in enumerate(boxes, 1):
        cell = image.crop(tuple(box))
        name = f"visual_{index:02d}.png"
        ImageOps.fit(
            cell,
            (width, output_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        ).save(output / name)
        records.append({
            "cardId": f"c{index}",
            "order": index,
            "file": name,
            "sourceBox": list(box),
            "sourceSize": list(cell.size),
            "outputSize": [width, output_height],
            "method": f"{crop_mode} then proportional center-fit",
        })

    manifest = {
        "source": str(source),
        "sourceSize": [source_width, source_height],
        "grid": {
            "cardCount": card_count,
            "columns": columns,
            "rows": rows,
            "order": "row-major",
            "cropMode": crop_mode,
            "seamDetection": seam_detection,
        },
        "cards": records,
    }
    (output / "crop_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bounds", type=Path, help="JSON array of 6 or 9 [left,top,right,bottom] boxes")
    parser.add_argument("--cards", type=int, choices=(6, 9), help="网格卡片数；省略时按 bounds 或图片比例推断")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument(
        "--equal-grid",
        action="store_true",
        help="仅在人工确认分隔线严格等分时启用；默认自动识别实际分隔带",
    )
    parser.add_argument(
        "--min-cell-width",
        type=int,
        default=720,
        help="终稿每格的最低源像素宽度，默认 720",
    )
    parser.add_argument(
        "--allow-low-resolution",
        action="store_true",
        help="仅用于测试/草稿；跳过每格最低源分辨率检查",
    )
    args = parser.parse_args()
    try:
        bounds = json.loads(args.bounds.read_text(encoding="utf-8")) if args.bounds else None
        split(
            args.image,
            args.output_dir,
            bounds,
            args.width,
            args.cards,
            args.equal_grid,
            0 if args.allow_low_resolution else args.min_cell_width,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
