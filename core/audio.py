#!/usr/bin/env python3
"""core/audio.py — 音频域链路编排：ASR→json→clean→timeline→半成品 md。

音频只有声音（json 转写），无画面。复用 engines/asr（subprocess）+ clean/transcript + assemble/timeline。
"""
from __future__ import annotations

import os
import subprocess

import clean.transcript as transcript
import assemble.timeline as timeline

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_ENGINES_DIR = os.path.join(_ROOT, "engines")
ASR_PY = os.environ.get("ASR_PY", "")


def process_audio(audio: str, out_root: str = "") -> dict:
    """音频 → 半成品 md。返回 {tjson, clean_json, clean_md, chars}。"""
    if not os.path.isfile(audio):
        return {"error": f"音频不存在: {audio}"}
    out_root = out_root or os.path.join("_转写缓存", "音频")
    os.makedirs(out_root, exist_ok=True)
    stem = os.path.splitext(os.path.basename(audio))[0]
    tjson = os.path.join(out_root, f"{stem}.json")

    # ① ASR 转写 → json（断点：已存在则复用）
    if not (os.path.exists(tjson) and os.path.getsize(tjson) > 0):
        subprocess.run([ASR_PY, os.path.join(_ENGINES_DIR, "asr.py"), audio, tjson],
                       capture_output=True, timeout=7200)

    # ② 清洗（json 保结构）
    cjson = transcript.clean_transcript_json(tjson) if os.path.exists(tjson) else ""

    # ③ 组装：按时间排 → md
    if not cjson:
        return {"error": "转写 json 缺失，无法组装", "tjson": tjson}
    md = timeline.assemble_timeline(cjson, title=stem)
    clean_md = os.path.join(out_root, f"{stem}_clean.md")
    with open(clean_md, "w", encoding="utf-8") as f:
        f.write(md)
    return {"tjson": tjson, "clean_json": cjson, "clean_md": clean_md, "chars": len(md)}