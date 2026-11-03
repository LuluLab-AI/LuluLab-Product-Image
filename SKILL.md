---
name: LuluLab-Product-Image
description: 'Create TikTok and Douyin product carousels and single-image ads from product photos, with strategy, visuals, text layout, and publishing copy. / 根据产品图制作 TikTok 和抖音带货图文及单图广告，包含策划、视觉、排版和发布文案。'
metadata:
  slug: LuluLab-Product-Image
  version: "3.1.1"
  display_name: LuluLab-Product-Image
  summary: Create TikTok and Douyin product carousels or single-image ads from product photos, including strategy, visuals, text layout, and publishing copy. / 根据产品图生成 TikTok 和抖音带货图文或单图广告，包含策划、视觉、排版和发布文案。
  workbuddy_compatible: true
  workbuddy_description_en: Create TikTok and Douyin product carousels or single-image ads from product photos, including strategy, visuals, text layout, and publishing copy.
  workbuddy_description_zh: 根据产品图生成 TikTok Carousel、抖音图文或单图带货广告，包含策略、视觉、排版和发布文案。
---

# LuluLab 带货图文

所有新任务复用前端带货图文的工作流与提交协议：`ProductImagePromptV1 → ImageGenV2`，通过 Customer API 创建 Dispatcher 任务。客户端先创建一份策划，再按返回的 cards 顺序逐张提交图片，携带 parentTaskId、cardIndex 和 creationSource。当前服务端没有整套图文父任务；后续图片提交仍需运行 `advance`，并非关闭客户端后整套自动执行。

商品图 1～8 张，达人参考图可选 1 张。默认 6 张、9:16、1K、GPT Image 2.5 Sunburst。张数 1～10，1 张为单图；可选 Sunburst/Flare，1K/2K/4K，9:16、3:4、4:5、1:1、16:9。一次请求对应一套；多套使用不同 state 和独立创作需求，不能复制同一份策划凑数。

与前端一致，未提供达人时 creatorMode=none；提供一张达人参考图时为 provided。用户明确要求 AI 达人时，先说明可将人物要求写入 creativeRequirement；不要默认为本地额外生达人图。不得丢弃用户对人物的要求。

请求示例（替换为实际上传结果）：

```json
{
  "kind": "image",
  "productName": "",
  "sellingPoints": [],
  "targetAudience": "",
  "productImages": [{"url":"https://asset.example/product.png","mimeType":"image/png"}],
  "creatorImages": [],
  "targetCountry": "United States",
  "targetLanguage": "en-US",
  "creativeRequirement": "",
  "model": "gpt-image-2-5-sunburst",
  "count": 6,
  "aspectRatio": "9:16",
  "resolution": "1K"
}
```

策划输出 `imagePrompts.cards[]` 包含 title、prompt、textOverlay，张数必须一致。直接使用原始 card.prompt 生图，与前端相同；不再默认走本地 ChatGenV2 Blueprint、无字底图加文字覆盖链路。保留策划输出供审阅，最终按顺序展示全部成功图片、实际像素尺寸、失败卡片及原因。图片是独立原图，不生成网格再裁切，不以普通插值声称原生高清。

首图优先停留 Hook，中间增加信息与证明，末图自然转化；可以在 creativeRequirement 传入用户明确的创意要求，不在本地替换工作流生成的 prompt。不要伪造评价、销量、价格或功效。

前端当前仅支持原创图文。用户要求对标视频或对标图文改编时，说明共享工作流暂不支持；经用户同意，可将其明确的创意要求写入 creativeRequirement 后按原创提交。不得悄悄改为原创，也不得自动退回 ChatGenV2、本地 Blueprint、网格裁切或文字覆盖的独立生成链路。旧脚本只用于恢复已有历史任务。

接口字段、配置快照和前端源码对应关系见 [references/FRONTEND_WORKFLOW.md](references/FRONTEND_WORKFLOW.md)；修改适配器时按该契约核对。

## 多语言交互与成品语言

