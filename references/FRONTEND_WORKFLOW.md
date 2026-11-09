# 前端带货图文提交契约

核对日期：2026-11-03。此 skill 作为前端之外的 Customer API 客户端，调用同一套服务端工作流，不另写本地策划或生图流水线。以下源码路径相对于 LuluLab 工作区；运行 skill 不依赖前端仓库。

| 前端源码 | 负责的契约 |
| --- | --- |
| `lululab-ui/workshop/src/views/ShoppableImagesView.vue` | 默认 6 张、美国/en-US、9:16、1K；最多 8 张商品图和 1 张达人图；策划成功后自动按序提交图片 |
| `lululab-ui/workshop/src/domain/productImagePrompt.ts` | ProductImagePromptV1 input、creatorMode、cards 数量校验与输出解析 |
| `lululab-ui/workshop/src/domain/imageTask.ts` | ImageGenV2 input、来源属性、父任务关系与配置快照 |
| `lululab-ui/workshop/src/config/workflows.ts` | Sunburst/Flare、1K/2K/4K 与可用画幅 |
| `lululab-ui/packages/lululab-client/src/client.ts` | `/billing/estimates`、`/billing/quotes` → `/tasks`、`/tasks/{id}` |

## 策划请求

`workflowId=ProductImagePromptV1`。`input` 由以下对象组成：

- `productBrief`：productName、sellingPoints 字符串数组、targetCountry、targetAudience、productImages。
- `creativeRequirement`：用户创意要求，去除首尾空白。页面创意输入在此字段传递，不由客户端改写成另一套提示词。
- `userConfig`：creativeMode=original、cardsPerSet、aspectRatio、targetLanguage、storyStyle=imageStyle=storyDrivenCarousel。
- `creatorBrief`：无达人图时 creatorMode=none、creatorImages=[]；提供图时为 provided 和该参考图。

商品名称优先使用独立 productName；否则从卖点中的“产品名：”或“Product name:”行提取。卖点按行去空白并移除产品名称行。商品名称、卖点与受众可留空。美国市场的前端请求值为 `United States`。

所有参考图使用 `{url,mimeType,expiredAt?}`；兼容资产的 location 与 expiresAt，提交时统一为 url、expiredAt。不能提交过期素材。

顶层 `editorSnapshot` 保存 productName、creativeNotes、market、targetLanguage、cardsPerSet、aspectRatio、model、resolution、productImages、可选 personImage；只作为历史配置，不合并进 input。skill 的卖点、受众等补充字段也保存于快照，避免恢复时丢失。

## 图片请求与计费

策划输出支持 JSON 字符串或对象、直接 payload 或 `{output: payload}`。遇到 success=false、空 prompt 或 cards 数量不符时停止，禁止补写缺失 prompt 或付费补齐。

按 `imagePrompts.cards` 数组顺序，对每张提交 `workflowId=ImageGenV2`；input 为 model、原始 prompt（仅去除首尾空白）、aspectRatio、resolution、referenceImages（商品图在前、达人图在后）。title 与 textOverlay 作为策划结果保留，不额外拼进 prompt。每张对应独立原图。

顶层 attributes 为 saveGeneratedAssets=true、creationSource=shoppable-images、parentTaskId=策划任务 ID、cardIndex=0 起始索引。图片 editorSnapshot 保存这些来源设置与图片 input 对应的生成配置。

整套估算为 `/billing/estimates` 的 items：1 个 `{workflowId:'ProductImagePromptV1'}` 和 1 个 `{workflowId:'ImageGenV2',input:{model,resolution,imageCount}}`。策划前校验整套费用与可用积分。策划使用 `/billing/quotes` → `/tasks`；生成图片时每张取得报价，然后将全部请求及 quoteId 一次提交 `/tasks/batch`。服务端整批冻结，额度不足时全部不启动。

当前没有整套图文的服务端父编排任务。策划成功后的图片创建由前端或 skill 客户端驱动，关闭客户端不会自动提交剩余图片。skill 通过持久化 state 与 advance 恢复，同一已确认配置只补提交没有任务 ID 的图片；失败或提交结果未知的任务不得自动重提。
