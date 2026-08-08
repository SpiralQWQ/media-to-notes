<p align="center">
  <!-- 封面占位：可放 assets/cover.png（推荐 1280×640）并取消下行注释 -->
  <!-- <img src="assets/cover.png" alt="media-to-notes" width="800"> -->
</p>

<p align="center">
  <a href="README.md"><kbd>🇺🇸 English</kbd></a> · <kbd>🇨🇳 中文</kbd>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-AGPL%203.0%20%7C%20Commercial-blue" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

<h1 align="center">media-to-notes</h1>
<p align="center"><b>任意内容 → AI 教材学习笔记</b></p>

<p align="center">
  丢一个链接或本地路径，自动 下载 → 转写/OCR → 生成「喂给 AI 教学」的 AI 教材笔记。
</p>

<p align="center">
  来源支持：抖音 · YouTube · B站 · 本地文件 ｜ <a href="https://github.com/SpiralQWQ/media-to-notes">GitHub</a> · <a href="https://gitee.com/Spiral_QWQ/media-to-notes">Gitee 镜像</a>

**目前仅支持抖音视频、图片、文本和本地视频、图片、文本的转写，其余平台还未测试，敬请期待**
</p>

## 💛 支持一下

如果这个项目帮到过你，可以请我喝杯咖啡 ☕。打赏全凭心意，不打赏也完全没关系——项目永远免费开源。做开源这么久，每一份小小的支持都能让我高兴很久。

<p align="center">
  <img src="assets/donate_wechat.jpg" alt="微信收款" width="200">
  <img src="assets/donate_alipay.jpg" alt="支付宝收款" width="200">
</p>

<p align="center"><i>能一路读到这里的你，谢谢。🙏</i></p>

---

## What It Does

media-to-notes 把视频、图集和文本自动变成结构化的 AI 教材笔记。笔记面向零基础学生，目标是「AI 读完这份笔记就能照着教人」，因此包含概述、核心知识点、专业词汇表、费曼思考题和完整转写附录。

| 图标 | 组件 | 说明 |
|:--:|---|---|
| 📥 | 下载多源 | 抖音 jiji262 去水印 · 本地文件直接走路径 · YouTube/B站 yt-dlp（已实现，未充分测试） |
| 🔎 | 类型自动检测 | 自动区分视频 / 图集 / 文本，并归位到对应目录 |
| 🎙️ | ASR 转写 | SenseVoice + fsmn-vad 逐段转写，带标点恢复 |
| 🖼️ | 多帧 OCR | 视频默认每 1 秒抽 1 帧（上限 1200 帧，RapidOCR 轻量引擎），识别画面文字 |
| 💰 | 关键帧 GLM | 只对画面变化大的关键帧调用 GLM，省视觉费用 |
| 📝 | AI 教材生成 | Claude 按 `spec/note_style_spec.md` 生成教材 |
| 📁 | 目录归位 | 统一 `{类别}/{日期}/{顺序}_{日期}_{概要}_{大小}` 规范 |
| 🔧 | OCR 纠错 | 纠错词典 + 笔记生成时结合上下文纠正误识 |

---

## Architecture

```
丢链接 / 本地路径
    │
    ▼
阶段1  --detect   下载 → 检测类型 → 归位 → 写状态 → 报告
    │
    ├── 视频 → ASR 逐段转写 → 多帧 OCR → [--glm yes] 关键帧 GLM
    ├── 图集 → 逐张 OCR → [--glm yes] 每张 GLM 描述
    └── 文本 → 直接整理
    │
    ▼
阶段3  Claude 读取转写 / OCR / GLM 文本
        按 spec/note_style_spec.md 生成 AI 教材
    │
    ▼
NoteBooks/{日期}/{顺序}_{日期}_{概要}_{大小}.md
```

转写脚本 `transcribe_funasr.py` 先把音频切成逐段再交给 SenseVoice，避免长视频一次转写失真。`notes_pipeline.py` 把转写 JSON 转成原始转写 markdown，作为笔记的附录素材。

---

## Installation

| 项目 | 要求 | 检查方式 |
|------|:--:|------|
| Python | 3.10+ | `python --version` |
| ffmpeg / ffprobe | 需加入 PATH | `ffmpeg -version` |
| 抖音 Cookie | 仅抖音需要（jiji262 下载器） | — |
| GLM_API_KEY | 可选，`--glm yes` 时需要 | — |

