# CLAUDE.md — media-to-notes 项目配置

> **安装**：复制本文件到仓库根目录并重命名为 `CLAUDE.md`；按 `SKILL.md` 顶部说明安装技能。本文件是模板，按需裁剪。
>
> 项目：media-to-notes · 双重许可（AGPL-3.0 / 商业授权）· Spiral QWQ · GitHub: https://github.com/SpiralQWQ/media-to-notes · Gitee 镜像: https://gitee.com/Spiral_QWQ/media-to-notes

## 基础规则

- 始终用**中文**回复，回答简洁结构化。
- 编辑前先读懂现有结构和代码风格，不做超出任务范围的抽象或重构。
- 英文术语保留，附中文简要说明。
- 项目是配置模板（配置类），可依实际工作流裁剪增删章节。

## 项目定位

任意内容 → AI 教材学习笔记。来源：抖音 / YouTube / B站 / 本地文件。
丢一个链接或本地路径，自动完成 下载 → 转写/OCR → 生成"喂给 AI 教学"的 AI 教材笔记，写入 `NoteBooks/`。

## 🚀 开箱即用（拉取后第一步）

**先跑配置向导，回答几个问题就能用，无需提前看文档：**

```powershell
python setup.py
```

向导问 9 个问题（使用场景 / 数据根目录 / OCR 频率 / GLM 视觉 / 笔记语言 / 转写附录 / 费曼题密度 / 中间产物 / 笔记组织），
自动生成 `.env`（脚本运行时读）和 `spec/user_prefs.md`（Claude 生成笔记时遵循）。

## 触发方式

用户丢一个链接或本地路径（视频/图集/文本）即自动进入"内容 → AI 教材笔记"全流程，无需明说。
用户明确说"只下载 / 不写笔记"时，只执行下载归位，不生成笔记。

## 两阶段流程（先检测询问，再处理）

阶段1 检测下载并询问，阶段2 处理分析，阶段3 由 Claude 生成笔记。GLM 花钱必须征得用户同意；OCR 默认全做（免费）。

### 阶段1：检测（下载 + 识别类型）

```powershell
python scripts/media_to_notes.py "<链接>" --detect
```

抖音用 jiji262 douyin-downloader（去水印，需 Cookie）；YouTube/B站用 yt-dlp；本地视频/图片/文本直接用路径。
执行链路：下载 → 判断 🎬视频 / 🖼️图集 / 📄文本 → 归位（`视频/` `音频/` `图片/` `文本/`）→ 写状态文件（`temp/current_job.json`）→ 报告类型。

### 阶段2：询问 GLM 后处理

**必须**先向用户确认："这条是视频/图集，要开启 GLM 视觉分析（glm-4.6v-flashx）吗？OCR 默认都做，GLM 会额外花钱。"
得到同意后运行：

```powershell
python scripts/media_to_notes.py --glm yes|no
```

### 阶段3：生成 AI 教材

**生成前必读 `spec/user_prefs.md`**（用户偏好：笔记语言/费曼题密度/是否保留附录/目录组织——由 setup.py 生成）。
Claude 读取 转写 JSON / OCR 文本 / GLM 描述 → 按 `spec/note_style_spec.md` + `spec/user_prefs.md` 生成 AI 教材笔记 → 写入 `NoteBooks/{日期}/{顺序}_{日期}_{概要}_{大小}.md`（若 .env 设 `NOTE_ORGANIZE=topic` 则按课程/主题分目录）。

## 内容类型分支表

| 类型 | 下载/来源 | 处理链路 | GLM=yes 时（花钱） |
|---|---|---|---|
| 🎬 视频 | 抖音 jiji262 / YT·B站 yt-dlp / 本地路径 | FunASR 逐段转写（fsmn-vad 切段 + SenseVoiceSmall）→ 多帧 OCR（默认 1 秒 1 帧、上限 1200 帧、免费） | 只分析关键帧（画面差异自动选帧，省钱）；`.env` 设 `GLM_MODE=all` 则每帧都分析（贵） |
| 🖼️ 图集 | 抖音 jiji262 / YT·B站 yt-dlp / 本地路径 | 逐张 OCR（PaddleOCR 优先 / RapidOCR 兜底） | 每张图 GLM 描述 |
| 📄 文本 | 本地路径 | 无下载，Claude 直接整理成 AI 教材 | 不适用 |

## 脚本索引

| 脚本 | 职责 |
|---|---|
| `scripts/media_to_notes.py` | 主流程（阶段1 检测下载 + 阶段2 处理） |
| `scripts/transcribe_funasr.py` | SenseVoice 逐段转写（fsmn-vad 切段） |
| `scripts/video_frames_ocr.py` | 视频多帧 OCR + 场景检测 + 关键帧 GLM |
| `scripts/ocr_images.py` | 图集逐张 OCR |
| `scripts/glm_vision.py` | 独立 GLM 视觉理解（glm-4.6v-flashx，需 `GLM_API_KEY`） |
| `scripts/notes_pipeline.py` | 转写 JSON → 原始转写 md |

## 笔记格式铁律（摘要，完整见 `spec/note_style_spec.md`）

**frontmatter 8 字段，顺序固定，不得增删换序**：

