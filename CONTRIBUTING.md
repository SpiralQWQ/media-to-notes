# Contributing to media-to-notes / 贡献指南

Thanks for taking the time to contribute! 🎉
欢迎任何形式的贡献：报 Bug、提功能建议、修文档、写代码，都欢迎。

## Table of Contents / 目录

- [Project Conventions / 项目约定](#project-conventions-项目约定)
- [Reporting Bugs / 提交 Bug](#reporting-bugs-提交-bug)
- [Feature Requests / 功能建议](#feature-requests-功能建议)
- [Development Setup / 本地开发](#development-setup-本地开发)
- [Testing / 测试](#testing-测试)
- [Pull Request Process / PR 流程](#pull-request-process-pr-流程)
- [Commit & Changelog / 提交与变更日志](#commit-changelog-提交与变更日志)

## Project Conventions / 项目约定

Please read the README first. The most important rules, keep them intact:

1. **Two-stage CLI contract** — `python scripts/media_to_notes.py "<source>" --detect` (download + detect + organize), then `python scripts/media_to_notes.py --glm yes|no` (transcribe / OCR / GLM). Don't merge the stages or rename the flags.
2. **Portable config, no hardcoded paths** — every machine-specific path must be overridable via environment variables (`DD_*`, `GLM_API_KEY`, `OCR_INTERVAL`, `GLM_MODE`, …). Never hardcode an absolute path or a local folder name.
3. **The note style spec is the contract** — AI teaching notes must follow `spec/note_style_spec.md` (8-field frontmatter, six-part knowledge points, Feynman questions, glossary, full-transcript appendix). Changes to the spec are breaking: discuss first.
4. **Python 3.10+** — scripts use `dict | None` union syntax.
5. **Windows-friendly** — scripts must print Chinese / emoji on a GBK console (keep the `sys.stdout.reconfigure` block) and use forward slashes in documentation paths.

> 中文摘要：保持两阶段 CLI 契约、路径全部走环境变量（禁硬编码绝对路径/本地文件夹名）、笔记格式以 `spec/note_style_spec.md` 为准、Python 3.10+、保持 Windows 中文控制台兼容与文档正斜杠。

## Reporting Bugs / 提交 Bug

Open an issue with the **bug report template**. Please include:

- The exact command you ran (link / local path / flags).
- The full error output (paste, don't paraphrase).
- OS + Python version + how you installed dependencies.
- Whether you configured a Douyin Cookie / `GLM_API_KEY` (say "no" if you didn't — that's useful info too).

> 报 Bug 请附上：完整命令、完整错误输出、系统与 Python 版本、依赖安装方式、是否配置了 Cookie / GLM_API_KEY。

## Feature Requests / 功能建议

Open a **feature request** issue. A good request describes:

- The problem you're trying to solve (not just the feature name).
- A concrete example input → expected output.
- Whether it affects the two-stage CLI contract or the note spec.

> 提功能请描述「要解决的问题 + 具体输入输出例子 + 是否影响 CLI 契约或笔记规范」，而不是只给个功能名。

## Development Setup / 本地开发

```bash
git clone https://github.com/SpiralQWQ/media-to-notes.git
cd media-to-notes
pip install -r requirements.txt          # heavy deps (FunASR/PaddleOCR) can go in a separate venv
python setup.py                           # optional: generates .env + spec/user_prefs.md
```

The ASR stack (`funasr`, `modelscope`) and OCR stack (`paddleocr`, `rapidocr-onnxruntime`) are heavy — a dedicated venv for each is fine; point `DD_ASR_PY` / `DD_OCR_PY` at them.

## Testing / 测试

Before submitting, at minimum:

```bash
python -m py_compile scripts/*.py setup.py          # syntax
python scripts/media_to_notes.py --help             # CLI loads
# plus a real pass on a short local file:
python scripts/media_to_notes.py "<local text or video>" --detect
python scripts/media_to_notes.py --glm no
```

If your change touches `video_frames_ocr.py` / `ocr_images.py` / `glm_vision.py`, test the relevant `--glm yes|no|all` combinations (key-frame vs all-frame GLM) with a short sample.

> 提交前至少：`py_compile` 全脚本、CLI 能启动、本地短文件跑通 `--detect` + `--glm no`。改 OCR/GLM 相关脚本请同时测 `--glm yes` / `--glm all`。

## Pull Request Process / PR 流程

1. Fork the repo, create a branch, commit your change.
2. Keep the PR **small and focused** — one logical change per PR.
3. Add a **CHANGELOG.md + CHANGELOG_zh.md** entry under the top version (or `[Unreleased]`).
4. Run the tests above.
5. In the PR description, state: what changed, how you tested it, and whether it affects the CLI contract / note spec.

## Commit & Changelog / 提交与变更日志

We follow [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/). Each release's changes are logged in `CHANGELOG.md` (EN) and `CHANGELOG_zh.md` (ZH) — keep both in sync.

Suggested commit prefixes: `feat:` / `fix:` / `docs:` / `refactor:` / `perf:` / `chore:`.

---

Questions? Open an issue — we're friendly. Thanks again for helping make media-to-notes better. 🙏
