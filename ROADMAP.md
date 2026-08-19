# Roadmap / 路线图

media-to-notes turns videos / image albums / text into AI teaching notes. This roadmap lists the improvements we're considering, in priority order. **Input is welcome** — open an issue to vote or propose something new.

media-to-notes 把视频/图集/文本变成 AI 教材笔记。下面是按优先级排列的改进方向，**欢迎提 Issue 投票或补充**。

---

## Current focus / 当前重点

The core pipeline (download → ASR/OCR → note) is stable and released. **v0.3.0 (2026-08) added built-in zero-config cleaning** (transcript JSON + per-frame visual + plain text) and **timeline interleaving** (speech + frames aligned by timestamp into a half-ready Markdown), with three-branch tests (`tests/`, report `docs/test-report-v0.3.0.md`).

核心管线（下载 → 转写/OCR → 笔记）已稳定发布。**v0.3.0（2026-08）新增内置零配置清洗**（转写 json 保结构 + 画面逐帧 + 图集/文本通用）和**时间轴交错**（转写 + 画面按时间戳对齐成半成品 md），并附三分支测试（`tests/`，报告 `docs/test-report-v0.3.0.md`）。

Next up is making **visual extraction smarter**: today a video frame or image is OCR'd into plain text, which loses structure (tables, formulas, code).

下一步是**让画面信息提取更聪明**：现在视频帧/图片的 OCR 只得到纯文字，表格、公式、代码的结构会丢失。

---

## Planned / 规划中

| Priority | Improvement | Value | Cost | Notes |
|---|---|---|---|---|
| P0 | **Preserve code-block structure** (indentation / syntax) | ⭐⭐⭐ | ⭐⭐ | Low-hanging: OCR text + post-processing |
| P1 | **Table recognition** → Markdown tables | ⭐⭐⭐⭐ | ⭐⭐⭐ | e.g. TableMaster |
| P2 | **Formula recognition** → LaTeX | ⭐⭐⭐ | ⭐⭐⭐ | e.g. LaTeX-OCR / UniMERNet; on demand |
| P3 | **Layout analysis** for mixed content (title / paragraph / table / formula / code) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Long-term umbrella |

### Why these / 为什么是这些

- **Tables** — a screenshot of a data table becomes a text blob today; a Markdown table keeps the structure the note needs.
  （现在的数据表格截屏识别后变成一坨文字，Markdown 表格能保住结构）
- **Formulas** — LaTeX round-trips into renderable math and stays AI-searchable.
  （LaTeX 能还原成可渲染的公式，且便于 AI 检索）
- **Code** — preserved indentation makes code samples actually teachable.
  （保住缩进的代码示例才能教学）
- **Layout** — the umbrella that lets all of the above work together on one frame.
  （版面分析是让上述能力在同一帧上协同工作的总开关）

---

## Explicitly not planned / 明确不做

We will **not** integrate the whole MinerU document-parsing engine:

1. **MinerU is a PDF/PPT document parser** — it doesn't accept a single image / video frame as input. （MinerU 面向 PDF/PPT 文档，不吃单张视频帧）
2. **It's too heavy** — loading its full model stack (layout + table + formula + OCR) costs 10–20 s cold start per image. （整栈模型对单帧太重，冷启动 10–20 秒）
3. **It restores structure, not meaning** — the notes still need vision understanding (GLM) on top. （它只还原结构、不理解内容，笔记仍需 GLM 视觉理解）

Instead we pick individual, purpose-built models when a scenario needs them — light, on-demand, and compatible with the existing pipeline.

（策略：按场景按需选用专项模型，轻量、灵活、兼容现有流程）

---

## Community input / 社区参与

- Vote or propose in [Issues](https://github.com/SpiralQWQ/media-to-notes/issues)
- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)

## Reference models / 参考模型

- [TableMaster](https://github.com/minend/TableMaster)
- [LaTeX-OCR](https://github.com/lukas-blecher/LaTeX-OCR)
- [UniMERNet](https://github.com/opendatalab/UniMERNet)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
