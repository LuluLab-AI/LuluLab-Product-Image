from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contract_files_exist():
    required = [
        "SKILL.md", "agents/openai.yaml", "scripts/local_prompt.py",
        "scripts/check_lululab_api_key.py", "scripts/lululab_cli.mjs",
        "scripts/lululab_blueprint_generate.py", "scripts/lululab_image_generate.py",
        "scripts/lululab_product_analyze.py",
        "scripts/workbuddy_preflight.py",
        "scripts/validate_image_blueprint.py", "scripts/render_text_overlay.py",
        "scripts/build_carousel_preview.py", "scripts/build_reference_ad_logic.py",
        "scripts/extract_reference_frames.py", "scripts/split_grid.py",
    ]
    assert all((ROOT / item).is_file() for item in required)


def test_skill_excludes_video_generation():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "name: LuluLab-Product-Image" in text
    assert 'version: "2.4.0"' in text
    assert "display_name: LuluLab-Product-Image" in text
    assert "TikTok Carousel / 抖音图文广告" in text
    assert "不生成：" in text and "- 视频" in text
    assert "render_text_overlay.py" in text
    assert "creatorMode=none" in text
    assert "imageAdBlueprint v2.0" in text
    assert "默认生成 9 张" in text
    assert "不得生成九宫格、六宫格或其他拼图后裁剪" in text
    assert "benchmarkCarousel" in text
    assert "<python> <技能根目录>/scripts/check_lululab_api_key.py check" in text
    assert "WorkBuddy 与跨平台启动" in text
    assert "https://www.lululab.ai/" in text
