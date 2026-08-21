#!/usr/bin/env python3
"""assemble_md.py — 视频线组装：转写 json + visual txt → 半成品 md。

背景（重构项3，接口边界铁律：谁生产 md 谁组装）：
  视频线产物是「转写json + 逐帧视觉txt」，不是 md。_md_rewrite_tools 只收"清洗后 md"。
  本脚本把二者拼成半成品 md（正文 + 画面信息附录），供 text-cleaning-engine 清洗后
  喂给 _md_rewrite_tools。

不侵入 course_video_to_notes.py 主流程；老"交给 Claude 生成"流程完全不受影响。

用法:
  python assemble_md.py <转写.json> [--visual 视觉.txt] [--title 标题] [--output 输出.md]
    --output 缺省 → 与 json 同名的 .md（如 英文测试.json → 英文测试.md）
"""
from __future__ import annotations

import argparse
import json
import os
import re


def assemble(json_path: str, visual_path: str = "", title: str = "") -> str:
    """组装转写 json + visual txt → 半成品 md 文本。

    Args:
        json_path: 转写 json（须含 text 字段或为字符串）。
        visual_path: 逐帧视觉 txt（可选；不存在则跳过视觉附录）。
        title: 文档标题（可选）。

    Returns:
        str 半成品 md。
    """
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"转写 json 不存在: {json_path}")
    with open(json_path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    if isinstance(data, dict):
        text = data.get("text", "")
    elif isinstance(data, str):
        text = data
    else:
        raise ValueError("转写 json 结构异常（需含 text 字段或为字符串）")
    text = (text or "").strip()
    if not text:
        raise ValueError(f"转写 json 无正文内容: {json_path}")

    parts: list = []
    if title:
        parts.append(f"# {title}")
    parts.append(text)
    if visual_path and os.path.isfile(visual_path):
        with open(visual_path, encoding="utf-8", errors="replace") as f:
            vtxt = f.read().strip()
        if vtxt:
            parts.append("## 画面信息（OCR/GLM 附录）")
            parts.append(vtxt)
    return "\n\n".join(parts)


def _fmt_ts(ms: float) -> str:
    """毫秒 → [MM:SS]。"""
    ms = max(0, int(ms))
    return f"[{ms // 60000:02d}:{ms % 60000 // 1000:02d}]"


def assemble_timeline(clean_json: str, visual_clean: str = "", title: str = "") -> str:
    """清洗后 json + 清洗后视觉 → 带时间锚的半成品 md。

    转写正文取 clean_json.sentences（带 start_ms），每句前缀 [MM:SS]；
    画面附录取 visual_clean.txt（已带 [MM:SS]），原样整块附上。
    两者时间戳同格式，Claude 可据此把"台词"与"画面"对齐。
    """
    if not os.path.isfile(clean_json):
        raise FileNotFoundError(f"清洗后 json 不存在: {clean_json}")
    with open(clean_json, encoding="utf-8") as f:
        data = json.load(f)
    sents = data.get("sentences", []) if isinstance(data, dict) else []
    if not isinstance(sents, list):
        sents = []
    parts: list = []
    if title:
        parts.append(f"# {title}")
    parts.append("## 转写（带时间锚）")
    lines = []
    for s in sents:
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"{_fmt_ts(s.get('start_ms') or 0)} {text}")
    if not lines:
        raise ValueError(f"清洗后 json 无有效句子: {clean_json}")
    parts.append("\n".join(lines))
    if visual_clean and os.path.isfile(visual_clean):
        with open(visual_clean, encoding="utf-8", errors="replace") as f:
            vtxt = f.read().strip()
        if vtxt:
            parts.append("## 画面信息（OCR/GLM 附录 · 带时间锚）")
            parts.append(vtxt)
    return "\n\n".join(parts)


def assemble_interleaved(clean_json: str, visual_clean: str = "", title: str = "") -> str:
    """按时间轴交错：转写句子 + 画面帧按时间戳混排，不分两段。

    避免"画面信息在最后被忽略"的问题（两段分开时，转写太长 → 画面在末尾被忽略）。
    每个时间点同时显示转写和画面，Claude 一眼对应，不会漏。
    输出格式：按时间升序，同时间先转写后画面；每行前缀 [MM:SS] + 🎤/🖼 区分类型。
    """
    if not os.path.isfile(clean_json):
        raise FileNotFoundError(f"清洗后 json 不存在: {clean_json}")

    # 1) 读转写句子 → [(seconds, type, text)]
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
        ms = s.get("start_ms") or 0
        events.append((int(ms) / 1000, "transcript", text))

    if not events:
        raise ValueError(f"清洗后 json 无有效句子: {clean_json}")

    # 2) 读画面帧 → 按 [MM:SS] 切分 → [(seconds, type, text)]
    if visual_clean and os.path.isfile(visual_clean):
        with open(visual_clean, encoding="utf-8", errors="replace") as f:
            vtxt = f.read().strip()
        if vtxt:
            # 支持 [MM:SS] 和 [MM:SS~MM:SS] 两种格式（都取开始时间）
            v_events = []
            for block in re.split(r"\n(?=\[\d{2}:\d{2})", vtxt):
                block = block.strip()
                if not block:
                    continue
                m = re.match(r"\[(\d{2}):(\d{2})", block)
                if m:
                    sec = int(m.group(1)) * 60 + int(m.group(2))
                    content = block[m.end():].strip()
                    if content:
                        v_events.append((sec, "visual", block))
            events.extend(v_events)

    # 3) 按时间排序（同秒先转写后画面，保持阅读顺序）
    events.sort(key=lambda e: (e[0], 0 if e[1] == "transcript" else 1))

    # 4) 输出
    parts = []
    if title:
        parts.append(f"# {title}")
    parts.append("## 转写 + 画面（时间轴交错）")
    lines = []
    for sec, typ, text in events:
        ts = f"[{int(sec) // 60:02d}:{int(sec) % 60:02d}]"
        tag = "🎤" if typ == "transcript" else "🖼"
        # 画面块可能多行，缩进处理
        if typ == "visual":
            # 画面块可能多行（含时间戳行 + 内容），在首行前加 🖼 标记
            lines.append(f"🖼 {text.lstrip()}")
        else:
            lines.append(f"{ts} {tag} {text}")
    parts.append("\n".join(lines))
    return "\n\n".join(parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="转写 json + visual txt → 半成品 md")
    parser.add_argument("json", help="转写 json 路径（--timeline 时传清洗后 json）")
    parser.add_argument("--visual", default="", help="视觉 txt 路径（可选）")
    parser.add_argument("--title", default="", help="文档标题（可选）")
    parser.add_argument("--output", default="", help="输出 md 路径（默认 json 同名 .md）")
    parser.add_argument("--timeline", action="store_true", help="时间锚定模式：转写句子带 [MM:SS]")
    parser.add_argument("--interleaved", action="store_true", help="交错模式：转写+画面按时间轴混排（不分两段）")
    args = parser.parse_args(argv)

    try:
        if args.interleaved:
            md = assemble_interleaved(args.json, args.visual, args.title)
        elif args.timeline:
            md = assemble_timeline(args.json, args.visual, args.title)
        else:
            md = assemble(args.json, args.visual, args.title)
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}")
        return 1

    out = args.output or os.path.splitext(args.json)[0] + ".md"
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"已组装: {out}（{len(md)} 字符）")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
