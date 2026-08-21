#!/usr/bin/env python3
"""clean/transcript.py — 转写 json 保结构清洗。

把 ASR 转写 json 逐段/逐句清洗：标点规范化、纯标点段清空、段去重，保结构/时间戳/置信度。
输入/输出都保持 `{text, segments[], sentences[]}` 结构，供后续组装。
"""
from __future__ import annotations

import json
import os
import re

from . import clean_segment  # 公共原语：标点规范化 + 段清洗


def _seg_key(text: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]", "", (text or "").lower())


def _has_chinese(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def clean_transcript_json(json_path: str, out_path: str = "") -> str:
    """读取 ASR json → 清洗 → 写 *_clean.json（保结构）。返回输出路径。"""
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"转写 json 不存在: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"转写 json 结构异常: {json_path}")

    def _dedup_segments(segs):
        """去重：同文本+同时间戳 → 删后留前（中英文都去重）；中文段在不同时间戳时永不删。"""
        seen, kept = {}, []
        for seg in segs or []:
            if not isinstance(seg, dict):
                continue
            text = seg.get("text") or ""
            if not isinstance(text, str):
                text = str(text)
            key = _seg_key(text)
            ts = (seg.get("start_ms"), seg.get("end_ms"))
            if key in seen and seen[key][1] == ts:
                continue
            if _has_chinese(text):
                kept.append(seg)
                seen[key] = (len(kept) - 1, ts)
                continue
            kept.append(seg)
            seen[key] = (len(kept) - 1, ts)
        return kept

    out = {"text": clean_segment(data.get("text", "")), "segments": [], "sentences": []}
    for seg in _dedup_segments(data.get("segments")):
        out["segments"].append({
            "text": clean_segment(seg.get("text", "")),
            "start_ms": seg.get("start_ms"),
            "end_ms": seg.get("end_ms"),
            "confidence": seg.get("confidence"),
            "review": seg.get("review", False),
        })
    for sent in data.get("sentences") or []:
        if not isinstance(sent, dict):
            continue
        out["sentences"].append({
            "text": clean_segment(sent.get("text", "")),
            "start_ms": sent.get("start_ms"),
            "end_ms": sent.get("end_ms"),
            "confidence": sent.get("confidence"),
        })

    out_path = out_path or os.path.splitext(json_path)[0] + "_clean.json"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n_in = len(data.get("segments", []))
    n_out = len(out["segments"])
    print(f"      [清洗] 转写 json → {os.path.basename(out_path)} (segments {n_in}→{n_out})")
    return out_path