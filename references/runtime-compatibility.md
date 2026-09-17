# Codex / WorkBuddy 生图运行时兼容

共享业务流程、Blueprint、产品事实约束、逐张生图、排版和发布脚本。只在生图调用层按宿主路由，并始终以实际输出文件尺寸为准。

## 通用规则

1. 新任务只使用 `individual`，默认 9 张，用户可修改为 1～10 张。
2. 每张 Card 都独立调用生图能力，并实际传入产品原图；不得生成九宫格、六宫格或其他拼图再裁剪。
3. 目标画幅为 9:16，推荐 1080×1920 或更高的同画幅尺寸。工具不支持精确尺寸时，选最接近的高分辨率档。
4. 生成后逐张读取真实像素尺寸。Prompt 中写了目标尺寸不等于工具已经执行。
5. 不得把后期普通插值放大当作原始高分辨率；清晰度不足时只重做对应 Card。

## Codex

- 默认使用宿主原生 `image_gen`，每张 Card 单独提交。
- 尺寸若只能写在 Prompt 中而不是结构化参数，生成后必须验证实际尺寸和画幅。
- 最多并发 3 张；同一 Card 不得重复提交。失败时只重试失败 Card 一次。
- 只有用户明确选择 CLI/API 路径时，才使用需要 API Key 的外部生图脚本。

## WorkBuddy

1. 先用 WorkBuddy `ToolSearch` 精确加载 `ImageGen` 的当前 schema，了解当前选中文生图模型支持的参数。可用 `/model:text-to-image list` 查看宿主可用模型，但不自动更换用户模型。
2. 每张 Card 独立调用 WorkBuddy `ImageGen`，同时传入产品参考图；用户提供达人图时再附加达人参考图。
3. 如果内置工具提供结构化高分辨率参数，优先选择满足 9:16 的 2K 或更高档，并在输出后验证实际像素。
4. 若用户明确选择 `nano-banana-pro` Skill，可按其当前 schema 使用 `--resolution 1K|2K|4K`。4K 路径需要本机 `GEMINI_API_KEY`，且属于单独计费调用；执行前遵守 WorkBuddy 的授权与计费提示规则。
5. 即使请求了 2K/4K，也要逐张检查实际长边、画布比例和主体完整性；不达标时只重做失败 Card。

WorkBuddy 独立图片调用示例：

```text
uv run <nano-banana-pro>/scripts/generate_image.py \
  --prompt "<single-card prompt; portrait 9:16; no collage or grid>" \
  --filename "<output>/visual_01.png" \
  --input-image "<product reference>" \
  --resolution 2K
```

路径必须从当前 WorkBuddy 实际安装的 Skill 目录解析，不得硬编。

## 产物兼容

- Codex 与 WorkBuddy 都输出独立的 `visual_01.png`…`visual_N.png`，再渲染为 `card_01.png`…`card_N.png`。
- Blueprint、文字排版、预览和发布包结构保持一致。
- 新任务不产生 `grid_visual.png` 或 `crop_manifest.json`。
- `split_grid.py` 只用于恢复用户提供的历史网格素材。
- 不将 Codex 或 WorkBuddy 专有工具名写入 Blueprint；宿主路由只记录在执行日志或 `publish_package.creativeReview`。
