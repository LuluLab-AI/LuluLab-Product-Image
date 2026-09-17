from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts" / "validate_image_blueprint.py")
validator = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(validator)


def sample(card_count=9, generation_mode="individual"):
    payload = {
        "productBrief": {"price": "", "promotion": "", "productImages": [{"path": "product.png"}]},
        "userConfig": {
            "creativeMode": "original", "adFormat": "carousel", "cardsPerSet": card_count,
            "setCount": 1, "aspectRatio": "9:16", "targetLanguage": "en-US",
            "creatorMode": "none", "storyStyle": "storyDrivenCarousel", "generationMode": "individual",
        },
        "creatorBrief": {"creatorMode": "none", "creatorImages": []},
        "benchmarkAsset": {"type": "none", "videoPath": "", "imagePaths": []},
    }
    cards = []
    safe_prompt = (
        "Everyday product scene with a clean top safe area; no collage; no contact sheet; "
        "no split screen; no grid; no advertising text; no subtitles; "
        "no watermark; no added logo; preserve original product identity; no people; no hands; "
        "no human body parts."
    )
    for index in range(1, card_count + 1):
        function = "hook" if index == 1 else ("cta" if index == card_count else ("proof" if index in (3, 5) else "problem"))
        cards.append({
            "cardId": f"c{index}", "order": index, "function": function,
            "objective": f"objective {index}", "storyBeat": f"beat {index}",
            "newInformation": f"new information {index}", "swipeReason": f"next {index}" if index < card_count else "",
            "headline": f"headline {index}", "subheadline": "", "badge": "", "textLayout": "top-title",
            "visualGoal": f"goal {index}", "scene": "everyday home", "creator": "", "creatorAction": "",
            "productRole": "in-use product", "productState": "unchanged", "composition": "single focal point",
            "camera": "phone close-up", "lighting": "natural", "background": "home",
            "proofElement": f"visible detail {index}" if index in (3, 5) else "",
            "imagePrompt": safe_prompt, "negativePrompt": "distortion",
            "reference": {"stageIds": [], "shotIds": [], "assetIds": [], "referenceFrameTime": None},
        })
    blueprint = {
        "schemaVersion": "2.0",
        "strategy": {
            "sourceType": "original", "bigIdea": "simple", "angleType": "problem-solution",
            "targetAudience": "adults", "audienceInsight": "needs simplicity",
            "coreSellingPoint": "visible design", "hookType": "problem", "hookMechanism": "contrast",
            "proofPlan": "two visible proof moments", "conversionPath": "discover",
            "visualDNA": "candid phone photography", "creatorStrategy": "object-led",
            "conceptCandidates": ["problem", "result", "listicle"], "selectedConceptReason": "best visual story",
        },
        "cardPlan": {"cardCount": card_count, "progression": "hook to proof to CTA", "generationMode": generation_mode},
        "cards": cards,
        "publishCopy": {
            "language": "en-US", "caption": "A simpler setup", "cta": "Worth checking out.",
            "hashtags": [], "musicMood": "light",
            "chineseTranslation": {"caption": "更简单的布置。", "cta": "值得看看。"},
        },
    }
    return payload, blueprint


def test_valid_v2_blueprint():
    payload, blueprint = sample()
    assert validator.validate(blueprint, payload)["schemaVersion"] == "2.0"


def test_rejects_grid_generation_for_new_tasks():
    payload, blueprint = sample()
    blueprint["cardPlan"]["generationMode"] = "grid9"
    try:
        validator.validate(blueprint, payload)
    except validator.BlueprintError:
        return
    raise AssertionError("new tasks must use individual generation")


def test_accepts_user_selected_card_count():
    payload, blueprint = sample(card_count=7)
    assert validator.validate(blueprint, payload)["cardPlan"]["cardCount"] == 7


def test_rejects_unprovided_price():
    payload, blueprint = sample()
    blueprint["cards"][0]["headline"] = "$19.99 today"
    try:
        validator.validate(blueprint, payload)
    except validator.BlueprintError:
        return
    raise AssertionError("unprovided price should fail")


def test_rejects_creator_in_none_mode():
    payload, blueprint = sample()
    blueprint["cards"][0]["creator"] = "woman"
    try:
        validator.validate(blueprint, payload)
    except validator.BlueprintError:
        return
    raise AssertionError("creatorMode=none should fail")


def test_rejects_legacy_schema_and_wrong_language():
    payload, blueprint = sample()
    blueprint["schemaVersion"] = "1.2"
    try:
        validator.validate(blueprint, payload)
    except validator.BlueprintError:
        pass
    else:
        raise AssertionError("legacy schema should fail")
    blueprint["schemaVersion"] = "2.0"
    blueprint["publishCopy"]["language"] = "fr-FR"
    try:
        validator.validate(blueprint, payload)
    except validator.BlueprintError:
        return
    raise AssertionError("publish language should match targetLanguage")
