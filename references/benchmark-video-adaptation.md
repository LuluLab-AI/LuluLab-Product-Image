# 对标视频改编

## 服务门禁与单次提交

复用兄弟 Skill `LuluLab-Recreate-Video` 的 `scripts/server_video_analysis.py`，只调用 `RecreateVideoPromptV3`。运行前完整读取该 Skill 的 `references/server_video_analysis.md`。先完成本 Skill 的 LuluLab Key 预检，再通过已安装的最新版 `LuluLab-Recreate-Video` 提交 `RecreateVideoPromptV3`；该兄弟 Skill 使用随包 Node.js LuluLab CLI，视频上传和任务恢复遵循其现行文档。缺少 Key 时停止并提示用户配置，不能上传视频。

保留同一 manifest 的排他锁、preparing_submission、taskId 原子 receipt 与 `--resume-task-id`。状态未知或没有 taskId 时停止核查，禁止猜测未提交并再次上传或提交。错误信息脱敏。

`scripts/benchmark_video_analysis.py` 是轻量转发器，不复制视频生成 manifest。它把参数交给现有、经过验证的服务端拆解脚本。

## 读取重点

从 `videoBlueprint` 提炼：爆款逻辑的阶段拆解、爆款资产、逐镜头的画面/构图/角度/动作/产品状态/营销目的/停留原因/keyframes、替换产品时需保留的展示逻辑、视觉风格 DNA。

运行 `scripts/build_reference_ad_logic.py` 生成 `hook`、`stageSequence`、`proofMechanism`、`ctaMechanism`、`visualPatterns`、`strongestAssets`、`reusablePatterns`、`nonTransferableFacts`。最后一项必须覆盖原品牌、产品参数、价格、功效、促销、人物身份和具体承诺，只用于排除。

## Temporal → Spatial

视频以时间升级信息，Carousel 以滑动升级信息。把冲突、问题强化、产品亮相、操作、结果和购买引导重新创作成静态卡片；不是平均抽帧，也不是直接使用视频帧。每张目标卡最多绑定一个关键帧时间，且只参考构图、主体位置、冲突、角度和场景。

用 `scripts/extract_reference_frames.py` 抽取参考帧。参考帧不得作为最终广告图；最终视觉必须围绕用户产品重新生成。
