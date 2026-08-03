# 变更日志
本项目所有重要变更都记录在此，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

- **Added** 本地路径支持：视频/图片/文本文件直用，无需下载器
- **Added** 文本类型分支（📄）：本地 .txt/.md/.markdown → 直接整理成 AI 教材
- **Added** yt-dlp 来源路由：YouTube/B站等链接自动走 yt-dlp（需安装 yt-dlp，可用 `DD_YTDLP` 覆盖）
- **Fixed** 路径安全：目录/文件名过滤 Windows 非法字符与 `..`；aweme_id 校验为纯数字
- **Fixed** `.env` 现在真正生效（python-dotenv 加载，media_to_notes.py 与 glm_vision.py）
- **Fixed** 依赖补齐：新增 soundfile / paddlepaddle / python-dotenv；文档化 yt-dlp
- **Fixed** 健壮性：临时帧目录所有退出路径兜底清理（atexit）、ffprobe/ffmpeg 超时、VideoCapture 异常释放
- **Fixed** 未先 `--detect` 直接 `--glm` 给出友好提示；下载器缺失给出可操作提示
- **Changed** 文档与代码对齐：多源支持如实描述；ocr_corrections.json 说明为参考词典（非自动化套用）
- **Changed** CLAUDE.template.md 许可证标注 MIT → 双重许可（AGPL-3.0 / 商业授权）
- **Verified** 终审验收：六维验证全部通过 — 代码健壮性、安全与隐私、多源分发正确性、依赖与配置闭环、文档一致性、许可与免责；三方终审均分 96.3/100（≥95 阈值）

## [0.1.0] — 2026-08-03

初始开源发布。

- **Added** 核心两阶段流程：`--detect` 下载+类型检测+归位，`--glm yes|no` 分析处理
- **Added** 多来源下载：抖音(jiji262 去水印)、YouTube/B站(yt-dlp)、本地路径直用
- **Added** 内容类型自动分支：🎬视频→FunASR转写+多帧OCR(+可选GLM关键帧)；🖼️图集→逐张OCR(+可选GLM)；📄文本→直接整理
- **Added** SenseVoice 逐段转写（fsmn-vad 分割 + 逐段转写 + 标点恢复）
- **Added** 视频多帧 OCR：默认每 1 秒 1 帧（上限 1200 帧）；GLM 视觉仅分析画面差异自动选出的关键帧以节省费用
- **Added** AI 教材生成规范（spec/note_style_spec.md）：8 字段 frontmatter + 知识点六段式 + 费曼思考题(核心10/重要8/一般6道) + 专业词汇表 + 完整转写附录
- **Added** frontmatter 标签与 type 按来源网站自适应（抖音/B站/YouTube/文本整理）
- **Added** OCR / ASR 纠错词典示例（config/*.example.json）
- **Added** 可移植配置：全部路径环境变量可覆盖（DD_BASE/DD_DL_PY/DD_DL_SRC/DD_ASR_PY/DD_OCR_PY/GLM_API_KEY），无任何硬编码绝对路径
- **Fixed** 视频视觉分析临时帧目录清理（shutil 导入修复）
- **Changed** 许可证由 MIT 改为双重许可：AGPL-3.0（开源）+ 商业授权（见 COMMERCIAL.md）

[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
