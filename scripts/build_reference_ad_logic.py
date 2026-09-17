#!/usr/bin/env python3
"""Extract an ad-safe referenceAdLogic layer from a RecreateVideoPromptV3 blueprint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _first(mapping: dict[str, Any], names: tuple[str, ...], default: Any = "") -> Any:
    for name in names:
        if name in mapping and mapping[name] not in (None, "", []):
            return mapping[name]
    return default


def _dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _dicts(child)


def build(blueprint: dict[str, Any]) -> dict[str, Any]:
    stages: list[Any] = []
    patterns: list[str] = []
    assets: list[Any] = []
    hook = {"mechanism": "", "visualExpression": "", "whyItWorks": ""}
    proof = ""
    cta = ""
    for node in _dicts(blueprint):
        if not stages:
            value = _first(node, ("阶段拆解", "stageSequence", "stages"), [])
            if isinstance(value, list):
                stages = value
        if not assets:
            value = _first(node, ("爆款资产", "viralAssets", "strongestAssets"), [])
            if isinstance(value, list):
                assets = value
        if not hook["mechanism"]:
            hook["mechanism"] = str(_first(node, ("hookMechanism", "Hook类型", "钩子机制"), ""))
            hook["visualExpression"] = str(_first(node, ("visualExpression", "视觉钩子", "画面描述"), ""))
            hook["whyItWorks"] = str(_first(node, ("whyItWorks", "停留原因"), ""))
        proof = proof or str(_first(node, ("proofMechanism", "Proof方式", "证明机制"), ""))
        cta = cta or str(_first(node, ("ctaMechanism", "CTA方式", "转化方式"), ""))
        dna = _first(node, ("视觉风格DNA", "visualDNA", "构图", "composition"), "")
        if isinstance(dna, str) and dna.strip() and dna.strip() not in patterns:
            patterns.append(dna.strip())

    non_transferable = [
        "原品牌与 Logo", "原产品名称、参数、成分与功效", "原价格、折扣、促销与销量",
        "原人物身份", "原广告文案与具体承诺", "原环境中的专属品牌资产",
    ]
    return {
        "hook": hook,
        "stageSequence": stages,
        "proofMechanism": proof,
        "ctaMechanism": cta,
        "visualPatterns": patterns[:12],
        "strongestAssets": assets[:12],
        "reusablePatterns": ["Hook 类型", "信息顺序", "产品展示逻辑", "Proof 方式", "CTA 逻辑", "场景与构图逻辑", "视觉节奏"],
        "nonTransferableFacts": non_transferable,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.blueprint.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("videoBlueprint 必须是对象。")
        result = build(value)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
