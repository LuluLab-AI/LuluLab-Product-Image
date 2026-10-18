# LuluLab 图片运行时

Codex 与 WorkBuddy 使用同一随包 `scripts/lululab_cli.mjs`。运行 `scripts/workbuddy_preflight.py` 检查 Node.js 20+、Pillow 和 CLI 文件；运行 `scripts/check_lululab_api_key.py check` 做非生成式远端鉴权。不得按宿主切换到原生生图或其他平台。

先用 `scripts/lululab_product_analyze.py` 上传商品原图，调用 `ChatGenV2` 的 `images` 字段识别可见事实；识别结果进入首次确认和 `productBrief`。再用 `scripts/lululab_blueprint_generate.py` 提交 `ChatGenV2` 生成 Blueprint 和逐张视觉 Prompt。每张 Card 独立调用 `scripts/lululab_image_generate.py`，上传产品原图，用户提供达人图时追加达人图。该脚本通过 LuluLab `ImageGenV2`、`gpt-image-2-5-sunburst`、`1K`、`9:16` 生成一张无文字底图，并保存任务 ID。已有 ID 仅查询恢复；未知提交状态不得重提。图片与文字后期合成仍使用本地 `render_text_overlay.py`。

生成后实际读取像素尺寸并逐张检查主体和产品身份。原生分辨率不足时如实说明；不得把插值放大当作原生高分辨率。
