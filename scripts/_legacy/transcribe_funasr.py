#!/usr/bin/env python3
"""FunASR 高质量转写 v3: fsmn-vad 切段 → 逐段 SenseVoiceSmall 转写

为何逐段: SenseVoice 一次性调用会合并整段文本、拿不到时间戳;
          先 VAD 切出说话段(带毫秒时间), 再对每段单独转写, 段=时间戳。

输出 JSON: {text, segments:[{text,start_ms,end_ms}], sentences:[{text,start_ms,end_ms}]}
用法: python transcribe_funasr.py <音频.wav> [输出.json]
"""
import json
import os
import re
import sys
import time

# Windows 控制台 UTF-8 输出（防 gbk 编码崩溃，尤其是中文/进度条混排）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _fmt_remain(sec: float) -> str:
    """剩余时间估算格式化。"""
    sec = max(0, int(sec))
    if sec >= 3600:
        return f"{sec // 3600}小时{sec % 3600 // 60}分"
    if sec >= 60:
        return f"{sec // 60}分{sec % 60:02d}秒"
    return f"{sec}秒"


def _progress_bar(idx: int, total: int, pct: int, t0: float, label: str = "转写",
                  width: int = 24) -> str:
    """\r 单行刷新进度条：百分比条 + 第N/总 + 剩余时间估算。
    用 ASCII 字符(=/-)避免 gbk 终端 UnicodeEncodeError。"""
    filled = int(width * pct / 100)
    bar = "=" * filled + "-" * (width - filled)
    # 剩余时间 = 已用时间 / 已做比例 × 剩余比例（外推）
    elapsed = time.time() - t0
    remain = elapsed / pct * (100 - pct) if pct > 0 else 0
    return f"  [{label}] [{bar}] {pct:3d}% | {idx}/{total} | 剩余{_fmt_remain(remain)}"