- 三个概念独立处理：交互语言、目标市场、成品语言。交互语言依次采用用户明确指定的回复语言、宿主可用的语言设置、当前会话主要语言；无法判断时沿用上一轮，首次无上下文时使用用户本次消息的语言。支持按用户选择使用中文、英语、日语、韩语、西班牙语、葡萄牙语、法语、德语、越南语等语言，不限于中英文；不因本文或示例为中文就固定中文回复。
- 所有用户可见说明使用交互语言：素材收集、配置表的字段和选项、默认值说明、预计积分及计费明细、确认问题、进度、错误、恢复和交付说明。翻译服务端状态与计费项目的人类可读标签，保留原始积分数值、模型 ID、工作流 ID、命令、任务 ID、路径和 JSON 字段名。CLI 的原始英文输出由智能体用交互语言解释，不直接作为最终回复。
- 配置表单独列出成品语言；用户指定优先，否则沿用本 skill 的目标市场与默认规则，并作为待确认值展示。不得从交互语言推断市场或自动覆盖成品语言。图片内文字、发布文案、视频口播及字幕（仅实际支持的步骤）遵循目标语言；方言、地区用语和多语言混用要求完整保留。模型或工作流不支持时，在提交前说明限制并让用户选择，不静默改成中文或英语，也不承诺未经验证的语言效果。
- 确认文案均为可翻译示例。按交互语言表达“预计消耗 {credits} 积分；回复 1 开始制作，回复 2 修改配置”，接受数字或任意语言中明确等效的确认；拒绝、提问和修改配置不算确认。仅切换交流语言不改变生成配置或新增确认；修改成品语言属于配置变更，须更新请求、重新预估并确认。
- 服务端返回的生成 prompt 原文保留并原样提交；需要便于用户理解时，另附交互语言的摘要或译文并标为说明，不能用译文替换原 prompt。用户创作要求保留原文，不因翻译遗漏事实或修改语言选择。本节也适用于历史任务和旧参考文档；旧文档的“中文／非中文统一英文”展示规则不得覆盖本节。

图文请求通过 `targetLanguage` 传入目标文字语言（如 `ja-JP`、`es-ES`、`vi-VN`），策划输入使用 `userConfig.targetLanguage`。

## 调度器执行

需要 Node.js ≥20。从当前 SKILL.md 所在目录解析脚本，支持 Windows/macOS/Linux，无需 npm。凭证继续使用本 skill 已有的环境变量与私有配置；不在命令参数、提示词或日志中放 Key。默认 Customer API 为 `https://customer.lululab.ai`，可用 `LULULAB_API_BASE_URL` 指定开发环境。

收到产品图后识别可见商品事实；缺图时请求产品图。价格、优惠、功效、认证等只使用用户提供或素材有依据的信息。目标市场默认美国（请求值 United States）、发布语言默认 en-US；尊重用户设置。商品名称、卖点和受众均可留空，由共享工作流结合商品图策划，不为补齐字段编造事实。人物要求和附加创意完整保留在 creativeRequirement；素材提及须先替换为实际 URL，不把前端临时的 @ 标记直接提交。默认值只用于准备待确认配置。

### 提交前配置确认（必需）

每轮新任务先展示完整配置表：产品名称、可见卖点、产品图与达人图的用途、目标市场、目标受众、原创或对标改编模式、自定义创作需求、图中文字语言、模型、套数、每套张数、画幅与分辨率。标明用户指定值、默认值和建议值。表格外说明本轮计费范围：新任务为 1 次 ProductImagePromptV1 策划与对应数量的 ImageGenV2 图片生成；恢复旧任务时按实际剩余流程列出计费步骤。费用须按下述积分预估规则展示。

配置表后必须用交互语言展示**预计消耗：{credits} 积分**（翻译标签，保留真实数值），再让用户确认开始。先对同一份 request.json 运行 `estimate --config request.json`，读取 `/billing/estimates` 返回的 `credits`、`breakdown` 和 `version`；展示总额及服务端提供的计费明细，不写死单价、不用余额差推算，也不把预估说成最终扣费。多套请求须分别估算并汇总，列明套数、每套数量和本轮总积分。

预估查询不创建生成任务，可在确认前上传素材、校验配置并查询。预估失败、缺少有效积分总额或计费范围不完整时，说明原因并暂停提交，不把未知写成 0 或仅提示“可能收费”后继续。用户修改配置时重新估算并展示；用户须明确确认最终配置与预计积分后，才能传入 `--generation-approved`。同一配置与已展示计费范围的后续正常阶段沿用确认，不增加重复确认。提交时仍按服务端实时报价结算；若报价规则变化导致预计总额上涨，先展示更新预估并重新确认。旧入口的新计费提交也须先提供实际范围的预估，无法可靠估算时暂停。

