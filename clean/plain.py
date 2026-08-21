#!/usr/bin/env python3
"""clean/plain.py — 通用文本清洗（图集 OCR 文本 / 纯文本）。

对字符串做行级清洗：删噪音行（AI 标记/界面水印/标签/推荐类），标点与空白规整。
"""
from __future__ import annotations

from . import clean_segment
from .visual import is_noise_line


def clean_plain_text(text) -> str:
    """通用文本清洗：删噪音行 + 标点/空白规整。无内容返回空串。"""
    if not text:
        return ""
    lines = []
    for line in str(text).split("\n"):
        if is_noise_line(line):
            continue
        c = clean_segment(line)
        if c:
            lines.append(c)
    return "\n".join(lines)