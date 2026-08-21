#!/usr/bin/env python3
"""抖音视频 → Markdown 笔记管线

用法:
    python notes_pipeline.py <视频.mp4> <转写.json> <输出笔记.md>

流程:
    读 FunASR 转写JSON(字符级时间戳, ms) → 按标点切句 → 每句取开始时间
    → ffmpeg 抽一帧 → 组装 Markdown(时间戳 + 内嵌截图 + 原文)
"""
import json
import os
import re
import subprocess
import sys

SENT_END = re.compile(r"[。！？!?；;…]")

# 轻口语规范化: 只清理明显感叹/填充词, 不碰正常措辞与生动比喻
FILLERS = [
    r"我的妈呀", r"我的天啊", r"我的天呐", r"我的天", r"我的上帝",
    r"天啊", r"天呐", r"上帝啊", r"哎哟喂", r"哎哟", r"哎呀", r"哦豁",
    r"呃", r"嗯", r"啊这",
]


def normalize_sentence(text: str) -> str:
    t = text
    for f in FILLERS:
        t = re.sub(f, "", t)
    t = re.sub(r"^[,，。；;！？!?、\s]+", "", t)   # 去句首残留标点/空格
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


CORR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corrections.json")


def apply_corrections(text: str) -> str:
    """套用纠错词典(ASR 常见错听, 如 get up → github)。词典文件可随时增补。"""
    if not os.path.exists(CORR_PATH):
        return text
    try:
        with open(CORR_PATH, encoding="utf-8") as f:
            corr = json.load(f)
    except Exception:
        return text
    if not isinstance(corr, dict):
        return text
    for wrong, right in corr.items():
        if wrong.isascii():
            # 英文纠错用 ASCII 边界(而非 \b, 因 \w 会把中文也当单词字符)
            text = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(wrong)}(?![A-Za-z0-9_])",
                right, text, flags=re.IGNORECASE)
        else:
            text = re.sub(re.escape(wrong), right, text)
    return text


def build_char_times(text: str, timestamps: list) -> list:
    """把字符级时间戳对齐到每个字符(非空白字符依次消耗时间戳, 标点沿用前值)。"""
    n = len(timestamps)
    times = []
    k = 0
    for ch in text:
        if k < n:
            entry = timestamps[k]
            # 畸形条目(非 [s,e] 二元组)回退为前一时刻，不崩溃
            if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[0], (int, float)):
                s = entry[0]
            else:
                s = times[-1] if times else 0
            if ch.strip():
                times.append(s)
                k += 1
            else:
                times.append(s if times else 0)
        else:
            times.append(times[-1] if times else 0)
    return times


def split_sentences(text: str, times: list) -> list:
    """按句末标点切句, 返回 [(句子, 开始ms, 结束ms), ...]"""
    sentences = []
    buf = []
    start_ms = None
    for i, ch in enumerate(text):
        if not buf and not ch.strip():
            continue
        if start_ms is None:
            start_ms = times[i] if i < len(times) else 0
        buf.append(ch)
        if SENT_END.match(ch):
            end_ms = times[i] if i < len(times) else start_ms
            sentences.append(("".join(buf).strip(), start_ms, end_ms))
            buf, start_ms = [], None
    if buf:
        sentences.append(("".join(buf).strip(), start_ms, times[-1] if times else 0))
    return sentences


def fmt_ts(ms: int) -> str:
    s = max(0, int(ms // 1000))
    return f"{s // 60:02d}:{s % 60:02d}"


def main():
    if len(sys.argv) < 4:
        print("用法: python notes_pipeline.py <视频.mp4> <转写.json> <输出笔记.md>")
        sys.exit(1)
    video, tjson, out_md = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        with open(tjson, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[ERR] 转写文件不存在: {tjson}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERR] 转写文件不是合法 JSON: {tjson}（{e}）")
        sys.exit(1)
    if not isinstance(data, dict):
        print("[ERR] 转写 JSON 结构异常（应为对象，含 text/sentences 或 timestamps 字段）")
        sys.exit(1)
    text = data.get("text", "") or ""
    sentences_raw = data.get("sentences") or []
    if sentences_raw:
        if not isinstance(sentences_raw, list):
            print("[ERR] 转写 JSON 的 sentences 字段应为数组")
            sys.exit(1)
        # v2 格式(SenseVoice+fsmn-vad): 句子已带时间戳
        try:
            sentences = [(s["text"], s["start_ms"], s["end_ms"]) for s in sentences_raw]
        except (KeyError, TypeError) as e:
            print(f"[ERR] sentences 条目缺少 text/start_ms/end_ms 字段: {e}")
            sys.exit(1)
    else:
        # v1 格式(paraformer 字符级时间戳): 自行切句
        timestamps = data.get("timestamps") or []
        if not isinstance(timestamps, list):
            print("[ERR] 转写 JSON 的 timestamps 字段应为数组")
            sys.exit(1)
        times = build_char_times(text, timestamps)
        sentences = split_sentences(text, times)
    if not text and not sentences:
        print("[ERR] 转写为空")
        sys.exit(1)
    # 先纠错(ASR 错听), 再轻口语规范化
    sentences = [(normalize_sentence(apply_corrections(s)), st, en) for s, st, en in sentences]
    print(f"[INFO] 共 {len(sentences)} 句")

    # 只输出完整转写 md(含时间戳)。抽帧功能已于 2026-08-03 移除(笔记改为 AI 教材,不要图片)。
    out_dir = os.path.dirname(os.path.abspath(out_md))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# 完整转写（原始稿）\n\n")
        for sent, st, en in sentences:
            f.write(f"[{fmt_ts(st)}] {sent}\n")
    print(f"[OK] 原始转写已生成: {out_md}")


if __name__ == "__main__":
    main()
