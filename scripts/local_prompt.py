#!/usr/bin/env python3
"""Build the local model prompt for one imageAdBlueprint v2.0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


class PromptError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PromptError("输入必须是 JSON 对象。")
    return value


def build_prompt(payload: Mapping[str, Any], reference_logic: Mapping[str, Any] | None = None) -> str:
    brief = payload.get("productBrief")
    config = payload.get("userConfig")
    if not isinstance(brief, Mapping) or not isinstance(config, Mapping):
        raise PromptError("缺少 productBrief 或 userConfig。")

    data: dict[str, Any] = {"input": payload}
    if reference_logic:
        data["referenceAdLogic"] = reference_logic
    encoded = json.dumps(data, ensure_ascii=False, indent=2)

    return f'''你是 TikTok Carousel 广告导演、UGC 创意策划师和电商转化专家。根据下方输入生成且只生成一个 imageAdBlueprint v2.0 JSON 对象；不得输出 Markdown、解释、推理过程或额外文字。

目标：第一张制造停留，中间每张提供新信息和继续滑动的理由，最后自然完成种草与转化。Carousel 不是产品详情页，也不是连续包装展示。

必须使用以下顶层结构与字段：
- schemaVersion: 固定为 "2.0"。
- strategy: sourceType, bigIdea, angleType, targetAudience, audienceInsight, coreSellingPoint, hookType, hookMechanism, proofPlan, conversionPath, visualDNA, creatorStrategy, conceptCandidates, selectedConceptReason。
- cardPlan: cardCount, progression, generationMode。
- cards: 每张完整包含 cardId, order, function, objective, storyBeat, newInformation, swipeReason, headline, subheadline, badge, textLayout, visualGoal, scene, creator, creatorAction, productRole, productState, composition, camera, lighting, background, proofElement, imagePrompt, negativePrompt, reference；reference 包含 stageIds, shotIds, assetIds, referenceFrameTime。
- publishCopy: language, caption, cta, hashtags, musicMood, chineseTranslation.caption, chineseTranslation.cta。

硬规则：
- cards 数量严格等于 userConfig.cardsPerSet；单图广告只能 1 张。第一张 function=hook，最后一张必须有转化目的。
- 先内部设计 3 个真正不同的 Concept Candidates，并完整保留在 strategy.conceptCandidates；在 selectedConceptReason 说明选择原因。
- 每张 newInformation 必须非空且互不重复；除最后一张外，每张 swipeReason 必须非空。一张只表达一个核心信息。
- Carousel 至少 5 张时，至少安排 2 个 Proof Card 或 Proof Moment；proofElement 必须描述可见且不虚构的证据。
- generationMode 必须为 individual。无论 cardsPerSet 是 1～10 中的任何数量，都逐张独立生成完整 9:16 原图；不得先生成九宫格、六宫格或其他拼图再裁剪。
- creativeMode=benchmarkVideo 或 benchmarkCarousel 时只迁移 referenceAdLogic 的方法，不复制原品牌、人物身份、文案、价格、优惠或 nonTransferableFacts；必须重新设计静态滑动叙事。
- 只使用 productBrief 中明确确认或产品图可靠可见的事实。price/promotion 为空时不得出现价格、折扣、优惠、赠品或配送承诺。
- creatorMode=none 时 creator 和 creatorAction 必须为空，imagePrompt 必须明确 no people, no hands, no human body parts。
- creatorMode=auto 时使用同一个成年虚构达人，并在 strategy.creatorStrategy 固定身份与服装；不得生成独立人物参考板。
- creatorMode=referCreator 时，用户达人图锁定所有含人物 Card 的身份、面部、发色和基础服装特征。
- imagePrompt 只描述单张纯视觉底图，必须逐字包含这些安全要求：no collage; no contact sheet; no split screen; no grid; no advertising text; no subtitles; no watermark; no added logo; preserve original product identity。还要说明文案安全区，且实际产品图锁定颜色、轮廓、包装、Logo、结构、可见部件和关键视觉特征。
- textLayout 仅可为 top-title、left-title、bottom-card。主要广告文字只放 headline、subheadline、badge。
- publishCopy.language 必须等于 userConfig.targetLanguage。每套只有一条 caption 和 CTA；若发布语言不是中文，chineseTranslation 必须给出完整中文翻译。
- reference 的三个 IDs 字段必须为数组；referenceFrameTime 只能为 null 或非负秒数。
- sourceType 必须与 creativeMode 一致：original、benchmarkVideo 或 benchmarkCarousel。

输入数据：
<input-data>
{encoded}
</input-data>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--reference-logic", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = _load(args.input)
        reference = _load(args.reference_logic) if args.reference_logic else None
        result = build_prompt(payload, reference)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result + "\n", encoding="utf-8")
        else:
            print(result)
    except (OSError, json.JSONDecodeError, PromptError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
