# LuluLab Product Image

根据商品图制作 TikTok / 抖音带货图文或单图广告，与前端共用 `ProductImagePromptV1 → ImageGenV2`，通过 Customer API 报价、提交和查询 Dispatcher 任务。

默认每套 6 张、9:16、1K、GPT Image 2.5 Sunburst；支持 1～10 张，1～8 张商品图及可选 1 张达人参考图。商品名称、卖点与受众可留空，创意要求交给共享策划工作流。每张图片使用策划返回的 prompt 独立生成。

需要 Node.js 20+，无需 npm 或 Python。配置 `LULULAB_API_KEY`（兼容已有凭证配置），不得把 Key 放入命令参数或日志。具体命令、提交前配置确认与恢复规则见 [SKILL.md](SKILL.md)，接口契约见 [FRONTEND_WORKFLOW.md](references/FRONTEND_WORKFLOW.md)。

`plan` 离线校验；`estimate` 查询整套预估积分；配置确认后 `submit` 创建策划，`poll` 只读查询，策划成功后 `advance` 按序创建图片任务，完成后 `download` 下载。每次创建任务前均先取得 quoteId。中断后沿用原 state，不自动付费重试。

当前共享流程只支持原创图文；旧 Python / ChatGenV2 / Blueprint 工具仅用于恢复历史任务，见 [LEGACY_WORKFLOW.md](references/LEGACY_WORKFLOW.md)。

Create TikTok and Douyin product carousels through the same Customer/Dispatcher workflow as the frontend: `ProductImagePromptV1 → ImageGenV2`. Defaults: 6 cards, 9:16, 1K, GPT Image 2.5 Sunburst. Node.js 20+ only for new tasks. See [SKILL.md](SKILL.md) for configuration approval, estimates, submission, recovery, and delivery.

Supports multilingual interaction for configuration, estimated credits, confirmation, progress, errors and delivery. Reply language follows the user’s choice; output text/speech language is configured separately. See [SKILL.md](SKILL.md).
