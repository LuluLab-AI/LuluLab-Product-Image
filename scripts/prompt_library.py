#!/usr/bin/env python3
"""Validate optional image-ad prompt-library context without accessing a provider."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


FIELDS = ("title", "hook", "cardStructure", "visualStyle", "layoutPattern", "copyPattern", "proofPattern", "conversionPattern", "sellingPoints", "avoid")
STATUSES = {"disabled", "ready", "cached", "unavailable"}


def normalize(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion", "1.0") != "1.0":
        raise ValueError("schemaVersion 必须为 1.0。")
    status = str(value.get("status", "")).strip().lower()
    if status not in STATUSES:
        raise ValueError("提示词库状态无效。")
    raw = value.get("matches", [])
    if not isinstance(raw, list) or len(raw) > 3:
        raise ValueError("matches 必须是最多 3 条的数组。")
    if status not in {"ready", "cached"} and raw:
        raise ValueError("非活动状态不得携带 matches。")
    matches: list[dict[str, Any]] = []
    for index, item in enumerate(raw, 1):
        if not isinstance(item, Mapping) or not str(item.get("templateId", "")).strip():
            raise ValueError(f"第 {index} 条缺少 templateId。")
        out: dict[str, Any] = {"templateId": str(item["templateId"]).strip()}
        score = item.get("score")
        if score is not None:
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise ValueError(f"第 {index} 条 score 必须在 0～1。")
            out["score"] = float(score)
        for field in FIELDS:
            text = item.get(field, "")
            if text and not isinstance(text, str):
                raise ValueError(f"第 {index} 条 {field} 必须是字符串。")
            if isinstance(text, str) and text.strip():
                out[field] = text.strip()
        matches.append(out)
    if status in {"ready", "cached"} and not matches:
        raise ValueError("活动状态至少需要一条 match。")
    return {"schemaVersion": "1.0", "status": status, "source": str(value.get("source", "")), "version": str(value.get("version", "")), "matches": matches}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("输入必须是对象。")
        print(json.dumps(normalize(value), ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
