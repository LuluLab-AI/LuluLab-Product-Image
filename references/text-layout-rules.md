# 本地文字排版

支持 `top-title`、`left-title`、`bottom-card`。默认输出按原图尺寸；9:16 推荐 720×1280 或更高等比例尺寸。

- 自动换行、动态缩小字号；无法容纳时失败，不静默截断。
- 用描边、阴影或半透明底板保证对比度。不得遮挡人物脸、产品主体和关键操作。
- 底部保留约 15% 的 TikTok UI 安全区；左右保留约 5% 边距。
- 中文优先 PingFang SC / Microsoft YaHei，拉丁文字优先 Arial；缺失时使用 Noto/DejaVu 等系统字体。Skill 不打包商业字体。
- 文字只能读取 Blueprint/已确认输入，渲染脚本不得改写文案。

```text
python3 scripts/render_text_overlay.py --image visual.png --output card_01.png --headline "Still doing this the hard way?" --subheadline "A simpler everyday setup" --badge "NEW" --layout top-title
```