### 第一步 —— 克隆仓库

```bash
git clone https://github.com/SpiralQWQ/media-to-notes.git
cd media-to-notes
# 或 Gitee 镜像
git clone https://gitee.com/Spiral_QWQ/media-to-notes.git
```

### 第二步 —— 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含 PaddleOCR、FunASR、OpenCV。FunASR 的 SenseVoice 模型体积大，建议放进独立 venv，再用 `DD_ASR_PY` 指向它。下载器、转写、OCR 三个解释器可以各自独立，也可以全部指向同一个环境（依赖全部装一起），所有路径都可用环境变量覆盖。

抖音下载器 jiji262/douyin-downloader 需要单独克隆，位置默认是仓库根目录下的 `douyin-downloader`（可用 `DD_DL_SRC` 改）。

### 第三步 —— 开箱即用配置向导（推荐）

```bash
python setup.py
```

回答 9 个问题（使用场景 / OCR 频率 / GLM 视觉 / 笔记语言 / 转写附录 / 费曼题密度 / 中间产物 / 笔记组织），自动生成 `.env`（脚本运行时读）和 `spec/user_prefs.md`（Claude 生成笔记时遵循）。**无需提前看文档，答完即用。** 之后随时可重跑修改配置。

### 第四步 —— 安装 ffmpeg

下载 ffmpeg 并把 `bin` 目录加入 PATH，然后确认 `ffmpeg -version` 有输出。抽帧和音频提取都依赖它。

### 第五步 —— 配置环境变量

```bash
copy .env.example .env
```

> 用 `setup.py` 配置过的可跳过本步（已自动生成 .env）。手动配时：`.env` 里的变量**全部可省略**，脚本会基于自身目录自动推导（需要 `python-dotenv` 才自动加载，已在 requirements.txt 中）：

| 变量 | 作用 |
|------|------|
| `DD_BASE` | 数据根目录（视频/音频/图片/文本/NoteBooks/temp） |
| `DD_DL_PY` / `DD_DL_SRC` | 抖音下载器的解释器与源码目录 |
| `DD_ASR_PY` | FunASR 转写解释器 |
| `DD_OCR_PY` | OCR 脚本解释器（RapidOCR / PaddleOCR） |
| `DD_YTDLP` | yt-dlp 可执行文件（默认 `yt-dlp`，仅用抖音链接可忽略） |
| `GLM_API_KEY` | GLM 视觉分析 Key（可选） |
| `OCR_INTERVAL` | 视频画面 OCR 频率：秒数（`1`=每秒1帧 / `0.5`=每秒2帧）或 `scene`=画面变化才抽 / `no`=不OCR |
| `GLM_MODE` | GLM 画面理解：`yes`=只关键帧(省钱) / `all`=每帧(贵) / `no`=不用 |
| `NOTE_LANG` | 笔记正文语言：`zh`=中文 / `en`=英文 / `auto`=跟随内容 |
| `KEEP_APPENDIX` | 笔记末尾是否保留完整转写附录：`true` / `false` |
| `FEYNMAN_DENSITY` | 费曼思考题密度：`10`=10/8/6 / `6`=6/4/3 / `0`=不要 |
| `KEEP_MIDDLE` | 转写中间产物是否保留到缓存：`true` / `false` |
| `NOTE_ORGANIZE` | 笔记目录组织：`date`=按日期 / `topic`=按课程主题分目录 |

### 第六步 —— 安装抖音下载器

仅下载抖音内容时需要。把 [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader) 克隆到仓库根目录，使 `douyin-downloader/run.py` 存在（或设置 `DD_DL_SRC` 指向其源码目录）：

```bash
git clone https://github.com/jiji262/douyin-downloader.git
```

### 第七步 —— 抖音 Cookie 设置

双击 `scripts\get_douyin_cookie.bat`（或按 jiji262/douyin-downloader 仓库 README）抓取登录 Cookie（保存到 `douyin-downloader/config.yml`，仅本机）。Cookie 过期时同样重新运行即可。

### 第八步 —— GLM_API_KEY（可选）

