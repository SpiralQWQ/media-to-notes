# 变更日志
本项目所有重要变更都记录在此，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.1] — 2026-08-09

- **Fixed** 视频 OCR 线程占用：`RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)` 官方限线程——实测比默认 95 线程**更快 33%** 且 CPU 占用降 96%（环境变量对 onnxruntime 无效，必须官方 config 参数）

## [0.2.0] — 2026-08-08

- **Added** 开箱即用配置向导 `setup.py`：拉取后跑 `python setup.py`，回答 9 个问题（使用场景/OCR频率/GLM视觉/笔记语言/转写附录/费曼题密度/中间产物/笔记组织）即自动生成 `.env` + `spec/user_prefs.md`，无需提前看文档
- **Added** 用户偏好档 `spec/user_prefs.md`：Claude 生成笔记时遵循（语言/费曼题密度/是否保留附录/目录组织），SKILL.md 与 CLAUDE.template.md 已声明"生成笔记前必读"
- **Added** 视频 OCR 频率可配置：`OCR_INTERVAL`（秒数或 `scene`/`no`），替代硬编码每秒 1 帧
- **Added** GLM 模式可配置：`GLM_MODE`（`yes`/`all`/`no`）
- **Added** 笔记偏好环境变量：`NOTE_LANG` / `KEEP_APPENDIX` / `FEYNMAN_DENSITY` / `KEEP_MIDDLE` / `NOTE_ORGANIZE`
- **Changed** README(中英) 安装步骤：新增「开箱即用配置向导」步骤，环境变量表补全新配置项
- **Fixed** `--interval 1` 硬编码改为读 `.env` 的 `OCR_INTERVAL`

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
- **Added** 可移植配置：全部路径环境变量可覆盖（DD_BASE/DD_DL_PY/DD_DL_SRC/DD_ASR_PY/DD_OCR_PY/DD_YTDLP/GLM_API_KEY），无任何硬编码绝对路径
- **Fixed** 视频视觉分析临时帧目录清理（shutil 导入修复）
- **Changed** 许可证由 MIT 改为双重许可：AGPL-3.0（开源）+ 商业授权（见 COMMERCIAL.md）

[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
