#!/usr/bin/env python3
"""视频关键帧视觉分析：抽帧 → OCR(默认,多帧上限1200) + 可选 GLM 视觉理解。

用法: python video_frames_ocr.py <视频.mp4> [--mode fixed|scene] [--interval 1] [--glm yes] [--out 输出.txt]

- 抽帧模式:
  - fixed(默认): 每 --interval 秒抽一帧(默认1s, 无上限)
  - scene(进阶): 画面变化才抽帧(场景切换检测, 更省不冗余), 附最大间隔兜底
- OCR: 默认对每帧识别画面文字(免费, RapidOCR 轻量引擎)
- GLM: --glm yes 时再对每帧调用 glm-4.6v-flashx 描述画面含义(花钱,需先征得用户同意)
"""
import argparse
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GLM_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glm_vision.py")
MAX_FRAMES = 1200  # 单视频抽帧上限，防超长视频耗尽 CPU/内存/超时


def fmt_ts(sec: float) -> str:
    s = int(sec)
    return f"{s // 60:02d}:{s % 60:02d}"


def extract_fixed(video, interval, tmpdir):
    """固定间隔抽帧: 每 interval 秒一帧(上限 MAX_FRAMES)"""
    if interval <= 0:
        return []
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video],
            capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    try:
        dur = float(r.stdout.strip() or 0)
    except ValueError:
        return []
    frames = []
    t = 0.0
    while t < dur and len(frames) < MAX_FRAMES:
        out = os.path.join(tmpdir, f"f{int(t * 1000):07d}.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}",
                 "-i", video, "-frames:v", "1", "-q:v", "3", out],
                capture_output=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if os.path.exists(out):
            frames.append((t, out))
        t += interval
    return frames


def extract_scene(video, threshold, max_interval, tmpdir):
    """进阶: 场景切换检测抽帧(画面变化才抽, 附最大间隔兜底防漏慢变化)"""
    try:
        import cv2
    except ImportError:
        sys.exit("[错误] 未安装 opencv-python。--mode scene 场景检测抽帧需要它，请先 pip install opencv-python（或 pip install -r requirements.txt）")
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    prev = None
    last_shot_t = -999.0
    idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            t = idx / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean = 0.0
            if prev is not None:
                mean = float(cv2.absdiff(prev, gray).mean())
            if prev is None or mean > threshold or (t - last_shot_t) >= max_interval:
                out = os.path.join(tmpdir, f"f{int(t * 1000):07d}.jpg")
                cv2.imwrite(out, frame)
                frames.append((t, out))
                last_shot_t = t
            prev = gray
            idx += 1
    finally:
        cap.release()
    return frames


def select_key_frames(frames, threshold=18.0, max_interval=5.0):
    """在已抽帧里选"关键帧"(画面变化大 或 超过最大间隔兜底) —— GLM 只分析这些"""
    try:
        import cv2
    except ImportError:
        sys.exit("[错误] 未安装 opencv-python。--glm yes 的关键帧分析需要它，请先 pip install opencv-python（或 pip install -r requirements.txt）")
    selected = []
    last_t = -999.0
    prev_gray = None
    for i, (t, fp) in enumerate(frames):
        img = cv2.imread(fp)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        diff = 0.0
        if prev_gray is not None:
            diff = float(cv2.absdiff(prev_gray, gray).mean())
        if prev_gray is None or diff > threshold or (t - last_t) >= max_interval:
            selected.append(i)
            last_t = t
        prev_gray = gray
    return selected


