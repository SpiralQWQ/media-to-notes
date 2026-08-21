#!/usr/bin/env python3
"""assemble/album.py — 图片/图集半成品 md（图序罗列，无时间轴）。

输入：已清洗的图片文本（每图一块，`【图N】/【文件名】` 开头，图序分隔）。
输出：`## 🖼️ 图集` 节，保留每图块与顺序；题首可加标题。
"""
from __future__ import annotations


def assemble_album(clean_text: str, title: str = "") -> str:
    """把清洗后的图集文本包装为图序罗列 md。clean_text 为空则返回空串。"""
    clean_text = (clean_text or "").strip()
    if not clean_text:
        return ""
    parts = []
    if title:
        parts.append(f"# {title}")
    parts.append("## 🖼️ 图集")
    parts.append(clean_text)
    return "\n\n".join(parts)