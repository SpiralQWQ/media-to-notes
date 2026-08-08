---
name: media-to-notes
description: 任意内容（视频/图集/文本，来自抖音/YouTube/B站/本地）一键转 AI 教材学习笔记。用户丢链接或本地路径即自动触发。流程：下载→检测类型→**先问用户是否开启 GLM 视觉分析(glm-4.6v-flashx)**→OCR默认全做(视频多帧上限1200帧/图集逐张)→按需GLM画面理解→生成含概述/知识点/词汇表/费曼题的 AI 教材。用户说"只下载/不写笔记"时才只下载。
category: tool
tags: [抖音, YouTube, B站, 视频转笔记, 图集OCR, FunASR, 学习笔记, AI教材]
---

# 视频 → AI 教材学习笔记

把任意视频（抖音/YouTube/B站/本地文件）一键转成**喂给 AI 教学的 AI 教材笔记**。
笔记**不嵌图片**，但会**抽帧做画面文字识别（OCR）**来补全音频转写漏掉的视觉信息。

## 🚀 开箱即用（拉取后第一步）

**先跑配置向导，回答几个问题就能用，无需提前看文档：**

```powershell
python setup.py
```

向导会问 9 个问题（使用场景 / OCR 频率 / GLM 视觉 / 笔记语言 / 转写附录 / 费曼题密度 / 中间产物 / 笔记组织），
自动生成 `.env`（脚本运行时读）和 `spec/user_prefs.md`（Claude 生成笔记时遵循）。

## 触发方式

用户丢一个视频链接或本地视频路径即可触发（**无需明说"做笔记"**）。
用户明确说"只下载/不写笔记"时才只下载，不生成笔记。

## 用法（两阶段：先检测询问，再处理）

### 阶段1：检测（下载 + 识别类型）
```powershell
python scripts\media_to_notes.py "<链接>" --detect
```
- 抖音用 jiji262 去水印；YouTube/B站用 yt-dlp；本地视频/图片/文本直接用路径
- 下载 → 自动判断 🎬视频 / 🖼️图集 / 📄文本 → 归位（视频\ 音频\ / 图片\ / 文本\）→ 写状态文件 → 报告类型

### 阶段2：**必须先问用户**是否开启 GLM 视觉分析
向用户确认："这条是视频/图集，要开启 GLM 视觉分析（glm-4.6v-flashx）吗？（OCR 默认都做，GLM 会额外花钱）"
然后运行：
```powershell
python scripts\media_to_notes.py --glm yes|no
```
- 🎬 **视频** → ① SenseVoice 转写（`transcribe_funasr.py`）② **多帧 OCR 画面文字**（`video_frames_ocr.py`，默认间隔/上限由 `.env` 的 `OCR_INTERVAL` 控制，**OCR 全帧免费**）③ GLM=yes 时 **只对关键帧**（画面变化大的帧，`select_key_frames` 自动判断）调用 `glm_vision.py`（glm-4.6v-flashx）描述画面——省钱
- 🖼️ **图集** → ① OCR 每张图（`ocr_images.py`）② GLM=yes 再对每张图调用 `glm_vision.py` 描述

### 阶段3：Claude 读取转写/OCR/GLM 文本 → 按 `spec\note_style_spec.md` **+ `spec\user_prefs.md`（用户偏好）** 生成 AI 教材笔记
写入 `NoteBooks\{日期}\{顺序}_{日期}_{概要}_{大小}.md`（若 .env 设 `NOTE_ORGANIZE=topic` 则按课程/主题分目录）
**生成笔记前必读 `spec\user_prefs.md`**：遵循用户偏好（笔记语言 / 费曼题密度 / 是否保留附录 / 目录组织）。
**OCR 文本必须纠错**：识别错字/乱码/误识需结合上下文纠正（可查 `config\ocr_corrections.example.json`），保证专业准确

### 关键脚本
- `video_frames_ocr.py`：视频多帧 OCR + 可选 GLM（RapidOCR 轻量引擎）
- `glm_vision.py`：独立 GLM 视觉脚本（glm-4.6v-flashx，需 `GLM_API_KEY`）

## AI 教材笔记格式（风格规范）

- **frontmatter 固定 8 字段（顺序固定，详见 `spec\note_style_spec.md`）**：`title / source / author / duration / word_count / created / tags / type`
- **tags 首个 + type 按来源网站**：抖音→`抖音学习笔记`+`douyin-ai-teaching-note`；B站→`B站学习笔记`+`bilibili-ai-teaching-note`；YouTube→`YouTube学习笔记`+`youtube-ai-teaching-note`；其他网站类推（`{网站名小写}-ai-teaching-note`）；**文本整理→抖音默认**（`抖音学习笔记`+`douyin-ai-teaching-note`）；tags 最低 6 个
- 一句话总结
- 📚 概述 / 学习目标 / 前置知识
- 🧠 核心知识点（每个含：定义 / 通俗类比 / 原理 / 示例 / 💡为什么重要 / ⚠️易错点）
- 📖 专业词汇表（英文 | 中文 | 通俗解释 | 视频原句）
- **❓ 费曼思考题：每个知识点末尾按重要程度配题（密度见 `spec\user_prefs.md`，默认核心10 / 重要8 / 一般6）**
- `---` 分隔线 + 📄 完整转写附录（AI 核对用）
- 风格铁律：**特别详细 / 清晰有条理 / 通俗易懂(类比) / 专业准确(保留中英术语) / 可教学**

## 目录规则（五类统一）

`{类别}\{日期}\{顺序}_{日期}_{概要}_{大小}`，顺序 00/01/02 按当天创建（每日期文件夹独立从 00）。

| 类别 | 位置 |
|---|---|
| 视频 | `视频\{日期}\{顺序}_...\` |
| 音频+转写 | `音频\{日期}\{顺序}_...\` |
| 图片/图集 | `图片\{日期}\{顺序}_...\` |
| 文本 | `文本\{日期}\{顺序}_...\` |
| 笔记（AI 教材） | `NoteBooks\{日期}\{顺序}_....md` |

## 注意事项

- **抖音 Cookie 过期**（报反爬/Empty 200）：按 README「Cookie 设置」重新抓取登录 Cookie 后重跑
- **转写错听**：可往 `scripts\corrections.json` 加词条（如 "get up": "github"）
- 长视频(>10分钟)转写需几分钟，耐心等待
