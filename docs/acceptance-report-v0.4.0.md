# Acceptance Report · media-to-notes v0.4.0

> Date: 2026-08-19
> Scope: Trimodal (video / image album / audio) + text, layered architecture, typed wizard.
> Process: fixloop (S1 tasks, S3 4-round review per task, S2 exhaustive, S4 acceptance).

## Result: PASS

### Added
- Layered processing: `core/` (video/image/audio) + `engines/` (asr/ocr/glm_vision/ffmpeg) + `clean/` (transcript/visual/plain) + `assemble/` (interleave/album/timeline).
- `cli.py` four-modal entry (video / image album / audio / text) with `--wizard` (per-type wizard).
- Audio pipeline (ASR → timeline md); image aligned with video (OCR + GLM per image, album batch → one md).
- Typed wizard: video all / image only GLM / audio only speaker.

### Kept (open-source essentials)
- Download (Douyin/YT/Bilibili + Cookie), type detection, text branch, setup.py, community files, dual license.

### Security / Privacy
- Removed hardcoded local venv paths from `core/base.py|video.py|audio.py` → env-only (`ASR_PY`/`OCR_PY`, no defaults).

### Cleanup
- Archived duplicate scripts to `scripts/_legacy/` (transcribe_funasr / video_frames_ocr / glm_vision / clean_timeline / assemble_md / notes_pipeline / splice_feynman / test_wizard); `media_to_notes.py` now uses the layered engines/clean/assemble; `ocr_images.py` kept for album.

### Test
- Existing tests green; cli text branch verified; exhaustive (no-arg / missing / bad-ext / text-consistency) pass. fixloop evidence rounds 027–033.
