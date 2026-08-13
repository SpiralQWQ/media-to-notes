# 变更日志
本项目所有重要变更都记录在此，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.2] — 2026-08-13

- **Fixed** 隐私：`优化方向/README.md` 剔除残留的内部环境引用
- **Fixed** GBK 控制台兼容：6 个子脚本补齐 stdout/stderr 编码转换，中文 Windows 控制台打印中文/emoji 不乱码、不报错（与主脚本一致）
- **Added** `--glm all`（视频）：`GLM_MODE=all` 现在真正对**每一帧**做 GLM 分析（与原文档一致）——此前会静默退回关键帧分析
- **Added** 开源社区规范文件：`CONTRIBUTING.md` / `SECURITY.md` / `CODE_OF_CONDUCT.md` / `.gitattributes` / `.github/`（Issue 与 PR 模板、`FUNDING.yml`），以及每次 push/PR 自动语法检查的 GitHub Actions CI
- **Fixed** `--glm no` 现在会覆盖 `.env` 的 `GLM_MODE`：文档承诺的「免费模式开关」真正生效
- **Fixed** `notes_pipeline.py`：用法与文档与实际行为一致——视频参数为兼容保留、不再使用（新 2 参为主，旧 3 参仍兼容）
- **Docs** 开源规范打磨：README(中英) 文件树补全；CHANGELOG 版本链接引用补全；FAQ 与 `GLM_MODE` 描述与真实行为对齐；`README_zh.md` 版本号修正为 0.2.1

## [0.2.1] — 2026-08-09

- **Fixed** 视频 OCR 线程占用：`RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)` 官方限线程——实测比默认 95 线程**更快 33%** 且 CPU 占用降 96%（环境变量对 onnxruntime 无效，必须官方 config 参数）
- **Fixed** 隐私：`优化方向/README.md` 不再引用本地绝对路径——改为官方 MinerU 文档链接

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

[0.2.2]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.2
[0.2.1]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.1
[0.2.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.0
[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
