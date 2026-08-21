#!/usr/bin/env python3
"""core/video.py — 视频域链路编排：extract(音频+画面)→clean→assemble→半成品 md。

组装顺序（单向依赖 core→{engines,clean,assemble}）：
  视频 → ffmpeg 提音频 → ASR→json
       → OCR(+坐标排序)→ visual.txt
       → 清洗(transcript + visual)
       → assemble.interleave → 半成品 md
返回产物路径 dict；引擎已有产物时跳过（断点），仅 clean+assemble 也可用。
"""
from __future__ import annotations

import os
import subprocess

import clean.transcript as transcript
import clean.visual as visual
import assemble.interleave as interleave
from engines import ffmpeg

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_ENGINES_DIR = os.path.join(_ROOT, "engines")

# 引擎解释器（core/base 配置或环境变量）
ASR_PY = os.environ.get("ASR_PY", "")
OCR_PY = os.environ.get("OCR_PY", "")


def _run(cmd, timeout=3600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def process_video(video: str, glm: str = "no", out_root: str = "") -> dict:
    """视频 → 半成品 md。返回 {tjson, vtxt, clean_json, clean_md, chars}。"""
    if not os.path.isfile(video):
        return {"error": f"视频不存在: {video}"}
    stem = os.path.splitext(os.path.basename(video))[0]
    out_root = out_root or os.path.join("_转写缓存", stem)
    os.makedirs(out_root, exist_ok=True)

    tjson = os.path.join(out_root, f"{stem}.json")
    vtxt = os.path.join(out_root, f"{stem}_visual.txt")

    # ① 提音频 → wav（缺则生成）
    wav = os.path.join(out_root, f"{stem}.wav")
    if not (os.path.exists(wav) and os.path.getsize(wav) > 0):
        ffmpeg.extract_audio(video, wav)

    # ② ASR 转写 → json（断点跳过）
    if os.path.exists(tjson) and os.path.getsize(tjson) > 0:
        pass
    else:
        _run([ASR_PY, os.path.join(_ENGINES_DIR, "asr.py"), wav, tjson], timeout=7200)

    # ③ 画面 OCR → visual（断点跳过）
    if not (os.path.exists(vtxt) and os.path.getsize(vtxt) > 0):
        _run([OCR_PY, os.path.join(_ENGINES_DIR, "ocr.py"), video,
              "--interval", "1", "--glm", glm, "--out", vtxt], timeout=14400)

    # ④ 清洗（json 保结构 + 画面逐帧）
    cjson = transcript.clean_transcript_json(tjson) if os.path.exists(tjson) else ""
    cvisual = visual.clean_visual_timeline(vtxt) if os.path.exists(vtxt) else ""

    # ⑤ 组装：时间交错 → 半成品 md
    if not cjson and not cvisual:
        return {"error": "转写 json 与画面 txt 均缺失，无法组装", "tjson": tjson, "vtxt": vtxt}
    md = interleave.assemble_interleaved(cjson, cvisual, title=stem)
    clean_md = os.path.join(out_root, f"{stem}_clean.md")
    with open(clean_md, "w", encoding="utf-8") as f:
        f.write(md)

    return {"tjson": tjson, "vtxt": vtxt, "clean_json": cjson,
            "clean_visual": cvisual, "clean_md": clean_md, "chars": len(md)}