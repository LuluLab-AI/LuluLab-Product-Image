#!/usr/bin/env python3
"""Validate imageAdBlueprint v2.0 structure and user-authorized facts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping


class BlueprintError(ValueError):
    pass


STRATEGY_FIELDS = (
    "sourceType", "bigIdea", "angleType", "targetAudience", "audienceInsight",
    "coreSellingPoint", "hookType", "hookMechanism", "proofPlan",
    "conversionPath", "visualDNA", "creatorStrategy", "selectedConceptReason",
)
CARD_TEXT_FIELDS = (
    "function", "objective", "storyBeat", "newInformation", "swipeReason",
    "headline", "subheadline", "badge", "visualGoal", "scene", "creator",
    "creatorAction", "productRole", "productState", "composition", "camera",
    "lighting", "background", "proofElement", "imagePrompt", "negativePrompt",
)
TEXT_LAYOUTS = {"top-title", "left-title", "bottom-card"}
CREATIVE_MODES = {"original", "benchmarkVideo", "benchmarkCarousel"}
CREATOR_MODES = {"auto", "referCreator", "none"}
STORY_STYLES = {"storyDrivenCarousel", "creatorRecommendation", "productShowcase", "poster"}
GENERATION_MODES = {"individual"}
CONVERSION_FUNCTIONS = {"cta", "conversion", "offer", "trust", "benefit"}

PRICE_RE = re.compile(
    r"(?:[$€£¥]\s*\d|\b\d+(?:\.\d+)?\s*(?:%\s*off|percent off|usd|eur|rmb|cny)\b)", re.I
)
PROMO_RE = re.compile(
    r"\b(?:buy\s*\d+\s*get|free\s+(?:gift|shipping)|limited[- ]time offer|discount|sale|bogo)\b|"
    r"优惠|折扣|促销|满减|买\S*送|包邮|赠品", re.I
)
NO_AD_TEXT_RE = re.compile(r"no\s+(?:advertising|ad)\s+text|without\s+(?:advertising|ad)\s+text|no\s+text|禁止.{0,8}(?:广告)?文字|无广告文字", re.I)
NO_COLLAGE_RE = re.compile(r"no\s+collage", re.I)
NO_CONTACT_SHEET_RE = re.compile(r"no\s+contact\s+sheet", re.I)
NO_SPLIT_SCREEN_RE = re.compile(r"no\s+split\s+screen", re.I)
NO_GRID_RE = re.compile(r"no\s+grid", re.I)
NO_SUBTITLE_RE = re.compile(r"no\s+subtitles?|without\s+subtitles?|禁止.{0,8}字幕|无字幕", re.I)
NO_WATERMARK_RE = re.compile(r"no\s+watermarks?|without\s+watermarks?|禁止.{0,8}水印|无水印", re.I)
NO_ADDED_LOGO_RE = re.compile(r"no\s+added\s+logos?|do\s+not\s+add\s+(?:a\s+)?logos?|不(?:新增|添加).{0,6}logo|禁止.{0,8}新增.{0,4}logo", re.I)
IDENTITY_RE = re.compile(r"preserve\s+(?:the\s+)?original\s+product\s+identity|lock.{0,20}product\s+identity|产品身份|保持.{0,20}产品.{0,20}(?:颜色|轮廓|包装|结构)", re.I)
NO_PEOPLE_RE = re.compile(r"no\s+(?:people|person|humans?|creator|model)|无人|不出现.{0,6}(?:人物|真人|达人)", re.I)
NO_HANDS_RE = re.compile(r"no\s+(?:hands?|human\s+body\s+parts?)|无手部|不出现.{0,6}(?:手|人体局部)", re.I)


def _obj(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BlueprintError(f"{field} 必须是对象。")
    return value


def _text(value: Any, field: str, required: bool = False) -> str:
    if not isinstance(value, str):
        raise BlueprintError(f"{field} 必须是字符串。")
    result = value.strip()
    if required and not result:
        raise BlueprintError(f"{field} 不能为空。")
    return result


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BlueprintError(f"{field} 必须是字符串数组。")
    return value


def _normalized(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()


def _is_chinese_language(language: str) -> bool:
    return language.casefold().startswith(("zh", "cmn", "yue"))


def _looks_like_packshot(card: Mapping[str, Any]) -> bool:
    role = str(card.get("productRole", "")).casefold()
    scene = str(card.get("scene", "")).casefold()
    function = str(card.get("function", "")).casefold()
    no_creator = not str(card.get("creator", "")).strip() and not str(card.get("creatorAction", "")).strip()
    package_role = any(token in role for token in ("package", "packaging", "packshot", "包装", "产品正面"))
    plain_scene = not scene or any(token in scene for token in ("white background", "studio", "plain background", "白底", "棚拍"))
    return no_creator and package_role and plain_scene and function not in {"proof", "usage_proof", "detail_proof"}


def validate(blueprint: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if blueprint.get("schemaVersion") != "2.0":
        raise BlueprintError("schemaVersion 必须为 2.0。")

    brief = _obj(payload.get("productBrief"), "input.productBrief")
    config = _obj(payload.get("userConfig"), "input.userConfig")
    product_images = brief.get("productImages")
    if not isinstance(product_images, list) or not product_images:
        raise BlueprintError("input.productBrief.productImages 必须至少包含一张产品图。")
    for index, product_image in enumerate(product_images, 1):
        image = _obj(product_image, f"input.productBrief.productImages[{index}]")
        _text(image.get("path"), f"input.productBrief.productImages[{index}].path", True)
    creative_mode = config.get("creativeMode", "original")
    if creative_mode not in CREATIVE_MODES:
        raise BlueprintError("creativeMode 无效。")
    story_style = config.get("storyStyle", "storyDrivenCarousel")
    if story_style not in STORY_STYLES:
        raise BlueprintError("storyStyle 无效。")
    requested_generation = config.get("generationMode", "individual")
    if requested_generation not in GENERATION_MODES:
        raise BlueprintError("generationMode 无效。")
    if config.get("aspectRatio", "9:16") != "9:16":
        raise BlueprintError("v2.0 仅支持 9:16 图片。")
    set_count = config.get("setCount", 1)
    if isinstance(set_count, bool) or not isinstance(set_count, int) or not 1 <= set_count <= 10:
        raise BlueprintError("setCount 必须是 1～10 的整数。")

    benchmark_asset = _obj(payload.get("benchmarkAsset", {}), "input.benchmarkAsset")
    benchmark_type = benchmark_asset.get("type", "none")
    if creative_mode == "original" and benchmark_type != "none":
        raise BlueprintError("original 模式下 benchmarkAsset.type 必须为 none。")
    if creative_mode == "benchmarkVideo":
        if benchmark_type not in {"video", "benchmarkVideo"}:
            raise BlueprintError("benchmarkVideo 模式需要视频类型 benchmarkAsset。")
        _text(benchmark_asset.get("videoPath"), "input.benchmarkAsset.videoPath", True)
    if creative_mode == "benchmarkCarousel":
        if benchmark_type not in {"carousel", "images", "benchmarkCarousel"}:
            raise BlueprintError("benchmarkCarousel 模式需要图文类型 benchmarkAsset。")
        image_paths = benchmark_asset.get("imagePaths")
        if not isinstance(image_paths, list) or not image_paths or not all(isinstance(path, str) and path.strip() for path in image_paths):
            raise BlueprintError("benchmarkCarousel 模式需要非空的 benchmarkAsset.imagePaths。")

    creator_brief = _obj(payload.get("creatorBrief", {}), "input.creatorBrief")
    creator_mode = config.get("creatorMode", creator_brief.get("creatorMode", "auto"))
    if creator_mode not in CREATOR_MODES:
        raise BlueprintError("creatorMode 无效。")
    brief_creator_mode = creator_brief.get("creatorMode")
    if brief_creator_mode is not None and brief_creator_mode != creator_mode:
        raise BlueprintError("userConfig.creatorMode 与 creatorBrief.creatorMode 不一致。")
    if creator_mode == "referCreator":
        creator_images = creator_brief.get("creatorImages")
        if not isinstance(creator_images, list) or not creator_images:
            raise BlueprintError("creatorMode=referCreator 时必须提供 creatorImages。")

    ad_format = config.get("adFormat", "carousel")
    if ad_format not in {"carousel", "single"}:
        raise BlueprintError("adFormat 无效。")
    expected = config.get("cardsPerSet", 9)
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise BlueprintError("cardsPerSet 必须是整数。")
    if ad_format == "single":
        expected = 1
    elif not 2 <= expected <= 10:
        raise BlueprintError("Carousel cardsPerSet 必须在 2～10。")

    strategy = _obj(blueprint.get("strategy"), "strategy")
    for field in STRATEGY_FIELDS:
        _text(strategy.get(field), f"strategy.{field}", True)
    if strategy.get("sourceType") != creative_mode:
        raise BlueprintError("strategy.sourceType 必须与 userConfig.creativeMode 一致。")
    candidates = strategy.get("conceptCandidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise BlueprintError("strategy.conceptCandidates 必须恰好包含 3 个候选。")
    if any(not isinstance(item, (str, Mapping)) or not item for item in candidates):
        raise BlueprintError("每个 Concept Candidate 必须是非空字符串或对象。")

    card_plan = _obj(blueprint.get("cardPlan"), "cardPlan")
    if card_plan.get("cardCount") != expected:
        raise BlueprintError(f"cardPlan.cardCount 必须为 {expected}。")
    _text(card_plan.get("progression"), "cardPlan.progression", True)
    actual_generation = card_plan.get("generationMode")
    if actual_generation != "individual":
        raise BlueprintError("cardPlan.generationMode 必须为 individual；新任务不得生成网格后裁剪。")
    if requested_generation != "individual":
        raise BlueprintError("userConfig.generationMode 必须为 individual。")

    cards = blueprint.get("cards")
    if not isinstance(cards, list) or len(cards) != expected:
        raise BlueprintError(f"cards 数量必须为 {expected}。")

    functions: list[str] = []
    new_information: list[str] = []
    all_copy: list[str] = []
    proof_moments = 0
    consecutive_packshots = 0

    for index, card in enumerate(cards, 1):
        item = _obj(card, f"cards[{index}]")
        if item.get("cardId") != f"c{index}" or item.get("order") != index:
            raise BlueprintError(f"第 {index} 张必须使用 cardId=c{index} 且 order={index}。")

        values: dict[str, str] = {}
        for field in CARD_TEXT_FIELDS:
            required = field in {
                "function", "objective", "storyBeat", "newInformation", "visualGoal",
                "scene", "productRole", "productState", "composition", "camera",
                "lighting", "background", "imagePrompt", "negativePrompt",
            } or (field == "swipeReason" and index < expected)
            values[field] = _text(item.get(field), f"cards[{index}].{field}", required)
            all_copy.append(values[field])

        if item.get("textLayout") not in TEXT_LAYOUTS:
            raise BlueprintError(f"第 {index} 张 textLayout 无效。")
        functions.append(values["function"].casefold())
        normalized_info = _normalized(values["newInformation"])
        if not normalized_info:
            raise BlueprintError(f"第 {index} 张 newInformation 不能为空。")
        if normalized_info in new_information:
            raise BlueprintError(f"第 {index} 张 newInformation 与前卡重复。")
        new_information.append(normalized_info)

        prompt = values["imagePrompt"]
        for pattern, message in (
            (NO_COLLAGE_RE, "未明确禁止拼贴"),
            (NO_CONTACT_SHEET_RE, "未明确禁止联络表"),
            (NO_SPLIT_SCREEN_RE, "未明确禁止分屏"),
            (NO_GRID_RE, "未明确禁止网格"),
            (NO_AD_TEXT_RE, "未明确禁止模型生成广告文字"),
            (NO_SUBTITLE_RE, "未明确禁止字幕"),
            (NO_WATERMARK_RE, "未明确禁止水印"),
            (NO_ADDED_LOGO_RE, "未明确禁止新增 Logo"),
            (IDENTITY_RE, "未明确锁定原产品身份"),
        ):
            if not pattern.search(prompt):
                raise BlueprintError(f"第 {index} 张 imagePrompt {message}。")

        if creator_mode == "none":
            if values["creator"] or values["creatorAction"]:
                raise BlueprintError(f"第 {index} 张违反 creatorMode=none。")
            if not NO_PEOPLE_RE.search(prompt) or not NO_HANDS_RE.search(prompt):
                raise BlueprintError(f"第 {index} 张 imagePrompt 必须明确排除人物、手和人体局部。")

        reference = _obj(item.get("reference"), f"cards[{index}].reference")
        for field in ("stageIds", "shotIds", "assetIds"):
            _string_list(reference.get(field), f"cards[{index}].reference.{field}")
        frame_time = reference.get("referenceFrameTime")
        if frame_time is not None and (
            isinstance(frame_time, bool) or not isinstance(frame_time, (int, float)) or frame_time < 0
        ):
            raise BlueprintError(f"第 {index} 张 referenceFrameTime 必须为空或非负数。")

        if "proof" in functions[-1] or values["proofElement"]:
            proof_moments += 1
        consecutive_packshots = consecutive_packshots + 1 if _looks_like_packshot(item) else 0
        if consecutive_packshots >= 3:
            raise BlueprintError("不得连续出现 3 张或更多纯包装产品图。")

    if expected > 1:
        if functions[0] != "hook":
            raise BlueprintError("第一张 function 必须为 hook。")
        if functions[-1] not in CONVERSION_FUNCTIONS:
            raise BlueprintError("最后一张必须有明确转化目的。")
    if expected >= 5 and proof_moments < 2:
        raise BlueprintError("Carousel 至少 5 张时必须包含至少 2 个 Proof Card 或 Proof Moment。")

    publish = _obj(blueprint.get("publishCopy"), "publishCopy")
    target_language = _text(config.get("targetLanguage", "en-US"), "input.userConfig.targetLanguage", True)
    language = _text(publish.get("language"), "publishCopy.language", True)
    if language != target_language:
        raise BlueprintError("publishCopy.language 必须与 userConfig.targetLanguage 一致。")
    for field in ("caption", "cta"):
        all_copy.append(_text(publish.get(field), f"publishCopy.{field}", True))
    all_copy.append(_text(publish.get("musicMood"), "publishCopy.musicMood", False))
    hashtags = _string_list(publish.get("hashtags"), "publishCopy.hashtags")
    all_copy.extend(hashtags)
    translation = _obj(publish.get("chineseTranslation"), "publishCopy.chineseTranslation")
    for field in ("caption", "cta"):
        translated = _text(
            translation.get(field), f"publishCopy.chineseTranslation.{field}", not _is_chinese_language(language)
        )
        all_copy.append(translated)

    combined = "\n".join(all_copy)
    if not str(brief.get("price", "")).strip() and PRICE_RE.search(combined):
        raise BlueprintError("用户未提供价格，但 Blueprint 出现价格或折扣数字。")
    if not str(brief.get("promotion", "")).strip() and PROMO_RE.search(combined):
        raise BlueprintError("用户未提供优惠，但 Blueprint 出现促销内容。")
    return dict(blueprint)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validate(_obj(blueprint, "blueprint"), _obj(payload, "input"))
        print(json.dumps({"valid": True, "schemaVersion": "2.0", "cards": len(blueprint["cards"])}, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, BlueprintError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
