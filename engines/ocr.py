#!/usr/bin/env python3
"""engines/ocr.py — 视频帧/图片 OCR 引擎（含坐标排序，被 core 单向调用 / 亦可独立跑）

用法: python engines/ocr.py <视频.mp4> [--mode fixed|scene] [--interval 1] [--glm yes] [--out 输出.txt]
      python engines/ocr.py <图片1> [图片2...] [--out 输出.txt]   # 图片走同名 OCR+排序

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
import time
from pathlib import Path

# Windows 控制台 UTF-8 输出（防 gbk 编码崩溃，尤其是中文/进度条混排）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GLM_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glm_vision.py")
MAX_FRAMES = 6000  # 单视频抽帧上限（每秒2帧×50分钟≈6000，用户确认 OCR 每帧分析不惧耗时）


def _fmt_remain(sec: float) -> str:
    """剩余时间估算格式化。"""
    sec = max(0, int(sec))
    if sec >= 3600:
        return f"{sec // 3600}小时{sec % 3600 // 60}分"
    if sec >= 60:
        return f"{sec // 60}分{sec % 60:02d}秒"
    return f"{sec}秒"


def _progress_bar(idx: int, total: int, pct: int, t0: float, label: str = "OCR",
                  width: int = 24) -> str:
    """\r 单行刷新进度条：百分比条 + 第N/总 + 剩余时间估算。
    用 ASCII 字符(=/-)避免 gbk 终端 UnicodeEncodeError。"""
    filled = int(width * pct / 100)
    bar = "=" * filled + "-" * (width - filled)
    # 剩余时间 = 已用时间 / 已做比例 × 剩余比例（外推）
    elapsed = time.time() - t0
    remain = elapsed / pct * (100 - pct) if pct > 0 else 0
    return f"  [{label}] [{bar}] {pct:3d}% | {idx}/{total} | 剩余{_fmt_remain(remain)}"


def make_ocr(threads: int = 2):
    """初始化 RapidOCR（限线程，环境变量对 onnxruntime 无效，须构造传参）。"""
    from rapidocr_onnxruntime import RapidOCR
    try:
        return RapidOCR(intra_op_num_threads=threads, inter_op_num_threads=1)
    except TypeError:  # 老版本不支持该参数，退化为默认
        return RapidOCR()


def ocr_image_to_text(image_path: str, ocr=None) -> str:
    """单张图片 OCR → 按坐标排序的文字。未装 rapidocr-onnxruntime 抛 ImportError。"""
    ocr = ocr or make_ocr()
    result, _ = ocr(image_path)
    return _ocr_reading_order(result or [])


def ocr_images_to_text(image_paths: list) -> list:
    """多张图片 OCR → 每张排序文字列表（共享一个 OCR 实例，省加载）。"""
    ocr = make_ocr()
    return [ocr_image_to_text(p, ocr) for p in image_paths]


def fmt_ts(sec: float) -> str:
    s = int(sec)
    return f"{s // 60:02d}:{s % 60:02d}"


def _ocr_reading_order(items: list) -> str:
    """把 RapidOCR 结果按视觉阅读顺序重排：上→下分行、行内左→右拼接。

    问题背景：RapidOCR 返回的文字顺序 ≠ 阅读顺序（可能上/下排字、按钮、正文混排），
    直接拼接会导致画面文字语序混乱。此函数利用检测框坐标恢复阅读顺序。
    items: RapidOCR 结果，每项 [box, text, conf]，box=[[x,y]×4]。
    返回有序拼接文本（无内容 → ""）。
    """
    if not items:
        return ""

    def _top_y(it):
        box = it[0]
        return min(p[1] for p in box)

    items = [it for it in items if it[1] and str(it[1]).strip()]
    items.sort(key=_top_y)                    # 先按上边缘 y 从上到下

    # 行聚类：y 差 ≤ 40px 视为同一视觉行；行内按中心 x 从左到右
    rows = []  # [{'y': 行锚, 'cells': [(x, text), ...]}]
    for it in items:
        box = it[0]
        min_y = min(p[1] for p in box)
        cx = sum(p[0] for p in box) / len(box)
        if rows and abs(min_y - rows[-1]["y"]) <= 40:
            rows[-1]["cells"].append((cx, str(it[1]).strip()))
        else:
            rows.append({"y": min_y, "cells": [(cx, str(it[1]).strip())]})

    out_lines = []
    for row in rows:
        row["cells"].sort(key=lambda t: t[0])
        out_lines.append(" ".join(c[1] for c in row["cells"]))
    return "\n".join(l for l in out_lines if l)


def extract_fixed(video, interval, tmpdir):
    """固定间隔抽帧: 每 interval 秒一帧(上限按时长动态: 时长×2帧/秒, 不低于6000)"""
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
    # 帧预算自适应：上限 = 时长(秒) × 2帧/秒，下限 6000（防短视频过小，留足余量）
    # 这样 50 分钟→6000，100 分钟→12000，不再固定 6000 截断长视频
    dynamic_max = max(int(dur * 2), MAX_FRAMES) if dur > 0 else MAX_FRAMES
    frames = []
    t = 0.0
    while t < dur and len(frames) < dynamic_max:
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


def precheck_deps(glm: str = "no"):
    """入口依赖预检：缺失组件直接报错（fails loud），不等到运行中途才发现。"""
    missing = []
    for tool in ("ffmpeg", "ffprobe"):
        try:
            r = subprocess.run([tool, "-version"], capture_output=True, timeout=30)
            if r.returncode != 0:
                missing.append(tool)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            missing.append(tool)
    if missing:
        sys.exit(f"[错误] 依赖缺失: {', '.join(missing)}。请安装 ffmpeg/ffprobe 并加入 PATH。")
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        sys.exit("[错误] 未安装 rapidocr-onnxruntime。视频帧 OCR 需要它，请先 pip install rapidocr-onnxruntime。")
    if glm == "yes":
        if not os.path.exists(GLM_SCRIPT):
            sys.exit(f"[错误] GLM 脚本缺失: {GLM_SCRIPT}")
    print("[PRECHECK] 依赖预检通过（ffmpeg/ffprobe/rapidocr 就绪）")


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
    parser.add_argument("--precheck", choices=["yes", "no"], default="yes",
                        help="入口依赖预检(默认开): ffmpeg/ffprobe/ocr/glm 缺失直接报错")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"视频不存在: {args.video}")
    if args.interval <= 0:
        sys.exit("--interval 必须为正数（单位：秒）")

    if args.precheck == "yes":
        precheck_deps(args.glm)

    tmpdir = tempfile.mkdtemp(prefix="vf_")
    atexit.register(shutil.rmtree, tmpdir, ignore_errors=True)  # 任何退出路径（含 sys.exit/异常）都清理临时帧
    if args.mode == "scene":
        frames = extract_scene(args.video, args.threshold, args.max_interval, tmpdir)
        print(f"[INFO] 场景检测抽帧: {len(frames)} 帧 (阈值{args.threshold}, 最大间隔{args.max_interval}s)")
    else:
        frames = extract_fixed(args.video, args.interval, tmpdir)
        print(f"[INFO] 固定间隔抽帧: {len(frames)} 帧 (每{args.interval}秒1帧, 动态上限)")
        if len(frames) >= MAX_FRAMES:
            print(f"[⚠️WARN] 已达抽帧上限 {MAX_FRAMES}（约{MAX_FRAMES*args.interval/60:.0f}分钟视频），"
                  f"超长部分画面被截断！如需完整请调大 MAX_FRAMES")

    if not frames:
        sys.exit("未抽到帧")

    # OCR 全部帧(免费; 视频帧 OCR 用 RapidOCR 轻量引擎)
    # 限制 CPU 线程数：RapidOCR 原生支持 intra_op/inter_op_num_threads（官方 config 参数）
    # 环境变量(OMP/ORT_*)对 onnxruntime 无效，必须构造时传参
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        sys.exit("[错误] 未安装 rapidocr-onnxruntime。视频帧 OCR 需要它，请先 pip install rapidocr-onnxruntime（或 pip install -r requirements.txt）")
    try:
        ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    except TypeError:  # 老版本不支持该参数，退化为默认
        ocr = RapidOCR()
    sections = []
    _t0 = time.time()
    for i, (ts, fp) in enumerate(frames):
        pct = int((i + 1) / max(len(frames), 1) * 100)
        # 实时进度条：百分比 + 第N/帧 + 剩余时间估算（\r 单行刷新）
        print(_progress_bar(i + 1, len(frames), pct, _t0, "OCR"), end="\r", flush=True)
        try:
            result, _ = ocr(fp)
            text = _ocr_reading_order(result or [])
        except Exception as e:
            print(f"\n  [WARN] 帧 {fmt_ts(ts)} OCR 失败: {e}")
            text = ""
        block = [f"===== 帧 {fmt_ts(ts)} (第{i + 1}/{len(frames)}帧) ====="]
        if text.strip():
            block.append(f"[画面文字 OCR]\n{text}")
        else:
            block.append("[画面文字 OCR] (无明显文字)")
        sections.append("\n".join(block))
    print()  # 进度条换行结束，后续输出从新行开始

    # 可选 GLM 视觉理解(glm-4.6v-flashx): 只对"关键帧"(画面变化大)调用, 省费用
    if args.glm == "yes":
        keys = select_key_frames(frames, args.threshold, args.max_interval)
        print(f"[INFO] GLM 只分析 {len(keys)}/{len(frames)} 个关键帧 (阈值{args.threshold}, 最大间隔{args.max_interval}s)")
        max_retries = 3  # 网络错误重试上限
        skipped = 0
        stopped = False
        _t_glm = time.time()
        for _gi, i in enumerate(keys):
            if stopped:
                sections[i] += "\n[GLM画面理解] (用户停止画面理解，未处理)"
                continue
            ts, fp = frames[i]
            desc = ""
            last_err = ""
            is_content_filter = False
            # 实时进度条：第N/总关键帧 + 剩余时间估算（\r 单行刷新）
            _gpct = int((_gi + 1) / max(len(keys), 1) * 100)
            print(_progress_bar(_gi + 1, len(keys), _gpct, _t_glm, "GLM"), end="\r", flush=True)
            # 网络错误 → 重试；contentFilter(400) → 不重试（确定性拒绝）
            for attempt in range(1, max_retries + 1):
                try:
                    rr = subprocess.run(
                        [sys.executable, GLM_SCRIPT, "--image", fp,
                         "--prompt", "请描述这张视频截图的内容：画面中有什么主体/图表/界面/动作，用于辅助制作学习笔记。简洁中文。"],
                        capture_output=True, text=True, timeout=180)
                    if rr.returncode == 0 and rr.stdout.strip():
                        desc = rr.stdout.strip()[:500]
                        break
                    last_err = (rr.stdout or rr.stderr or "").strip()[:300]
                    # 判定：400 contentFilter（内容敏感）→ 不重试
                    if "contentFilter" in last_err or "1301" in last_err or "content_filter" in last_err:
                        is_content_filter = True
                        break
                except Exception as e:
                    last_err = str(e)
                if attempt < max_retries:
                    print(f"\n      [GLM重试] 帧 {fmt_ts(ts)} 第{attempt}次失败({last_err})，重试...")
            # 处理失败
            if not desc:
                if is_content_filter:
                    # 内容敏感：先提示，逐帧让用户选（跳过/停止/重试）
                    print(f"\n      [⚠️敏感] 帧 {fmt_ts(ts)} 画面被 AI 判定敏感（内容过滤）：{last_err[:80]}")
                    choice = input("      跳过此帧(A) / 停止画面理解(B) / 重试(C) [A]: ").strip().upper() or "A"
                    if choice == "C":
                        # 重试一次
                        try:
                            rr = subprocess.run(
                                [sys.executable, GLM_SCRIPT, "--image", fp,
                                 "--prompt", "请描述这张视频截图的内容（无敏感内容，仅画面构图与主体）：简洁中文。"],
                                capture_output=True, text=True, timeout=180)
                            if rr.returncode == 0 and rr.stdout.strip():
                                desc = rr.stdout.strip()[:500]
                        except Exception:
                            pass
                        if not desc:
                            print(f"      重试仍失败，跳过此帧")
                            skipped += 1
                            sections[i] += "\n[GLM画面理解] (帧被AI判定敏感，用户选择跳过)"
                            continue
                    elif choice == "B":
                        print("      已停止画面理解（保留已处理帧，未处理帧标记为停止）")
                        stopped = True
                        sections[i] += "\n[GLM画面理解] (用户停止画面理解)"
                        continue
                    else:
                        skipped += 1
                        sections[i] += "\n[GLM画面理解] (帧被AI判定敏感，用户选择跳过)"
                        continue
                else:
                    # 网络错误：重试3次后三选（继续重试/跳过/停止）
                    print(f"\n      [❌网络] 帧 {fmt_ts(ts)} 网络异常：{last_err[:80]}")
                    choice = input("      继续重试(A) / 跳过此帧(B) / 停止画面理解(C) [B]: ").strip().upper() or "B"
                    if choice == "A":
                        try:
                            rr = subprocess.run(
                                [sys.executable, GLM_SCRIPT, "--image", fp,
                                 "--prompt", "请描述这张视频截图的内容：画面中有什么主体/图表/界面/动作，用于辅助制作学习笔记。简洁中文。"],
                                capture_output=True, text=True, timeout=180)
                            if rr.returncode == 0 and rr.stdout.strip():
                                desc = rr.stdout.strip()[:500]
                        except Exception:
                            pass
                        if not desc:
                            print(f"      重试仍失败，跳过此帧")
                            skipped += 1
                            sections[i] += "\n[GLM画面理解] (网络错误，用户选择跳过)"
                            continue
                    elif choice == "C":
                        print("      已停止画面理解（保留已处理帧）")
                        stopped = True
                        sections[i] += "\n[GLM画面理解] (用户停止画面理解)"
                        continue
                    else:
                        skipped += 1
                        sections[i] += "\n[GLM画面理解] (网络错误，用户选择跳过)"
                        continue
            sections[i] += f"\n[GLM画面理解]\n{desc}"
        print()  # 进度条换行结束，后续输出从新行开始

        # 总结（不因 GLM 失败卡死，保留已处理 + 标记未处理）
        if skipped or stopped:
            done = len(keys) - skipped - (stopped and 1 or 0)
            print(f"[GLM] 完成 {done}/{len(keys)} 帧，跳过 {skipped} 帧，"
                  f"{'停止' if stopped else ''}（笔记可生成，缺失帧可后续补跑）")
        else:
            print(f"[GLM] 全部 {len(keys)} 帧画面理解完成")

    combined = "\n\n".join(sections)
    if args.out:
        Path(args.out).write_text(combined, encoding="utf-8")
        print(f"[OK] 视觉文本已保存: {args.out}")
    else:
        print(combined)

    # 临时帧目录由 atexit 统一清理（见 tmpdir 创建处）


if __name__ == "__main__":
    main()
