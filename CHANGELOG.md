# Changelog
All notable changes to media-to-notes are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning follows [Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/SpiralQWQ/media-to-notes/releases/tag/v0.1.0