def main():
    parser = argparse.ArgumentParser(description="视频关键帧视觉分析(OCR+可选GLM)")
    parser.add_argument("video")
    parser.add_argument("--mode", choices=["fixed", "scene"], default="fixed",
                        help="fixed=每N秒1帧(默认); scene=场景变化才抽帧(进阶,更省不冗余)")
    parser.add_argument("--interval", type=float, default=1.0, help="fixed模式每N秒抽一帧(默认1)")
    parser.add_argument("--threshold", type=float, default=18.0, help="scene模式画面差异阈值(默认18)")
    parser.add_argument("--max-interval", type=float, default=5.0, help="scene模式最大间隔兜底(秒)")
    parser.add_argument("--glm", choices=["yes", "no"], default="no", help="是否开启GLM视觉理解")
    parser.add_argument("--out")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"视频不存在: {args.video}")
    if args.interval <= 0:
        sys.exit("--interval 必须为正数（单位：秒）")

    tmpdir = tempfile.mkdtemp(prefix="vf_")
    atexit.register(shutil.rmtree, tmpdir, ignore_errors=True)  # 任何退出路径（含 sys.exit/异常）都清理临时帧
    if args.mode == "scene":
        frames = extract_scene(args.video, args.threshold, args.max_interval, tmpdir)
        print(f"[INFO] 场景检测抽帧: {len(frames)} 帧 (阈值{args.threshold}, 最大间隔{args.max_interval}s)")
    else:
        frames = extract_fixed(args.video, args.interval, tmpdir)
        print(f"[INFO] 固定间隔抽帧: {len(frames)} 帧 (每{args.interval}秒1帧, 上限{MAX_FRAMES})")
        if len(frames) >= MAX_FRAMES:
            print(f"[WARN] 已达抽帧上限 {MAX_FRAMES}，超长视频画面可能被截断")

    if not frames:
        sys.exit("未抽到帧")

    # OCR 全部帧(免费; 视频帧 OCR 用 RapidOCR 轻量引擎)
    # 限线程（官方 config 参数，比环境变量有效）：实测 2 线程反而比默认 95 线程快 33%，且 CPU 占用大降
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        sys.exit("[错误] 未安装 rapidocr-onnxruntime。视频帧 OCR 需要它，请先 pip install rapidocr-onnxruntime（或 pip install -r requirements.txt）")
    try:
        ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    except TypeError:  # 老版本不支持该参数，退化为默认
        ocr = RapidOCR()
    sections = []
    for i, (ts, fp) in enumerate(frames):
        try:
            result, _ = ocr(fp)
            text = "\n".join(item[1] for item in (result or []))
        except Exception as e:
            print(f"  [WARN] 帧 {fmt_ts(ts)} OCR 失败: {e}")
            text = ""
        block = [f"===== 帧 {fmt_ts(ts)} (第{i + 1}/{len(frames)}帧) ====="]
        if text.strip():
            block.append(f"[画面文字 OCR]\n{text}")
        else:
            block.append("[画面文字 OCR] (无明显文字)")
        sections.append("\n".join(block))

    # 可选 GLM 视觉理解(glm-4.6v-flashx): 只对"关键帧"(画面变化大)调用, 省费用
    if args.glm == "yes":
        keys = select_key_frames(frames, args.threshold, args.max_interval)
        print(f"[INFO] GLM 只分析 {len(keys)}/{len(frames)} 个关键帧 (阈值{args.threshold}, 最大间隔{args.max_interval}s)")
        for i in keys:
            ts, fp = frames[i]
            try:
                rr = subprocess.run(
                    [sys.executable, GLM_SCRIPT, "--image", fp,
                     "--prompt", "请描述这张视频截图的内容：画面中有什么主体/图表/界面/动作，用于辅助制作学习笔记。简洁中文。"],
                    capture_output=True, text=True, timeout=180)
                desc = (rr.stdout or rr.stderr or "").strip()[:500]
            except Exception as e:
                desc = f"失败: {e}"
            sections[i] += f"\n[GLM画面理解]\n{desc if desc else '(GLM无返回)'}"

    combined = "\n\n".join(sections)
    if args.out:
        Path(args.out).write_text(combined, encoding="utf-8")
        print(f"[OK] 视觉文本已保存: {args.out}")
    else:
        print(combined)

    # 临时帧目录由 atexit 统一清理（见 tmpdir 创建处）


if __name__ == "__main__":
    main()
