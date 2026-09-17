#!/usr/bin/env python3
"""Extract one non-final reference frame per selected card time."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def times_from_blueprint(path: Path) -> list[tuple[str, float]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    result: list[tuple[str, float]] = []
    for index, card in enumerate(value.get("cards", []), 1):
        ref = card.get("reference", {}) if isinstance(card, dict) else {}
        timestamp = ref.get("referenceFrameTime") if isinstance(ref, dict) else None
        if timestamp is not None:
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or timestamp < 0:
                raise ValueError(f"第 {index} 张 referenceFrameTime 无效。")
            result.append((str(card.get("cardId", f"c{index}")), float(timestamp)))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ValueError("未找到 ffmpeg。")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for card_id, timestamp in times_from_blueprint(args.blueprint):
            output = args.output_dir / f"{card_id}_reference.png"
            completed = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}", "-i", str(args.video), "-frames:v", "1", "-y", str(output)], capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file():
                raise ValueError(f"{card_id} 抽帧失败：{completed.stderr.strip()}")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
