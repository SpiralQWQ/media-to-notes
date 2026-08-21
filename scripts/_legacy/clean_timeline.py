#!/usr/bin/env python3
"""clean_timeline.py — 内置清洗：转写 json 保结构清洗 + 画面 txt 逐帧清洗 + 通用文本清洗。

方案 A（成品、零配置）：清洗规则直接内嵌本脚本，**不依赖外部 text-cleaning-engine**，
media-to-notes 开箱即用。三条内容分支共用：
  - 转写 json → clean_transcript_json   （保结构逐句清洗 + 标点规范化 + 段去重）
  - 画面 txt  → clean_visual_timeline   （切帧 → 逐帧清洗 → 每帧 [MM:SS] 保留）
  - 图集/文本 → clean_plain_text        （通用文本清洗）

不破坏原工作流：原产物（json/txt）保留，清洗只额外产出 *_clean.* 供 Claude 生成 AI 笔记。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Windows 控制台 UTF-8（防 gbk 崩溃）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 视觉 txt 帧标记：===== 帧 MM:SS (第N/总帧) =====
_FRAME_RE = re.compile(r"===== 帧 (\d+):(\d+) \(第\d+/\d+帧\) =====")

# 标点乱码规范化（ASR/OCR 转写常见）
_PUNCT_PAIRS = [
    (re.compile(r",{2,}"), ","),
    (re.compile(r"\.{2,}"), "."),
    (re.compile(r"\?{2,}"), "?"),
    (re.compile(r",\."), "."),
    (re.compile(r"\.,"), "."),
    (re.compile(r"，。"), "。"),
    (re.compile(r"。，"), "。"),
    (re.compile(r"。{2,}"), "。"),
    (re.compile(r"，{2,}"), "，"),
]

# 画面 OCR 标签行（整行删）
_VISUAL_LABELS = ["[画面文字 OCR]", "[GLM画面理解]"]

# 画面界面水印/按钮碎片（独立行含任一子串 → 删行；GLM 描述内嵌的不删，防误删描述）
_VISUAL_WATERMARKS = [
    "坚持打卡", "片名：", "知识点", "高手盲听", "纯英文字幕", "初学看字幕",
    "点赞", "收藏", "关注", "分享", "爱说英语",
]

# 通用内容噪音（任意长度行含任一子串 → 删行）：AI 生成标记 / 阅读/推荐类 UI
_COMMON_NOISE = [
    "以上内容由AI生成", "以上内容由 AI 生成", "以上内容由AI大模型生成",
    "阅读全文", "展开更多", "相关推荐", "大家都在搜", "换一换",
]


def _norm_punct(text: str) -> str:
    """标点乱码规范化：,,→, / ..→. / ??→? / 。，→。 / 连续中文标点压缩。"""
    for rx, repl in _PUNCT_PAIRS:
        text = rx.sub(repl, text)
    return text.strip()


def _clean_segment(text: str) -> str:
    """单段/单句清洗：标点规范化 + 空白规整 + 纯标点/纯空白段清空。"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    t = _norm_punct(text)
    t = re.sub(r"[ \t　]+", " ", t)
    t = t.strip()
    if not re.search(r"[A-Za-z0-9一-鿿]", t):  # 纯标点/纯空白 → 清空
        return ""
    return t


def _is_noise_line(line: str) -> bool:
    """行是否噪音：通用内容噪音 / OCR 标签行 / 界面水印短独立行。"""
    s = line.strip()
    if not s:
        return True
    if any(w in s for w in _COMMON_NOISE):
        return True
    if any(lbl in s for lbl in _VISUAL_LABELS):
        return True
    if len(s) <= 24:  # 只对短独立行判水印（防误删 GLM 长描述中的内嵌界面词）
        for w in _VISUAL_WATERMARKS:
            if w in s:
                return True
    return False


