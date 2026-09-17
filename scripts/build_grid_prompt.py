#!/usr/bin/env python3
"""Build one validated grid6 or grid9 visual-generation prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from validate_image_blueprint import validate


GRID_LAYOUTS = {
    "grid6": {"cards": 6, "rows": 2, "columns": 3, "ratio": "27:32", "size": "3240x3840"},
    "grid9": {"cards": 9, "rows": 3, "columns": 3, "ratio": "9:16", "size": "3240x5760"},
}


def build(blueprint: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    validate(blueprint, payload)
    mode = blueprint["cardPlan"]["generationMode"]
    if mode not in GRID_LAYOUTS:
        raise ValueError("当前 Blueprint 使用 individual；不得构建网格提示词。")
    layout = GRID_LAYOUTS[mode]
    cards = blueprint["cards"]
    if len(cards) != layout["cards"]:
        raise ValueError(f"{mode} 必须恰好包含 {layout['cards']} 张。")

    config = payload.get("userConfig", {})
    creator_brief = payload.get("creatorBrief", {})
    creator_mode = config.get("creatorMode", creator_brief.get("creatorMode", "auto"))
    creator_images = creator_brief.get("creatorImages", [])
    if creator_mode == "none":
        creator_rule = "No people, no hands, and no human body parts in any panel."
    elif creator_mode == "referCreator":
        creator_rule = (
            "Use the supplied creator images as the identity reference for every relevant panel; "
            "preserve face, hair color, and base outfit."
        )
    else:
        creator_rule = (
            "Directly generate one fictional adult creator and keep the exact same identity, hair, "
            "skin tone, age range, outfit, and overall vibe across all relevant panels; do not create a reference sheet."
        )
    if creator_mode == "referCreator" and not creator_images:
        raise ValueError("creatorMode=referCreator 时必须提供 creatorImages。")

    shared = f"""Generate ONE opaque grid image with exactly {layout['columns']} columns by {layout['rows']} rows,
overall {layout['ratio']} ratio, target {layout['size']}. Each independent cell is 9:16, target 1080x1920.
Use strict row-major order: left to right, then top to bottom. Equal cells, zero gutters, no borders.
Nothing may cross cell boundaries: no creator, product, prop, shadow, or composition may span cells.
Every cell needs an independent composition and a clean advertising-copy safe area matching its textLayout.
Reserve the bottom 15% as a TikTok UI-safe area.
Actual supplied product images are mandatory references for every cell and lock the original product identity:
preserve exact color, silhouette, packaging, existing Logo and lettering, structure, visible parts, and key visual features.
No advertising text; no subtitles; no watermark; no added logo; preserve original product identity.
{creator_rule}
Keep one coherent visualDNA across the set while making every cell a distinct story beat with new information.
Default aesthetic: TikTok-native candid phone photography, natural light, believable everyday setting, not a glossy brand poster.
"""
    panels = []
    for card in cards:
        panels.append({key: card.get(key, "") for key in (
            "order", "function", "objective", "storyBeat", "newInformation", "visualGoal",
            "scene", "creator", "creatorAction", "productRole", "productState", "composition",
            "camera", "lighting", "background", "proofElement", "textLayout", "imagePrompt",
            "negativePrompt",
        )})
    return (
        shared
        + "\nStory style: " + config.get("storyStyle", "storyDrivenCarousel")
        + "\nVisual DNA: " + blueprint["strategy"]["visualDNA"]
        + "\nPanels:\n" + json.dumps(panels, ensure_ascii=False, indent=2)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = build(
            json.loads(args.blueprint.read_text(encoding="utf-8")),
            json.loads(args.input.read_text(encoding="utf-8")),
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result + "\n", encoding="utf-8")
        else:
            print(result)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
