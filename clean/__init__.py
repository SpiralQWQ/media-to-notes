#!/usr/bin/env python3
"""clean — 清洗层（纯文本，零外部依赖，被 core 单向调用）。

模块内只含纯文本清洗原语，不含任何引擎/IO 业务，保证可独立单测、可复用。
公共原语（标点规范化、段落清洗）放在本包 __init__，供 transcript/visual/plain 引用。
"""
from __future__ import annotations

import re

# 标点乱码规范化（ASR/OCR 转写常见）：,,→, / ..→. / ??→? / 中文标点压缩
_PUNCT_PAIRS = [
    (re.compile(r",{2,}"), ","),
    (re.compile(r"\.{2,}"), "."),
    (re.compile(r"\?{2,}"), "?"),
    (re.compile(r",\."), "."),
    (re.compile(r"\.,"), "."),
    (re.compile(r"。，"), "。"),
    (re.compile(r"，。"), "。"),
    (re.compile(r"。{2,}"), "。"),
    (re.compile(r"，{2,}"), "，"),
]


def norm_punct(text: str) -> str:
    """标点乱码规范化。"""
    for rx, repl in _PUNCT_PAIRS:
        text = rx.sub(repl, text)
    return text.strip()


def clean_segment(text) -> str:
    """单段/单句清洗：标点规范化 + 空白规整 + 纯标点/纯空白段清空（返回空串）。"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    t = norm_punct(text)
    t = re.sub(r"[ \t　]+", " ", t)
    t = t.strip()
    if not re.search(r"[A-Za-z0-9一-鿿]", t):  # 纯标点/纯空白 → 清空
        return ""
    return t