from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contract_files_exist():
    required = [
        "SKILL.md", "agents/openai.yaml", "scripts/local_prompt.py",
        "scripts/check_lingzhi_api_key.py",
        "scripts/validate_image_blueprint.py", "scripts/render_text_overlay.py",
        "scripts/build_carousel_preview.py", "scripts/build_reference_ad_logic.py",
        "scripts/extract_reference_frames.py", "scripts/split_grid.py",
    ]
    assert all((ROOT / item).is_file() for item in required)


def test_skill_excludes_video_generation():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "name: product-image-ad" in text
    assert 'version: "2.3.0"' in text
    assert "不生成：" in text and "- 视频" in text
    assert "render_text_overlay.py" in text
    assert "creatorMode=none" in text
    assert "imageAdBlueprint v2.0" in text
    assert "默认生成 9 张" in text
    assert "不得生成九宫格、六宫格或其他拼图后裁剪" in text
    assert "benchmarkCarousel" in text
    assert "python3 scripts/check_lingzhi_api_key.py check" in text
    assert "请获取灵智工坊API Key：https://www.lingzhiai.com.cn/" in text
