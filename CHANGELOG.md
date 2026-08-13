# Changelog
All notable changes to media-to-notes are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

- **Docs** Removed the internal planning folder `优化方向/` from the repo (kept local, git-ignored) and replaced it with a polished bilingual [ROADMAP.md](ROADMAP.md) on the public roadmap

## [0.2.2] — 2026-08-13

- **Fixed** Privacy: `优化方向/README.md` stripped leftover internal environment references
- **Fixed** GBK console compatibility: all six sub-scripts now reconfigure stdout/stderr to UTF-8, so Chinese and emoji print cleanly on a Chinese Windows console (matches the main scripts)
- **Added** `--glm all` (video): `GLM_MODE=all` now truly analyzes **every** frame with GLM as documented — previously it silently fell back to key-frame analysis
- **Added** Open-source community files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.gitattributes`, `.github/` (issue & PR templates, `FUNDING.yml`), and a GitHub Actions CI that syntax-checks every push/PR
- **Fixed** `--glm no` now overrides `.env` `GLM_MODE`: the documented "free mode" switch works as expected
- **Fixed** `notes_pipeline.py`: usage and docstring now match behavior — the video argument is legacy and ignored (new 2-arg form is primary, old 3-arg form still accepted)
- **Docs** Open-source polish: README (EN/ZH) file tree completed; CHANGELOG version-link references added; FAQ & `GLM_MODE` descriptions aligned with real behavior; `README_zh.md` version number corrected to 0.2.1

## [0.2.1] — 2026-08-09

- **Fixed** Video OCR thread usage: `RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)` official thread limit — measured **33% faster** than the default 95 threads with 96% less CPU (env vars don't affect onnxruntime; the official config params are required)
- **Fixed** Privacy: `优化方向/README.md` no longer references local absolute paths — switched to the official MinerU docs link

## [0.2.0] — 2026-08-08

- **Added** Out-of-the-box setup wizard `setup.py`: clone, run `python setup.py`, answer 9 questions (use case / OCR frequency / GLM vision / note language / transcription appendix / Feynman density / intermediate files / note organization), and it writes `.env` + `spec/user_prefs.md` automatically — no docs required up front
- **Added** User-preference file `spec/user_prefs.md`: followed by Claude when generating notes (language / Feynman density / appendix / organization); SKILL.md and CLAUDE.template.md now say "read user_prefs.md before generating"
- **Added** Configurable video OCR frequency: `OCR_INTERVAL` (seconds, or `scene`/`no`) replaces the hardcoded 1 frame/second
- **Added** Configurable GLM mode: `GLM_MODE` (`yes`/`all`/`no`)
- **Added** Note-preference env vars: `NOTE_LANG` / `KEEP_APPENDIX` / `FEYNMAN_DENSITY` / `KEEP_MIDDLE` / `NOTE_ORGANIZE`
- **Changed** README (EN/ZH) install steps: added an "out-of-the-box setup wizard" step; env-var table expanded with the new settings
- **Fixed** Hardcoded `--interval 1` now reads `OCR_INTERVAL` from `.env`

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

[0.2.2]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.2
[0.2.1]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.1
[0.2.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.2.0
[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