在智谱开放平台 [open.bigmodel.cn](https://open.bigmodel.cn) 申请 Key，填入 `.env` 的 `GLM_API_KEY`。不配置就无法开启 `--glm yes`。

> 使用 YouTube/B站等链接时另需 `pip install yt-dlp`；本地视频/图片/文本路径无需下载器。

---

## Usage

处理分两个阶段。先检测，再按确认结果处理。

```powershell
# 阶段1：下载 + 检测类型（会询问是否开启 GLM 视觉分析）
python scripts/media_to_notes.py "<抖音/YouTube/B站链接 或 本地路径>" --detect

# 阶段2：按确认结果执行
python scripts/media_to_notes.py --glm yes
python scripts/media_to_notes.py --glm no
```

`--glm no` 时不调用任何付费模型，OCR 与 ASR 全部在本地完成。`--glm yes` 只对关键帧调用 GLM，控制费用。

| 类型 | 转写 / 识别 | `--glm yes` 时 |
|---|---|---|
| 🎬 视频 | SenseVoice 逐段转写（fsmn-vad 分段 + 标点恢复）· 多帧 OCR 每 1 秒 1 帧（上限 1200 帧，RapidOCR） | 只分析关键帧（画面差异自动选帧） |
| 🖼️ 图集 | 逐张 OCR（PaddleOCR 优先，RapidOCR 兜底） | 每张图生成画面描述 |
| 📄 文本 | 直接整理为 AI 教材 | 不涉及 |

纠错词典放在 `config/`：`corrections.example.json`（ASR 词条，复制为 `scripts/corrections.json` 后由转写管线自动套用）；`ocr_corrections.example.json`（OCR 词条，复制为 `scripts/ocr_corrections.json` 作为生成笔记时的参考词典）。OCR 误识在笔记生成阶段由生成方结合上下文纠正。

---

## Note Format

笔记格式由 `spec/note_style_spec.md` 定义，生成时强制遵守。

**Frontmatter 固定 8 字段**（顺序固定，不可增删）：

`title / source / author / duration / word_count / created / tags / type`

**tags 首个标签与 type 按来源网站**：

| 来源 | 首个 tag | type |
|---|---|---|
| 抖音 | `抖音学习笔记` | `douyin-ai-teaching-note` |
| B站 | `B站学习笔记` | `bilibili-ai-teaching-note` |
| YouTube | `YouTube学习笔记` | `youtube-ai-teaching-note` |
| 其他网站 | `{网站名}学习笔记` | `{网站名小写}-ai-teaching-note` |
| 文本整理 | `抖音学习笔记`（项目默认） | `douyin-ai-teaching-note` |

**正文结构**：一句话总结 → 📚 概述（学习目标 / 前置知识）→ 🧠 核心知识点 → 📖 专业词汇表 → ❓ 费曼思考题 → 📄 完整转写附录。

**核心知识点固定六段**：定义 / 通俗类比 / 原理 / 示例 / 为什么重要 / 易错点。每个知识点末尾配费曼思考题，数量按重要程度：**核心 10 道 / 重要 8 道 / 一般 6 道**。词汇表四字段：`英文术语 | 中文 | 通俗解释 | 视频原句`，保留证据可溯源。

**风格铁律**：特别详细 / 清晰有条理 / 通俗易懂（善用类比）/ 专业准确（保留中英术语）/ 可教学 —— AI 读完能照本宣科把学生讲懂。**OCR 误识必须在生成笔记时结合上下文纠正**（错别字/乱码/英文单词/专业术语/数字）。

---

## File Tree

```
media-to-notes/
├── scripts/
│   ├── media_to_notes.py       # 主流程：两阶段（下载检测 + 处理）
│   ├── transcribe_funasr.py    # SenseVoice 逐段转写（fsmn-vad 分段）
│   ├── video_frames_ocr.py     # 视频多帧 OCR + 场景检测 + 关键帧 GLM
│   ├── ocr_images.py           # 图集逐张 OCR
│   ├── glm_vision.py           # 独立 GLM 视觉理解（glm-4.6v-flashx）
│   ├── notes_pipeline.py       # 转写 JSON → 原始转写 markdown
│   ├── splice_feynman.py       # 把预生成的费曼思考题块批量拼回笔记
│   └── get_douyin_cookie.bat   # 抖音登录 Cookie 抓取助手（扫码登录）
├── config/
│   ├── corrections.example.json       # ASR 纠错词典示例
│   ├── ocr_corrections.example.json   # OCR 纠错词典示例
│   └── README.md                      # 配置使用说明
├── spec/
│   └── note_style_spec.md             # AI 教材笔记风格规范
├── SKILL.md                           # Claude 技能（丢链接自动触发）
├── .env.example                       # 环境变量示例（全部可省略）
├── requirements.txt
├── LICENSE                            # AGPL-3.0（开源）+ COMMERCIAL.md（商业授权）
├── CHANGELOG.md / CHANGELOG_zh.md
└── README.md / README_zh.md
```

运行时在 `DD_BASE` 下自动生成五个类别目录，每个日期文件夹内序号从 `00` 开始：

```
DD_BASE/
├── 视频/{日期}/{顺序}_{日期}_{概要}_{大小}/
├── 音频/{日期}/{顺序}_{日期}_{概要}_{大小}/
├── 图片/{日期}/{顺序}_{日期}_{概要}_{大小}/
├── 文本/{日期}/{顺序}_{日期}_{概要}_{大小}/
├── NoteBooks/{日期}/{顺序}_{日期}_{概要}_{大小}.md
└── temp/current_job.json
```

---

## FAQ

<details>
<summary><b>抖音 Cookie 过期怎么解决？</b></summary>

报反爬或 Empty 200 时，按 jiji262/douyin-downloader 的 README 重新抓取登录 Cookie 并写入下载器配置，然后重跑 `--detect`。
</details>

<details>
<summary><b>GLM 要花钱吗？</b></summary>

ASR 与 OCR 全部免费在本地运行。GLM 视觉分析（glm-4.6v-flashx）按量计费，只在 `--glm yes` 时调用，且仅分析关键帧或图集逐张。不填 `GLM_API_KEY` 无法开启。
</details>

<details>
<summary><b>支持哪些网站？</b></summary>

抖音（jiji262 去水印，需 Cookie）、YouTube、B站（yt-dlp），以及任意本地视频 / 图片 / 文本文件。遇到不支持的网站先用 yt-dlp 兜底，再提 issue。
</details>

<details>
<summary><b>为什么要先问 GLM？</b></summary>

GLM 是整条流程里唯一花钱的环节。先确认避免无谓消耗：OCR 默认全做且免费，GLM 只对关键帧分析，已是省钱路径。
</details>

<details>
<summary><b>转写错了怎么纠正？</b></summary>

ASR 错听往 `config/corrections.example.json`（复制为 `scripts/corrections.json`）加词条，例如 `"get up": "github"`。OCR 误识用 `ocr_corrections.example.json`，笔记生成时还会结合上下文自动纠正。
</details>

<details>
<summary><b>能处理纯文本吗？</b></summary>

能。传入本地 `.txt` / `.md` 文件路径，跳过下载与 OCR，直接按 `spec/note_style_spec.md` 整理成 AI 教材。
</details>

---

## Changelog

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)。当前版本 0.1.0（2026-08-03 首发）。

---

## Contributing

Bug 与新网站支持先提 [GitHub Issues](https://github.com/SpiralQWQ/media-to-notes/issues)。报告时附上：输入链接或路径、完整错误输出、操作系统与 Python 版本、是否已配置 Cookie / GLM_API_KEY。

提交代码走 fork + PR。改动需保持两阶段结构，合并前跑通 `--detect` 与 `--glm no` 全流程。

---

## License（许可）

**双重许可：AGPL-3.0 或 商业授权**。

- **开源**：代码遵循 AGPL-3.0（见 [LICENSE](LICENSE)）——修改版必须继续开源，含网络服务场景。
- **商业**：闭源或商业用途需申请商业授权，见 [COMMERCIAL.md](COMMERCIAL.md)。

## 法律声明 / 免责声明

本工具**仅供个人学习研究使用**。下载、去水印或复用他人视频，可能违反平台服务条款与著作权法。使用者有责任遵守平台条款与当地法律，尊重原作者版权，**不得**将下载内容用于商业或公开传播。作者不对任何滥用行为负责。
