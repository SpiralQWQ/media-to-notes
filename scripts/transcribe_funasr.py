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


def apply_corrections(text: str, corr: dict) -> str:
    for wrong, right in corr.items():
        if wrong.isascii():
            text = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(wrong)}(?![A-Za-z0-9_])",
                right, text, flags=re.IGNORECASE)
        else:
            text = re.sub(re.escape(wrong), right, text)
    return text


def merge_spaced_letters(t: str) -> str:
    """SenseVoice 会把英文拆成单字母(如 "w s l"), 合并连续单字母为词(如 "wsl")。"""
    return re.sub(
        r"(?<!\w)((?:[a-zA-Z] )+[a-zA-Z])(?!\w)",
        lambda m: m.group(1).replace(" ", ""),
        t,
    )


def clean_sensevoice(t: str) -> str:
    # 去 <|zh|><|NEUTRAL|> 等标签(容忍内部被拆成带空格的 < | zh | >)
    t = re.sub(r"<\s*\|\s*[^|]+\s*\|\s*>", "", t)
    t = merge_spaced_letters(t)
    t = re.sub(r"([。，！？、；：])\1+", r"\1", t)   # 折叠重复标点 ，， → ，
    return t.strip()


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


def transcribe(audio_path: str, out_json: str) -> None:
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

    # 1) fsmn-vad 切段拿时间戳(长音频分块返回, 拼接所有块)
    vad = AutoModel(model="fsmn-vad", disable_update=True, device="cpu")
    vres = vad.generate(input=audio_path)
    seg_times = []
    for r in vres:
        seg_times.extend((r or {}).get("value", []))

    # 2) SenseVoiceSmall(不带 vad, 逐段喂) + ct-punc 补标点
    asr = AutoModel(model="iic/SenseVoiceSmall", punc_model="ct-punc",
                    disable_update=True, device="cpu")

    try:
        audio, sr = sf.read(audio_path, dtype="float32")
    except Exception as e:
        print(f"[ERR] 音频读取失败（文件损坏或非音频格式）: {e}")
        sys.exit(1)
    sr = int(sr)

    segments = []
    for s, e in seg_times:
        i0, i1 = int(s * sr / 1000), int(e * sr / 1000)
        seg_audio = audio[i0:i1]
        if len(seg_audio) < sr // 2:      # <0.5s 的碎片跳过
            continue
        try:
            res = asr.generate(input=seg_audio, batch_size_s=60,
                               language="auto", use_itn=True)
        except Exception as exc:
            print(f"  [WARN] 段 {s}-{e} 转写失败: {exc}")
            continue
        text = clean_sensevoice(res[0].get("text", "")) if res else ""
        if text:
            segments.append({"text": text, "start_ms": s, "end_ms": e})

    # 3) 句级拆分(段内按标点)
    sentences = []
    for seg in segments:
        sentences.extend(split_sentences_in_segment(seg["text"], seg["start_ms"], seg["end_ms"]))

    # 拼接全文（VAD 段文本顺序连接，供输出/纠错/打印使用）
    full = "".join(seg["text"] for seg in segments)

    # 套用 ASR 纠错词典（corrections.json，若存在）
    corr = _load_corrections()
    if corr:
        full = apply_corrections(full, corr)
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
