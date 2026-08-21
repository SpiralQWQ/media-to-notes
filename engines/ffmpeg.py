#!/usr/bin/env python3
"""engines/ffmpeg.py — 媒体底层工具（被 core/engines 单向调用）。

只做 ffmpeg/ffprobe 的命令封装（提音频、探测时长、抽帧），
不含业务逻辑。命令一律带 `-loglevel error`，靠可执行命令不在码。
"""
from __future__ import annotations

import os
import subprocess


def run(cmd, cwd=".", timeout=3600) -> subprocess.CompletedProcess:
    """执行命令，静默捕获输出；Windows 下用 UTF-8 解码防 gbk 崩溃。"""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, timeout=timeout)
        proc.stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
        proc.stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
        return proc
    except subprocess.TimeoutExpired:
        raise


def probe_duration(path: str):
    """ffprobe 探测媒体时长（秒，float）。失败返回 None。"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, timeout=60)
        return float(r.stdout.decode("utf-8", errors="replace").strip())
    except Exception:
        return None


def extract_audio(video: str, out_wav: str, sample_rate: int = 16000) -> bool:
    """ffmpeg 从视频/音频提 pcm_s16le 单声道 wav（ASR 输入）。

    若视频 AAC 流含损坏包部分，ffmpeg 可能返回非 0 但主体已提取——
    以产物文件是否生成且非空为准，不因 returncode 误判失败。
    """
    if not os.path.exists(video):
        return False
    rr = run(["ffmpeg", "-y", "-loglevel", "error", "-i", video,
              "-vn", "-acodec", "pcm_s16le", "-ar", str(sample_rate),
              "-ac", "1", out_wav], timeout=3600)
    return os.path.exists(out_wav) and os.path.getsize(out_wav) > 0