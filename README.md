# LuluLab Product Image

Create TikTok and Douyin product carousels or single-image ads from product photos. The skill plans the selling angle and slide sequence, generates visuals, renders accurate text overlays, and prepares publishing copy. It supports original ads and adaptations of reference videos or carousels.

The bundled Node.js LuluLab CLI handles product analysis and carousel planning through `ChatGenV2`, and image generation through `ImageGenV2`. The skill does not generate video. Read [SKILL.md](SKILL.md) for the full workflow and product-identity rules.

## Requirements

- Python 3, Pillow, and Node.js 20 or newer
- A valid LuluLab API key (`LULULAB_API_KEY`; legacy `LINGZHI_API_KEY` and `LZSTUDIO_API_KEY` are also accepted)

Run `python3 scripts/workbuddy_preflight.py` to check the local environment. Run `python3 scripts/check_lululab_api_key.py check` before using the skill. On Windows, use `py -3` in place of `python3` if available. Do not put an API key in command arguments or commit it to this repository.

## 中文说明

根据产品图片制作 TikTok Carousel、抖音图文或单图带货广告。Skill 会策划卖点与逐页叙事、生成视觉图片、准确排版广告文字，并输出发布文案；支持原创以及参考视频或图文的改编。

随包的 Node.js LuluLab CLI 使用 `ChatGenV2` 完成商品分析和图文策划，使用 `ImageGenV2` 生成图片。使用前需安装 Python 3、Pillow、Node.js 20+，并配置有效的 LuluLab API Key。完整流程及产品真实性规则见 [SKILL.md](SKILL.md)。
