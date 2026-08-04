# Changelog
All notable changes to media-to-notes are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

- **Added** Local path support: video / image / text files are used directly, no downloader needed
- **Added** Text-type branch (📄): local .txt/.md/.markdown → directly structured into an AI teaching note
- **Added** yt-dlp source routing for YouTube / Bilibili / other links (requires `yt-dlp`; `DD_YTDLP` to override)
- **Fixed** Path sanitization: directory/file names strip Windows-illegal characters and `..`; aweme_id validated as pure digits
- **Fixed** `.env` is now actually loaded via `python-dotenv` (media_to_notes.py, glm_vision.py)
- **Fixed** Dependencies: added `soundfile`, `paddlepaddle`, `python-dotenv`; documented `yt-dlp`
- **Fixed** Robustness: temp-frame dir cleanup on all exit paths (atexit), ffprobe/ffmpeg timeouts, VideoCapture released on error
- **Fixed** Friendly error when `--glm` runs without a prior `--detect`; missing downloader gives an actionable message
- **Changed** Docs aligned with code: multi-source support described honestly; ocr_corrections.json described as a reference dictionary (not auto-applied)
- **Changed** CLAUDE.template.md license annotation MIT → dual (AGPL-3.0 / commercial)
- **Fixed** Windows console (GBK): UTF-8 stdout/stderr reconfigured so emoji/Chinese never crash; `run()` now catches TimeoutExpired / FileNotFoundError / PermissionError / OSError with readable messages; a corrupt state file gives a readable error instead of a traceback
- **Fixed** OCR & pipeline robustness: per-image isolation (a bad image no longer aborts the whole batch); malformed timestamps fall back instead of crashing; directory sequence numbers support ≥100 entries per day
- **Verified** Final acceptance: all six review dimensions passed — code robustness, security & privacy, multi-source distribution correctness, dependency & configuration closure, docs consistency, license & disclaimer; tri-party review avg 96.3/100 (≥95 threshold)

## [0.1.0] — 2026-08-03

Initial open-source release.

- **Added** Two-phase pipeline: `--detect` downloads/detects/organizes; `--glm yes|no` transcribes and analyzes
- **Added** Multi-source download: Douyin (jiji262 watermark-free), YouTube/Bilibili (yt-dlp), local paths
- **Added** Content-type branching: video → ASR + multi-frame OCR (+ optional GLM on key frames); gallery → per-image OCR (+ optional GLM); text → direct notes
- **Added** SenseVoice per-segment transcription (fsmn-vad split + per-segment ASR + punctuation restoration)
- **Added** Video multi-frame OCR: 1 frame/second by default (capped at 1200 frames); GLM vision only on scene-change key frames to save cost
- **Added** AI teaching-note spec (spec/note_style_spec.md): 8-field frontmatter + six-part knowledge points + Feynman questions (10/8/6) + glossary + full transcript appendix
- **Added** Source-aware first tag & type (Douyin / Bilibili / YouTube / text)
- **Added** OCR/ASR correction dictionary examples (config/*.example.json)
- **Added** Portable config: every path overridable via env vars (DD_BASE/DD_DL_PY/DD_DL_SRC/DD_ASR_PY/DD_OCR_PY/DD_YTDLP/GLM_API_KEY); no hardcoded absolute paths
- **Fixed** Temp-frame directory cleanup in video visual analysis (missing shutil import)
- **Changed** License from MIT to dual license: AGPL-3.0 (open source) + commercial license (see COMMERCIAL.md)

[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