```yaml
---
title: 主标题
source: 来源 | 源链接
author: 作者名（可附主页链接）
duration: x分x秒（非视频一律 0分0秒）
word_count: 正文字数（不含 frontmatter 与转写附录）
created: 2026/8/3 22:23（精确到分钟）
tags: [标签1, ...]（最低 6 个，首个为 "{来源网站}学习笔记"）
type: {来源网站小写}-ai-teaching-note
---
```

**来源网站 → 首个 tag / type 映射**：

| 来源网站 | 首个 tag | type |
|---|---|---|
| 抖音 | 抖音学习笔记 | douyin-ai-teaching-note |
| B站 / bilibili | B站学习笔记 | bilibili-ai-teaching-note |
| YouTube / youtube | YouTube学习笔记 | youtube-ai-teaching-note |
| 其他网站 | {网站名}学习笔记 | {网站名小写}-ai-teaching-note |
| 文本整理 | 抖音学习笔记（项目默认） | douyin-ai-teaching-note |

**正文结构（顺序固定）**：

| 栏目 | 要求 |
|---|---|
| 一句话总结 | 标题下方 `>` 引用块 |
| 📚 概述 | 学完能得到什么；含 学习目标 / 前置知识 |
| 🧠 核心知识点 | 每个含 定义 / 通俗类比 / 原理 / 示例 / 💡为什么重要 / ⚠️易错点 |
| 📖 专业词汇表 | 4 字段：英文 \| 中文 \| 通俗解释 \| 视频原句 |
| ❓ 费曼思考题 | 核心 10 道 / 重要 8 道 / 一般 6 道，四角度开放题 |
| 📄 完整转写附录 | `---` 分隔线后，AI 核对用 |

**核心知识点六段式**：定义（一句话专业准确）→ 通俗类比（生活化比喻）→ 原理（逻辑递进）→ 示例（引用视频原句）→ 💡为什么重要 → ⚠️易错点。

**费曼思考题**：每个知识点末尾按重要程度配题 —— 核心 10 道 / 重要 8 道 / 一般 6 道；从 复述 / 类比 / 应用推导 / 挑错 四角度出开放题。

**OCR 必须纠错**：识别错字/乱码/误识需结合上下文纠正（英文单词、专业术语、数字），可参考 `scripts/ocr_corrections.json` 词典（键=识别错的文本，值=正确文本）。

**风格铁律**：特别详细 / 清晰有条理 / 通俗易懂（类比）/ 专业准确（保留中英术语）/ 可教学 —— AI 读完能照本宣科把学生讲懂。

## 目录规则（五类统一）

`{类别}/{日期}/{顺序}_{日期}_{概要}_{大小}`，顺序号按当天创建，每日期文件夹独立从 00 开始。

| 类别 | 位置 |
|---|---|
| 视频 | `视频/{日期}/{顺序}_{日期}_{概要}_{大小}/` |
| 音频 + 转写 | `音频/{日期}/{顺序}_{日期}_{概要}_{大小}/` |
| 图片 / 图集 | `图片/{日期}/{顺序}_{日期}_{概要}_{大小}/` |
| 文本 | `文本/{日期}/{顺序}_{日期}_{概要}_{大小}/` |
| 笔记（AI 教材） | `NoteBooks/{日期}/{顺序}_{日期}_{概要}_{大小}.md` |

## 配置与故障

**环境变量**（全部可省略，脚本基于自身目录自动推导），见仓库根 `.env.example`：

| 变量 | 作用 |
|---|---|
| `DD_BASE` | 数据根目录（视频/音频/图片/文本/NoteBooks/temp 落这里） |
| `DD_DL_PY` / `DD_DL_SRC` | 抖音下载器解释器 / douyin-downloader 源码目录 |
| `DD_ASR_PY` | FunASR 转写解释器 |
| `DD_OCR_PY` | OCR 脚本解释器（RapidOCR / PaddleOCR） |
| `DD_YTDLP` | yt-dlp 可执行文件（默认 `yt-dlp`，仅非抖音链接需要） |
| `GLM_API_KEY` | GLM 视觉 API Key（仅 `--glm yes` 时需要） |

依赖的 3 个解释器（下载器/FunASR/PaddleOCR）可指向独立 venv，也可全部指向同一 Python（依赖装一起）。
系统依赖：Python 3.10+；ffmpeg / ffprobe 需加入 PATH。

**纠错词典**：`config/` 下是示例配置，运行时复制到 `scripts/`（脚本从自身所在目录加载）：

```powershell
copy config\corrections.example.json   scripts\corrections.json
copy config\ocr_corrections.example.json scripts\ocr_corrections.json
```

ASR 纠错示例：`"get up": "github"`（转写管线自动套用）；OCR 词典作为生成笔记时的参考词典（OCR 误识由生成方结合上下文纠正）。词典文件可随时增补。

**抖音 Cookie 过期**：报反爬 / Empty 200 → 运行 `scripts/get_douyin_cookie.bat` 重新抓取登录 Cookie 后重跑。

**GLM_API_KEY**：`https://open.bigmodel.cn` BigModel 开放平台申请；未设置时 `--glm yes` 报 `[ERR] 未设置 GLM_API_KEY 环境变量`，改用 `--glm no`。

**长视频（>10 分钟）转写**：需几分钟，等待完成，不中断进程。
