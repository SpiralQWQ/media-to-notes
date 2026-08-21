#!/usr/bin/env python3
"""assemble/timeline.py — 音频半成品 md：纯转写按时间戳排句子（无画面）。

输入：清洗后 json（含 sentences，带 start_ms）。
输出：`## 🎧 转写` 节，每句前缀 `[MM:SS] 🎤`，按时间升序。无 🖼（音频无画面）。
"""
from __future__ import annotations

import json
import os


def assemble_timeline(clean_json: str, title: str = "") -> str:
    """清洗后 json → 按时间戳排句子的转写 md。"""
    if not os.path.isfile(clean_json):
        raise FileNotFoundError(f"清洗后 json 不存在: {clean_json}")
    with open(clean_json, encoding="utf-8") as f:
        data = json.load(f)
    sents = data.get("sentences", []) if isinstance(data, dict) else []
    if not isinstance(sents, list):
        sents = []
    lines = []
    for s in sents:
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if not text:
            continue
        ms = int(s.get("start_ms") or 0)
        ts = f"[{ms // 60000:02d}:{ms % 60000 // 1000:02d}]"
        lines.append(f"{ts} 🎤 {text}")
    if not lines:
        raise ValueError(f"清洗后 json 无有效句子: {clean_json}")

    parts = []
    if title:
        parts.append(f"# {title}")
    parts.append("## 🎧 转写")
    parts.append("\n".join(lines))
    return "\n\n".join(parts)