def _trim_silence_silero(audio_path: str, out_path: str, min_speech_ratio: float = 0.02) -> str:
    """VAD 静音预过滤（补丁A）：用 silero-vad 裁剪纯静音头尾，减少幻觉词+省 ASR 算力。

    流程：读 wav → silero-vad 检测语音段 → 若有语音且首/尾存在长静音 → 裁剪为精简 wav。
    返回裁剪后的 wav 路径；无需裁剪时返回原路径。
    """
    try:
        import torch
        import soundfile as sf
        import numpy as np
        # 静音占比低于阈值（如 2%）说明几乎没语音 → 不裁剪（防误删整段讲课停顿）
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad', model='silero_vad',
            trust_repo=True, source='github')
        get_speech_timestamps = utils[0]
    except Exception as e:
        print(f"      [VAD] silero-vad 不可用（{e}），跳过静音预过滤")
        return audio_path
    try:
        audio, sr = sf.read(audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        sr = int(sr)
        if len(audio) < sr:  # <1s 不做
            return audio_path
        ts = get_speech_timestamps(torch.from_numpy(audio), model, sampling_rate=sr)
        if not ts:
            return audio_path  # 检测不到语音 → 不动（可能全是安静讲课，交给 fsmn-vad）
        # 计算语音总时长占比（silero 的 start/end 是样本索引，需 /sr 转秒）
        speech_s = sum((t['end'] - t['start']) / sr for t in ts)
        total_s = len(audio) / sr
        ratio = speech_s / total_s if total_s else 0
        if ratio < min_speech_ratio:
            return audio_path  # 语音太少，裁剪无意义
        # 首尾静音：第一段语音前 / 最后一段语音后
        head_trim = ts[0]['start'] / sr      # 秒
        tail_keep = ts[-1]['end'] / sr       # 秒
        # 只有首尾静音 >1.5s 才值得裁剪（否则裁剪反而引入切点噪音）
        if head_trim < 1.5 and (len(audio) / sr - tail_keep) < 1.5:
            return audio_path
        start_s = max(0, head_trim - 0.2)    # 留 0.2s 缓冲
        end_s = min(len(audio) / sr, tail_keep + 0.2)
        trimmed = audio[int(start_s * sr):int(end_s * sr)]
        sf.write(out_path, trimmed, sr)
        print(f"      [VAD] 静音预过滤: {len(audio)/sr:.1f}s → {len(trimmed)/sr:.1f}s (裁掉首尾静音)")
        return out_path
    except Exception as e:
        print(f"      [VAD] 静音预过滤失败（{e}），用原音频")
        return audio_path


def _load_corrections() -> dict:
    """加载同目录 corrections.json（ASR 纠错词典，如 "get up" → "github"）。"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corrections.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _hotwords_from_corrections(corr: dict) -> list:
    """从纠错词典提取"目标词"作为前置热词（模型级解码偏置，提升术语识别率）。

    热词 = corrections 里所有"纠正后"的值（如 "github"/"PowerShell"/"AI agent"）。
    转写前喂给 generate(hotword=...)，让 ASR 解码期优先往这些词上猜，
    比"事后替换"更准（源头就识别对，而非错后再改）。
    """
    words = set()
    for wrong, right in corr.items():
        # 只取纠正后的实义词（>1 字符，非纯符号），排除空/数字
        for w in re.split(r"[\s,，。；;]", right):
            w = w.strip()
            if len(w) > 1 and not w.isdigit() and w not in words:
                words.add(w)
    return sorted(words)


def apply_corrections(text: str, corr: dict) -> str:
    for wrong, right in corr.items():
        if wrong.isascii():
            text = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(wrong)}(?![A-Za-z0-9_])",
                right, text, flags=re.IGNORECASE)
        else:
            text = re.sub(re.escape(wrong), right, text)
    return text


def _pinyin_phonemes(text: str) -> list:
    """把文本转拼音音素序列（中文按字转拼音，英文按原词转小写）。
    供音素级热词纠错用。返回 [(原文token, 音素)] 列表。"""
    try:
        from pypinyin import lazy_pinyin
        tokens = re.findall(r"[一-鿿]+|[A-Za-z]+", text)
        result = []
        for tok in tokens:
            if re.fullmatch(r"[一-鿿]+", tok):
                # 中文：逐字转拼音拼接
                phones = "".join(lazy_pinyin(tok))
            else:
                phones = tok.lower()
            result.append((tok, phones))
        return result
    except ImportError:
        return [(text, text.lower())]


def phoneme_hotword_correct(text: str, corr: dict, threshold: float = 0.95) -> str:
    """热词后处理纠错层（补丁B）：中文同音字纠错，补 apply_corrections 精确替换的盲区。

    场景：ASR 把目标词（corr 的值）听成同音/近音字，精确词典匹配不到时，
    用拼音高度相似且字数相同来纠正（如 "辛福"→"幸福"、"邹喻"→"周瑜"）。
    实现：在中文串里按目标词长度做滑动窗口，比较窗口拼音与目标拼音。
    英文目标词由 apply_corrections 精确替换，本层不碰（避免 I→AI 这类误伤）。
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return text
    # 只取含中文的目标词（>1 字符，非纯数字）
    cn_targets = []
    for _, right in corr.items():
        for w in re.split(r"[\s,，。；;]", right):
            w = w.strip()
            if len(w) > 1 and not w.isdigit() and re.search(r"[一-鿿]", w) and w not in cn_targets:
                cn_targets.append(w)
    if not cn_targets:
        return text

    def _cn_py(s: str) -> str:
        """纯中文串 → 拼音串。"""
        ph = _pinyin_phonemes(s)
        return "".join(p for _, p in ph) if ph else s

    # 每个中文目标词：在文本中文片段里滑动窗口找同音
    for tgt in cn_targets:
        tgt_py = _cn_py(tgt)
        if not tgt_py:
            continue
        n = len(tgt)
        for m in list(re.finditer(r"[一-鿿]+", text)):
            frag_all = m.group(0)
            # 在 frag 里按长度 n 滑动窗口
            for start in range(0, len(frag_all) - n + 1):
                window = frag_all[start:start + n]
                if window == tgt:
                    continue
                if fuzz.ratio(_cn_py(window), tgt_py) >= threshold * 100:
                    abs_pos = m.start() + start
                    text = text[:abs_pos] + tgt + text[abs_pos + n:]
                    break
    return text


def _normalize_english_case(text: str, corr: dict) -> str:
    """英文专名大小写归一（补丁B增强）：把词典目标词的英文词，大小写变体归一。

    例：词典目标 "PowerShell"，文本出现 "Powershell"/"POWERSHELL" → 统一为 "PowerShell"。
    只在目标词是英文且长度>2 时启用（短词如 "AI" 不动，防误伤）。
    """
    # 收集英文目标词（长度>2）
    en_targets = []
    for _, right in corr.items():
        for w in re.split(r"[\s,，。；;]", right):
            w = w.strip()
            if len(w) > 2 and w.isascii() and not w.isdigit() and w not in en_targets:
                en_targets.append(w)
    for tgt in en_targets:
        pattern = re.compile(re.escape(tgt), re.IGNORECASE)
        # 替换所有大小写变体为目标词（确保不是目标词本身则替换）
        text = pattern.sub(tgt, text)
    return text


def merge_spaced_letters(t: str) -> str:
    """SenseVoice 会把英文拆成单字母(如 "w s l"), 合并连续单字母为词(如 "wsl")。"""
    t = re.sub(
        r"(?<!\w)((?:[a-zA-Z] )+[a-zA-Z])(?!\w)",
        lambda m: m.group(1).replace(" ", ""),
        t,
    )
    # 增强：处理"大写单字母 + 空格 + 小写词"的音节级拆分（如 "O kay"→"Okay"）
    # 用精确字典，避免误合并正常冠词（"a few"/"A few" 不处理）
    t = merge_sensevoice_splits(t)
    return t


# SenseVoice 音节级拆分的常见词映射：拆开形式 → 原词
_SENSEVOICE_SPLITS = {
    "O kay": "Okay", "L ike": "Like", "B ut": "But", "T he": "The",
    "S o": "So", "W e": "We", "A nd": "And", "I t": "It",
    "Y ou": "You", "H e": "He", "S he": "She", "W as": "Was",
    "T hat": "That", "T his": "This", "A re": "Are", "W hat": "What",
    "W here": "Where", "W hen": "When", "N ot": "Not", "N ow": "Now",
    "F or": "For", "W ith": "With", "W ill": "Will", "W ould": "Would",
    "C an": "Can", "D o": "Do", "D id": "Did", "H as": "Has",
    "H ave": "Have", "E dit": "Edit", "W hy": "Why", "H ow": "How",
    "D uring": "During", "A bout": "About", "A fter": "After",
    "B efore": "Before", "B etween": "Between", "E very": "Every",
    "A nother": "Another", "A ny": "Any", "O ther": "Other",
    "S ome": "Some", "W ords": "Words", "S peech": "Speech",
    "S ystem": "System", "S equence": "Sequence", "P robability": "Probability",
    # 补充（抖音口语测试发现）
    "H ey": "Hey", "Y eah": "Yeah", "Y ay": "Yay", "Y es": "Yes",
    "O ht": "Oh", "T heir": "Their", "T here": "There", "T hen": "Then",
    "T han": "Than", "M aybe": "Maybe", "A lways": "Always",
    "A wesome": "Awesome", "S tuff": "Stuff", "W ays": "Ways",
    "G reat": "Great", "R eally": "Really", "K now": "Know",
    "K ind": "Kind", "K eep": "Keep",
}


def merge_sensevoice_splits(t: str) -> str:
    """合并 SenseVoice 音节级拆分的常见词（"O kay"→"Okay"）。
    仅精确匹配字典，不碰正常冠词（a few / A few 保持原样）。"""
    for split, merged in _SENSEVOICE_SPLITS.items():
        t = re.sub(rf"(?<!\w){re.escape(split)}(?!\w)", merged, t)
    return t


def clean_sensevoice(t: str) -> str:
    # 去 <|zh|><|NEUTRAL|> 等标签(容忍内部被拆成带空格的 < | zh | >)
    t = re.sub(r"<\s*\|\s*[^|]+\s*\|\s*>", "", t)
    t = merge_spaced_letters(t)
    t = collapse_filler_repeats(t)
    t = re.sub(r"([。，！？、；：])\1+", r"\1", t)   # 折叠重复标点 ，， → ，
    return t.strip()


# ── 口语规范化增强（v1.1）──
# 无意义填充重复（口头禅/卡壳）→ 折叠；有实义的重复（强调语气）→ 保留
_FILLER_REPEATS = (
    # 中文语气词/填充词重复（呃呃呃/嗯嗯嗯/那个那个）
    r"([呃嗯啊哦噢唉呀哦])\1{2,}",
    # 英文连接词/语气词重复（and and and / the the the / uh uh uh / um um um）
    r"\b(and|the|uh|um|er|well|so)\b(?:[ ,]+\1\b){2,}",
    # 中文"那个/这个"连续重复
    r"((?:那个|这个)[，, ]*){3,}",
)


def collapse_filler_repeats(t: str) -> str:
    """折叠无意义填充重复（口头禅），保留有实义的强调重复（重要！重要！）。
    仅处理连接词/语气词/填充词的连续重复，实义词（重要/记住/重点）不受影响。
    """
    for pat in _FILLER_REPEATS:
        t = re.sub(pat, lambda m: _collapse_filler(m), t, flags=re.IGNORECASE)
    return t


def _collapse_filler(m) -> str:
    """填充词重复折叠：保留一次（呃呃呃 → 呃）。"""
    s = m.group(0)
    # 取首个词，去重复
    words = re.findall(r"[一-鿿]|[A-Za-z]+", s)
    if not words:
        return s
    return words[0]


def split_sentences_in_segment(text: str, start_ms: int, end_ms: int) -> list:
    """段内按标点切句, 时间按字符占比大致分配。"""
    parts = [p.strip() for p in re.split(r"(?<=[。！？!?；;…])", text) if p.strip()]
    n = max(len(text), 1)
    acc = 0
    out = []
    for p in parts:
        s = start_ms + int((end_ms - start_ms) * acc / n)
        acc += len(p)
        e = start_ms + int((end_ms - start_ms) * acc / n)
        out.append({"text": p, "start_ms": s, "end_ms": max(e, s)})
    return out


# ── 启发式置信度估计（SenseVoice 不输出 logprob，用文本特征推算）──
# 低置信信号：过短碎片 / 连续孤立单字母（英文粘连未合并）/ 重复填充
_LOW_CONF_MARKS = (
    r"<\|[^|]*\|>",                          # 残留标签
    r"\b[a-zA-Z]\s+[a-zA-Z]\b",              # 连续两个孤立单字母（粘连残留，如 "w s l"）
)

# 补丁C：置信度低于此阈值 → 段标记 review:true（提示人工复核）
REVIEW_CONF_THRESHOLD = 0.5


def estimate_confidence(text: str, dur_ms: int) -> float:
    """基于文本特征估计段级置信度(0~1)。无真实 logprob 时的启发式替代。"""
    if not text:
        return 0.0
    # 特征1: 时长合理性（<0.5s 且无字 → 碎片）
    t = text.strip()
    n_chars = len(re.sub(r"\s", "", t))
    if dur_ms > 0 and n_chars == 0:
        return 0.1
    if n_chars <= 2:
        return 0.2
    # 特征2: 残留标签/孤立单字母（英文粘连未合并 → 听错风险高）
    if any(re.search(p, t) for p in _LOW_CONF_MARKS):
        return 0.35
    # 特征3: 重复填充（"呃呃呃" / "and and and"）
    if re.search(r"(\b\w+\b)\s+\1\s+\1", t, re.IGNORECASE):
        return 0.5
    # 特征4: 实义词比例（全是连接词 → 可疑）
    words = re.findall(r"[A-Za-z]{3,}|[一-鿿]{2,}", t)
    if not words:
        return 0.4
    # 默认: 正常文本给 0.85~0.95（越长越可信）
    base = 0.85
    if n_chars >= 50:
        base = 0.95
    elif n_chars >= 20:
        base = 0.90
    return base


def transcribe(audio_path: str, out_json: str, hotwords: list = None) -> None:
    if not os.path.exists(audio_path):
        print(f"[ERR] 音频文件不存在: {audio_path}")
        sys.exit(1)
    if os.path.getsize(audio_path) == 0:
        print(f"[ERR] 音频文件为空: {audio_path}")
        sys.exit(1)
    try:
        from funasr import AutoModel
        import soundfile as sf
    except ImportError as e:
        print(f"[ERR] 缺少 FunASR/soundfile 依赖，请按 requirements.txt 安装（或为 DD_ASR_PY 指定已装好的解释器）: {e}")
        sys.exit(1)

    # 0) 前置热词（模型级解码偏置）——corrections 目标词喂给 ASR，源头识别更准
    if hotwords is None:
        hotwords = _hotwords_from_corrections(_load_corrections())
    if hotwords:
        print(f"[HOTWORDS] 前置热词注入 {len(hotwords)} 个: {', '.join(hotwords[:10])}{'...' if len(hotwords) > 10 else ''}")

    # 1) VAD 静音预过滤（补丁A）：裁剪纯静音头尾，减少幻觉词+省算力（可选，默认自动）
    trim_path = _trim_silence_silero(audio_path, os.path.splitext(audio_path)[0] + "_vadtrim.wav")

    # 2) fsmn-vad 切段拿时间戳(长音频分块返回, 拼接所有块)——用裁剪后的音频
    vad = AutoModel(model="fsmn-vad", disable_update=True, device="cpu")
    vres = vad.generate(input=trim_path)
    seg_times = []
    for r in vres:
        seg_times.extend((r or {}).get("value", []))

    # 3) SenseVoiceSmall(不带 vad, 逐段喂) + ct-punc 补标点 + 前置热词
    asr = AutoModel(model="iic/SenseVoiceSmall", punc_model="ct-punc",
                    disable_update=True, device="cpu")

    try:
        audio, sr = sf.read(trim_path, dtype="float32")
    except Exception as e:
        print(f"[ERR] 音频读取失败（文件损坏或非音频格式）: {e}")
        sys.exit(1)
    sr = int(sr)

    segments = []
    total_seg = len(seg_times)
    total_dur_ms = seg_times[-1][1] if seg_times else 1
    _t0 = time.time()
    for idx, (s, e) in enumerate(seg_times, 1):
        # 实时进度条：百分比 + 第N/总段 + 剩余时间估算（\r 单行刷新）
        pct = min(100, int(e / total_dur_ms * 100)) if total_dur_ms else 0
        print(_progress_bar(idx, total_seg, pct, _t0), end="\r", flush=True)
        i0, i1 = int(s * sr / 1000), int(e * sr / 1000)
        seg_audio = audio[i0:i1]
        if len(seg_audio) < sr // 2:      # <0.5s 的碎片跳过
            continue
        try:
            # 有热词则传入 hotword（模型级解码偏置），否则正常转写
            if hotwords:
                res = asr.generate(input=seg_audio, batch_size_s=60,
                                   language="auto", use_itn=True, hotword=hotwords)
            else:
                res = asr.generate(input=seg_audio, batch_size_s=60,
                                   language="auto", use_itn=True)
        except Exception as exc:
            print(f"\n  [WARN] 段 {s}-{e} 转写失败: {exc}")
            continue
        text = clean_sensevoice(res[0].get("text", "")) if res else ""
        if text:
            conf = round(estimate_confidence(text, e - s), 2)
            segments.append({
                "text": text, "start_ms": s, "end_ms": e,
                "confidence": conf,
                # 补丁C：低置信段标记复核（conf<0.5 → 笔记提示人工复核）
                "review": conf < REVIEW_CONF_THRESHOLD,
            })
    print()  # 进度条换行结束，后续输出从新行开始

    # 3) 句级拆分(段内按标点) + 继承段置信度
    sentences = []
    for seg in segments:
        for s in split_sentences_in_segment(seg["text"], seg["start_ms"], seg["end_ms"]):
            s["confidence"] = seg["confidence"]
            sentences.append(s)

    # 拼接全文（VAD 段文本顺序连接，供输出/纠错/打印使用）
    full = "".join(seg["text"] for seg in segments)

    # 套用 ASR 纠错词典（corrections.json，若存在）——精确替换 + 音素同音纠错 + 英文大小写归一
    corr = _load_corrections()
    if corr:
        full = apply_corrections(full, corr)
        full = phoneme_hotword_correct(full, corr)
        full = _normalize_english_case(full, corr)
        for seg in segments:
            seg["text"] = apply_corrections(seg["text"], corr)
        for s in sentences:
            s["text"] = apply_corrections(s["text"], corr)

    out = {"text": full, "segments": segments, "sentences": sentences}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[OK] 转写完成: {len(segments)} 段, {len(sentences)} 句 -> {out_json}")
    print(f"[TEXT] {full[:150]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python transcribe_funasr.py <音频.wav> [输出.json]")
        sys.exit(1)
    audio = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else audio + ".json"
    transcribe(audio, out)
