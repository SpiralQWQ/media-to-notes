#!/usr/bin/env python3
"""assemble/interleave.py — 视频半成品 md：转写 + 画面按时间戳交错。

避免"画面在末尾被忽略"：把清洗后 json 的转写句与清洗后 visual 的画面帧按时间轴混排，
同时间先转写后画面，Claude 一眼对应。此为三模态之「视频」组装的实现。
"""
from __future__ import annotations

import json
import os
import re


def assemble_interleaved(clean_json: str, visual_clean: str = "", title: str = "") -> str:
    """按时间轴交错转写句子与画面帧 → md 文本。画面帧取开始时间，[MM:SS] 或 [MM:SS~MM:SS] 均支持。"""
    if not os.path.isfile(clean_json):
        raise FileNotFoundError(f"清洗后 json 不存在: {clean_json}")

    with open(clean_json, encoding="utf-8") as f:
        data = json.load(f)
    sents = data.get("sentences", []) if isinstance(data, dict) else []
    if not isinstance(sents, list):
        sents = []
    events = []
    for s in sents:
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if not text:
            continue
        events.append((int(s.get("start_ms") or 0) / 1000, "transcript", text))

    if not events:
        raise ValueError(f"清洗后 json 无有效句子: {clean_json}")

    if visual_clean and os.path.isfile(visual_clean):
        with open(visual_clean, encoding="utf-8", errors="replace") as f:
            vtxt = f.read().strip()
        if vtxt:
            for block in re.split(r"\n(?=\[\d{2}:\d{2})", vtxt):
                block = block.strip()
                if not block:
                    continue
                m = re.match(r"\[(\d{2}):(\d{2})", block)
                if m:
                    sec = int(m.group(1)) * 60 + int(m.group(2))
                    events.append((sec, "visual", block))

    events.sort(key=lambda e: (e[0], 0 if e[1] == "transcript" else 1))

    parts = []
    if title:
        parts.append(f"# {title}")
    parts.append("## 转写 + 画面（时间轴交错）")
    lines = []
    for sec, typ, text in events:
        ts = f"[{int(sec) // 60:02d}:{int(sec) % 60:02d}]"
        if typ == "visual":
            if "\n" in text:
                lines.append(f"🖼 {text.lstrip()}")   # 多行画面块
            else:
                lines.append(f"🖼 {text}")
        else:
            lines.append(f"{ts} 🎤 {text}")
    parts.append("\n".join(lines))
    return "\n\n".join(parts)