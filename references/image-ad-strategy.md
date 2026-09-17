# 输入与 imageAdBlueprint

新任务生成 `imageAdBlueprint v2.0`，默认 9 张，用户可修改为 1～10 张。故事字段与默认行为见 [ugc-story-grid.md](ugc-story-grid.md)。`generationMode` 固定为 `individual`；每张独立生成完整 9:16 原图，不得先生成网格再裁剪。

## 规范化输入

```json
{
  "productBrief": {"productName": "", "productType": "", "sellingPoints": [], "targetCountry": "美国", "targetAudience": "", "price": "", "promotion": "", "productImages": [{"path": ""}]},
  "userConfig": {"creativeMode": "original", "adFormat": "carousel", "cardsPerSet": 9, "setCount": 1, "aspectRatio": "9:16", "visualStyle": "auto", "targetLanguage": "en-US", "creatorMode": "auto", "generationMode": "individual"},
  "benchmarkVideo": {"path": ""},
  "creatorBrief": {"creatorMode": "auto", "creatorImages": []},
  "creativeRequirement": ""
}
```

支持 `creativeMode=original|benchmarkVideo`、`adFormat=carousel|single`、`visualStyle=auto|ugc|productScene|poster`、`creatorMode=auto|referCreator|none`。单图广告强制一张；Carousel 为 2～10 张。

## Blueprint

```json
{
  "schemaVersion": "1.0",
  "strategy": {"sourceType": "original", "bigIdea": "", "coreSellingPoint": "", "targetAudience": "", "hookMechanism": "", "conversionPath": "", "visualDNA": "", "creatorStrategy": ""},
  "cards": [{
    "cardId": "c1", "order": 1, "function": "hook", "headline": "", "subheadline": "", "badge": "",
    "visualGoal": "", "scene": "", "creator": "", "creatorAction": "", "productRole": "", "productState": "",
    "composition": "", "camera": "", "lighting": "", "background": "", "proofElement": "",
    "reference": {"stageIds": [], "shotIds": [], "assetIds": [], "referenceFrameTime": null},
    "imagePrompt": "", "negativePrompt": ""
  }],
  "publishCopy": {
    "language": "en-US",
    "caption": "",
    "cta": "",
    "hashtags": [],
    "musicMood": "",
    "chineseTranslation": {"caption": "", "cta": ""}
  }
}
```

每张承担不同的传播功能并增加新信息。功能标签不是固定模板。第一张需有明确停留理由，最后一张需有转化目的，但不强制统一的中间顺序。

原创模式先明确核心卖点、受众、Big Idea、Hook、Proof 和 CTA，再组织卡片。自动混合可交替使用真人 Hook、问题场景、产品特写、操作、Proof 与产品海报。

`imagePrompt` 只描述纯视觉：人物、产品、动作、场景、光线、构图、文字留白。必须要求不生成广告文字、字幕或水印。广告文案只能来自 Blueprint 的文字字段。

## publishCopy v1.2

- `language` 必须等于 `userConfig.targetLanguage`；如用户未单独指定，则使用目标市场的主流语言。美国默认 `en-US`。
- `caption` 是可直接发布的 TikTok 文案，用本地化口语完成停留钩子、卖点或场景回报和自然 CTA，不写空泛广告腔。
- `hashtags` 保持相关且适量，不虚构趋势、销量或用户反馈。
- `chineseTranslation.caption` 和 `chineseTranslation.cta` 必须完整传达对应原文，供用户理解与审阅；不将该译文混入实际发布 caption。
