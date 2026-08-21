#!/usr/bin/env python3
"""clean/visual.py — 画面 txt 切帧清洗（含噪音判断，供 plain 复用）。

输入：视频帧 OCR/GLM txt（`===== 帧 MM:SS (第N/总帧) =====` 结构 + OCR/GLM 标签 + 界面水印）。
输出：每帧 `[MM:SS]\\n清洗后内容`（时间戳由此持有，永不丢失）；删标签/界面水印独立行。
"""
from __future__ import annotations

import os
import re

from . import clean_segment

# 视觉 txt 帧标记
_FRAME_RE = re.compile(r"===== 帧 (\d+):(\d+) \(第\d+/\d+帧\) =====")

# 画面 OCR 标签行（整行删）
_VISUAL_LABELS = ["[画面文字 OCR]", "[GLM画面理解]"]

# 界面水印/按钮碎片（独立短行含任一 → 删；长描述内嵌不删）
_VISUAL_WATERMARKS = [
    "坚持打卡", "片名：", "知识点", "高手盲听", "纯英文字幕", "初学看字幕",
    "点赞", "收藏", "关注", "分享", "爱说英语",
]
# 通用内容噪音（任意长度行含任一 → 删）：AI 生成标记 / 阅读/推荐类 UI
_COMMON_NOISE = [
    "以上内容由AI生成", "以上内容由 AI 生成", "以上内容由AI大模型生成",
    "阅读全文", "展开更多", "相关推荐", "大家都在搜", "换一换",
]


def is_noise_line(line: str) -> bool:
    """行是否噪音：通用噪音 / OCR 标签行 / 界面水印短独立行。"""
    s = line.strip()
    if not s:
        return True
    if any(w in s for w in _COMMON_NOISE):
        return True
    if any(lbl in s for lbl in _VISUAL_LABELS):
        return True
    if len(s) <= 24:  # 只对短独立行判水印（防误删长描述中的内嵌界面词）
        for w in _VISUAL_WATERMARKS:
            if w in s:
                return True
    return False


def clean_visual_timeline(visual_path: str, out_path: str = "") -> str:
    """画面 txt 切帧清洗：切帧提取时间戳 → 逐帧清洗 → 每帧 `[MM:SS]\\n内容`保留。"""
    if not os.path.isfile(visual_path):
        raise FileNotFoundError(f"视觉 txt 不存在: {visual_path}")
    with open(visual_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    if not raw.strip():
        raise ValueError(f"视觉 txt 为空: {visual_path}")

    parts = _FRAME_RE.split(raw)  # [前导, mm, ss, content, mm, ss, ...]
    frames = [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts), 3)]
    if not frames:
        raise ValueError("视觉 txt 无帧标记（期望 '===== 帧 MM:SS (第N/总帧) ====='）")

    kept = []
    for mm, ss, content in frames:
        lines = [clean_segment(l) for l in content.split("\n") if not is_noise_line(l)]
        lines = [l for l in lines if l]
        if lines:
            kept.append(f"[{int(mm):02d}:{int(ss):02d}]\n" + "\n".join(lines))

    out_path = out_path or os.path.splitext(visual_path)[0] + "_clean.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(kept))
    n = sum(1 for _ in frames)
    print(f"      [清洗] 视觉 txt → {os.path.basename(out_path)} ({n} 帧 → {len(kept)} 块带时间戳)")
    return out_path