确认文案示例（须翻译为交互语言，占位符必须替换为真实返回值）：“以上是本次制作配置。预计消耗 {credits} 积分，包含{计费步骤与数量}；实际按提交时服务端报价结算。请选择：**1 开始制作**（按以上配置和预计积分提交），或 **2 修改配置**。直接回复数字即可，也可以说明想修改的内容。”

展示后必须给出上述两个选项，并等待用户回复。用户看过当前完整配置与预计积分后，回复“1”或“1 开始制作”即视为确认，可直接提交；明确等效的确认（如“确认开始”）也有效。回复“2”或提出修改时，先更新配置、重新预估，再展示新的完整配置与选项。用户在展示配置之前提出的“开始制作”“使用这个 skill”、上传素材、沉默或智能体自行宣布默认设置均不算配置确认；即使初始请求已列明参数，也要先展示最终配置并取得确认。已确认同一配置后，后续阶段沿用确认，不重复询问。新增计费范围或付费重试时，须展示更新配置并重新确认。已有任务的只读查询与下载无需重新确认；提交结果未知时保留原任务与 state，不得重提。

确认前可识别与整理素材、准备本地请求、离线 `plan` 校验及非生成式积分预估，不得创建策划、图片或视频任务。此确认规则同样适用于旧工作流；不能通过旧入口绕过。

所有新任务使用 `scripts/dispatcher_commerce.mjs`：

```bash
node <技能根目录>/scripts/dispatcher_commerce.mjs upload --file <产品图路径> --output asset_01.json
node <技能根目录>/scripts/dispatcher_commerce.mjs plan --config request.json
node <技能根目录>/scripts/dispatcher_commerce.mjs estimate --config request.json
node <技能根目录>/scripts/dispatcher_commerce.mjs submit --config request.json --state state.json --generation-approved
node <技能根目录>/scripts/dispatcher_commerce.mjs poll --state state.json
node <技能根目录>/scripts/dispatcher_commerce.mjs advance --state state.json --generation-approved
node <技能根目录>/scripts/dispatcher_commerce.mjs download --state state.json --output <交付目录>
```

上传所有产品图和用户提供的达人图，把上传返回的 `{url,mimeType,expiredAt?}` 对象写入请求。`plan` 离线校验和展示实际请求，不读取 Key 或创建任务。`estimate` 按前端相同的 `/billing/estimates` 请求查询策划及整套图片预估积分，不创建生成任务，可在配置确认前使用。`submit` 只创建策划任务；保存 state 后按需 `poll`，策划成功后 `advance` 逐个提交生成任务。等待生成期间继续 `poll`；它只查询，不会提交。每次 `advance` 只提交缺失的任务，已有 ID（含失败任务）不会重提。策划成功后主动执行 `advance`，无需用户逐张发起；后续循环查询直至全部任务结束或出现阻塞，不能只交付策划就停止。完成后下载成功结果，保留部分成功与所有失败信息。

每次任务创建都先调用 `/billing/quotes`，再携带 quoteId 调用 `/tasks`，与前端 SDK 一致。图片保存 `saveGeneratedAssets=true`、`creationSource=shoppable-images`、策划父任务 ID 和从 0 开始的 cardIndex。策划与图片任务均提交顶层 editorSnapshot，配置快照不混入工作流 input；使用同一账户可关联任务、资产及历史配置。

不要自动付费重试、切换 provider、重做整批或在本地改写服务端返回的提示词。state 在 POST 之前落盘，并用文件锁避免并发重复提交。提交结果未知时停止，核对同账户任务历史及精确 input 后人工恢复，不能删除 state 后重提。中断后继续使用原 state；遗留锁须先确认原进程已停止。API Key 无效、积分不足或网络故障分别报告，不回显服务端原始错误中的私人数据。

`--generation-approved` 仅表示用户已明确确认本轮展示的完整配置与计费范围；不能根据泛化的生成请求自行设置此标志。修改配置后需新 state，并重新确认。适配器本身不部署服务端或修改工作流。

历史任务：仅恢复旧任务时读取 [references/LEGACY_WORKFLOW.md](references/LEGACY_WORKFLOW.md)，沿用原任务 ID 与旧脚本，不挂接到新的调度器任务。