def clean_transcript_json(json_path: str, out_path: str = "") -> str:
    """转写 json 保结构清洗：逐段/逐句清洗 text，保留结构/时间戳/confidence/review。

    去重：同文本 + 同时间戳 → 删后留前（中英文都去重，属数据重复记录）；
    含中文的段在「不同时间戳」时永不删（教学讲解/重播保留）。
    输出与原 json 同构，可直接 dump 为 *_clean.json。
    """
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"转写 json 不存在: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"转写 json 结构异常: {json_path}")

    def _seg_key(text: str) -> str:
        return re.sub(r"[^a-z0-9一-鿿]", "", (text or "").lower())

    def _has_chinese(text: str) -> bool:
        return any("一" <= ch <= "鿿" for ch in text)

    def _dedup_segments(segs):
        seen = {}
        kept = []
        for seg in segs or []:
            if not isinstance(seg, dict):
                continue
            text = seg.get("text") or ""
            if not isinstance(text, str):
                text = str(text)
            key = _seg_key(text)
            ts = (seg.get("start_ms"), seg.get("end_ms"))
            if key in seen and seen[key][1] == ts:
                continue  # 同文本+同时间戳 → 数据重复记录，删后留前（中英文都去重）
            if _has_chinese(text):
                kept.append(seg)  # 中文教学段永不删（不同时间戳的重播/讲解保留）
                seen[key] = (len(kept) - 1, ts)
                continue
            kept.append(seg)
            seen[key] = (len(kept) - 1, ts)
        return kept

    out = {
        "text": _clean_segment(data.get("text", "")),
        "segments": [],
        "sentences": [],
    }
    for seg in _dedup_segments(data.get("segments")):
        cleaned = _clean_segment(seg.get("text", ""))
        out["segments"].append({
            "text": cleaned,
            "start_ms": seg.get("start_ms"),
            "end_ms": seg.get("end_ms"),
            "confidence": seg.get("confidence"),
            "review": seg.get("review", False),
        })
    for sent in data.get("sentences") or []:
        if not isinstance(sent, dict):
            continue
        out["sentences"].append({
            "text": _clean_segment(sent.get("text", "")),
            "start_ms": sent.get("start_ms"),
            "end_ms": sent.get("end_ms"),
            "confidence": sent.get("confidence"),
        })
    out_path = out_path or os.path.splitext(json_path)[0] + "_clean.json"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"      [清洗] 转写 json → {os.path.basename(out_path)} "
          f"(segments {len(data.get('segments', []))}→{len(out['segments'])})")
    return out_path


def clean_visual_timeline(visual_path: str, out_path: str = "") -> str:
    """画面 txt 切帧清洗：切帧提取时间戳 → 逐帧清洗 → 每帧 `[MM:SS]\\n内容` 保留。

    时间戳由本脚本持有（不进清洗流），永不丢失；清洗只删 OCR 标签行与界面水印独立行。
    """
    if not os.path.isfile(visual_path):
        raise FileNotFoundError(f"视觉 txt 不存在: {visual_path}")
    with open(visual_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    if not raw.strip():
        raise ValueError(f"视觉 txt 为空: {visual_path}")
    parts = _FRAME_RE.split(raw)  # [前导, mm, ss, content, ...]
    frames = []
    for i in range(1, len(parts), 3):
        frames.append((parts[i], parts[i + 1], parts[i + 2]))
    if not frames:
        raise ValueError(f"视觉 txt 无帧标记（期望 '===== 帧 MM:SS (第N/总帧) ====='）: {visual_path}")

    kept = []
    for mm, ss, content in frames:
        lines = []
        for line in content.split("\n"):
            if _is_noise_line(line):
                continue
            cleaned = _clean_segment(line)
            if cleaned:
                lines.append(cleaned)
        if lines:
            kept.append(f"[{int(mm):02d}:{int(ss):02d}]\n" + "\n".join(lines))

    out_path = out_path or os.path.splitext(visual_path)[0] + "_clean.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(kept))
    char_count = sum(len(t) for _, _, t in frames)
    print(f"      [清洗] 视觉 txt → {os.path.basename(out_path)} "
          f"({char_count} 字符, {len(kept)} 帧保留时间戳)")
    return out_path


def clean_plain_text(text: str) -> str:
    """通用文本清洗（图集/文本分支）：标点规范化 + 删空行 + 纯噪音行。"""
    if not text:
        return ""
    lines = []
    for line in text.split("\n"):
        if _is_noise_line(line):
            continue
        cleaned = _clean_segment(line)
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="内置清洗：转写 json / 画面 txt / 通用文本")
    parser.add_argument("path", help="输入文件路径（json 或 txt）")
    parser.add_argument("--output", default="", help="输出路径（默认 *_clean.*）")
    args = parser.parse_args(argv)
    try:
        if args.path.lower().endswith(".json"):
            out = clean_transcript_json(args.path, args.output)
        else:
            out = clean_visual_timeline(args.path, args.output)
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}")
        return 1
    print(f"已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
