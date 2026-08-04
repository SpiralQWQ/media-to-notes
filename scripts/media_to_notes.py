#!/usr/bin/env python3
"""视频/图集/文本 → AI 教材笔记（两阶段：先检测询问，再做分析）

支持来源：
  - 抖音链接  → jiji262 douyin-downloader（去水印，需 Cookie）
  - YouTube/B站等链接 → yt-dlp（需安装 yt-dlp）
  - 本地视频/图片/文本路径 → 直接使用

用法:
  阶段1(检测):  python media_to_notes.py "<链接或本地路径>" --detect
      → 下载/直用 → 检测类型(视频/图集/文本) → 归位 → 写状态文件 → 报告，等用户决定是否开 GLM
  阶段2(处理):  python media_to_notes.py --glm yes|no
      → 读状态文件 → 视频: ASR转写 + 多帧OCR(+GLM) / 图集: OCR(+GLM) / 文本: 直接整理
      → 产出 转写/OCR文本，交给 Claude 生成 AI 教材

内容类型:
  🎬 视频 → 提音频转写(必做) + 关键帧OCR(默认必做,多帧) + GLM画面理解(可选,需同意)
  🖼️ 图集 → OCR(默认必做) + GLM画面理解(可选,需同意)
  📄 文本 → 直接整理成 AI 教材（无 ASR/OCR）
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

try:  # Windows GBK 控制台也能正常打印 emoji/中文，避免 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:  # 允许从仓库根 .env 加载配置（可选依赖 python-dotenv）
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 可移植配置：全部可用环境变量覆盖（见仓库根 .env.example），缺省时基于脚本所在目录推导。
# 依赖的多个解释器可指向不同虚拟环境，也可全部指向同一 Python（全部依赖装一起）。
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("DD_BASE") or os.path.dirname(_THIS_DIR)   # 仓库根（数据/临时文件落这里）
DL_PY = os.environ.get("DD_DL_PY") or sys.executable             # douyin-downloader 解释器
DL_SRC = os.environ.get("DD_DL_SRC") or os.path.join(BASE, "douyin-downloader")  # 下载器源码/包目录
ASR_PY = os.environ.get("DD_ASR_PY") or sys.executable           # FunASR 转写解释器
OCR_PY = os.environ.get("DD_OCR_PY") or sys.executable           # PaddleOCR 解释器
YTDLP = os.environ.get("DD_YTDLP") or "yt-dlp"                   # yt-dlp 可执行文件
SCRIPTS = os.path.join(BASE, "scripts")
STATE = os.path.join(BASE, "temp", "current_job.json")

VIDEO_EXTS = (".mp4", ".webm", ".mkv", ".mov", ".flv", ".avi")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
TEXT_EXTS = (".txt", ".md", ".markdown")


def human_size(nbytes: int) -> str:
    mb = nbytes / 1048576
    return f"{mb:.1f}M" if mb >= 1 else f"{int(nbytes / 1024)}K"


def clean_summary(desc: str) -> str:
    t = re.sub(r"#\S+", "", desc or "")
    t = re.sub(r"[！!？?。，,、：:；;··\s]+", "", t)
    # 过滤 Windows 非法文件名字符与路径穿越，防止拼入目录/文件名
    t = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", t)
    t = t.replace("..", "_")
    return (t.strip("._") or "未命名")[:24]


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("www.")


def classify_path(p: str):
    low = p.lower()
    if low.endswith(VIDEO_EXTS):
        return "video"
    if low.endswith(IMAGE_EXTS):
        return "image"
    if low.endswith(TEXT_EXTS):
        return "text"
    return None


def _san(s: str) -> str:
    """把子进程输出里的本地路径/用户名替换为 <repo>，避免控制台/日志泄露"""
    if not s:
        return s
    masks = {BASE, os.path.join(BASE, "视频"), os.path.join(BASE, "音频"),
             os.path.join(BASE, "图片"), os.path.join(BASE, "文本"),
             os.path.expanduser("~")}
    for p in sorted((m for m in masks if m), key=len, reverse=True):
        s = re.sub(re.escape(p), "<repo>", s, flags=re.IGNORECASE)
        s = re.sub(re.escape(p.replace("\\", "/")), "<repo>", s, flags=re.IGNORECASE)
    return s


def read_manifest(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None
    for line in reversed(lines):
        line = line.strip()
        if line:
            try:
                return json.loads(line)
            except Exception:
                continue
    return None


def next_seq(date_dir: str) -> int:
    if not os.path.isdir(date_dir):
        return 0
    pat = re.compile(r"^(\d+)_")
    idxs = []
    for f in os.listdir(date_dir):
        m = pat.match(f)
        if m:
            idxs.append(int(m.group(1)))
    return max(idxs) + 1 if idxs else 0


def run(cmd, cwd, timeout=3600) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    try:
        return subprocess.run(cmd, cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, -1, "", f"[超时] 子进程超过 {timeout}s，已中止")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, -1, "", f"[错误] 找不到命令: {cmd[0]}（请先安装并加入 PATH，或用对应 DD_* 环境变量指定）")
    except PermissionError:
        return subprocess.CompletedProcess(cmd, -1, "", f"[错误] 命令不可执行（权限被拒绝）: {cmd[0]}（请确认 DD_YTDLP/DD_DL_PY/DD_ASR_PY/DD_OCR_PY 指向可执行文件，而不是目录或普通文本文件）")
    except OSError as e:
        return subprocess.CompletedProcess(cmd, -1, "", f"[错误] 命令运行异常: {cmd[0]}（{e}）")


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            st = json.load(f)
    except FileNotFoundError:
        sys.exit('未找到 temp/current_job.json，请先运行 python media_to_notes.py "<链接或本地路径>" --detect')
    except json.JSONDecodeError:
        sys.exit("temp/current_job.json 格式异常（内容已损坏，不是合法 JSON），请重新运行 --detect")
    except (UnicodeDecodeError, OSError):
        sys.exit("temp/current_job.json 无法读取（编码或权限异常），请重新运行 --detect")
    if not isinstance(st, dict) or "type" not in st:
        sys.exit("temp/current_job.json 格式异常，请重新运行 --detect")
    required = {"video": ("vdir", "video", "adir", "audio", "summary"),
                "image": ("idir", "images", "summary"),
                "text": ("tfile",)}
    if st.get("type") not in required:
        sys.exit("temp/current_job.json 的 type 字段非法（应为 video/image/text），请重新运行 --detect")
    if any(k not in st for k in required[st["type"]]):
        sys.exit("temp/current_job.json 字段不完整，请重新运行 --detect")
    return st


def _place_media(src_dir: str, files: list, summary: str, today: str, move: bool = True) -> dict:
    """把媒体文件从 src_dir 归位到 视频|图片/{today}/，视频再提音频。move=True 移走源文件，False 则复制。"""
    vroot, aroot, iroot = (os.path.join(BASE, "视频"), os.path.join(BASE, "音频"), os.path.join(BASE, "图片"))
    vids = [f for f in files if f.lower().endswith(VIDEO_EXTS)]
    imgs = [f for f in files if f.lower().endswith(IMAGE_EXTS)]
    copy_or_move = shutil.move if move else shutil.copy2

    if vids:
        vdatedir = os.path.join(vroot, today)
        os.makedirs(vdatedir, exist_ok=True)
        seq = next_seq(vdatedir)
        mp4 = vids[0]
        vsize = human_size(os.path.getsize(os.path.join(src_dir, mp4)))
        vdir = os.path.join(vdatedir, f"{seq:02d}_{today}_{summary}_{vsize}")
        os.makedirs(vdir, exist_ok=True)
        for f in files:
            copy_or_move(os.path.join(src_dir, f), os.path.join(vdir, f))
        try:
            os.rmdir(src_dir)
        except OSError:
            pass
        adatedir = os.path.join(aroot, today)
        os.makedirs(adatedir, exist_ok=True)
        awav_name = f"{summary}.wav"
        awav_tmp = os.path.join(adatedir, awav_name)
        rr = run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(vdir, mp4),
                  "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", awav_tmp], cwd=".", timeout=3600)
        if rr.returncode != 0:
            sys.exit("ffmpeg 提音频失败: " + _san(rr.stderr[-500:]))
        asize = human_size(os.path.getsize(awav_tmp))
        adir = os.path.join(adatedir, f"{seq:02d}_{today}_{summary}_{asize}")
        os.makedirs(adir, exist_ok=True)
        shutil.move(awav_tmp, os.path.join(adir, awav_name))
        print(f"[2/3] 视频已归位: {os.path.basename(vdir)} | 音频已归位: {os.path.basename(adir)}")
        return {"type": "video", "today": today, "summary": summary,
                "vdir": vdir, "video": os.path.join(vdir, mp4),
                "adir": adir, "audio": os.path.join(adir, awav_name), "seq": seq}

    if imgs:
        idatedir = os.path.join(iroot, today)
        os.makedirs(idatedir, exist_ok=True)
        seq = next_seq(idatedir)
        total = sum(os.path.getsize(os.path.join(src_dir, f)) for f in files)
        isize = human_size(total)
        idir = os.path.join(idatedir, f"{seq:02d}_{today}_{summary}_{isize}")
        os.makedirs(idir, exist_ok=True)
        for f in files:
            copy_or_move(os.path.join(src_dir, f), os.path.join(idir, f))
        try:
            os.rmdir(src_dir)
        except OSError:
            pass
        print(f"[2/3] 图片已归位: {os.path.basename(idir)}")
        return {"type": "image", "today": today, "summary": summary,
                "idir": idir, "images": [os.path.join(idir, f) for f in files], "seq": seq}

    sys.exit("目录内无视频/图片")


def _place_text(src: str, summary: str, today: str, move: bool = True) -> dict:
    """把文本文件归位到 文本/{today}/。move=True 移走源文件，False 则复制。"""
    troot = os.path.join(BASE, "文本")
    tdatedir = os.path.join(troot, today)
    os.makedirs(tdatedir, exist_ok=True)
    seq = next_seq(tdatedir)
    size = human_size(os.path.getsize(src))
    tdir = os.path.join(tdatedir, f"{seq:02d}_{today}_{summary}_{size}")
    os.makedirs(tdir, exist_ok=True)
    dst = os.path.join(tdir, os.path.basename(src))
    (shutil.move if move else shutil.copy2)(src, dst)
    print(f"[2/3] 文本已归位: {os.path.basename(tdir)}")
    return {"type": "text", "today": today, "summary": summary, "tfile": dst, "seq": seq}


def _detect_douyin(url: str, today: str) -> None:
    """抖音来源：jiji262 去水印下载 → 归位"""
    vroot = os.path.join(BASE, "视频")
    os.makedirs(vroot, exist_ok=True)
    run_py = os.path.join(DL_SRC, "run.py")
    if not os.path.exists(run_py):
        sys.exit(f"未找到下载器 {run_py}。请先克隆 jiji262/douyin-downloader 到仓库根目录（或设置 DD_DL_SRC 指向其源码目录）")
    print("[1/3] 下载内容 (抖音去水印)...")
    r = run([DL_PY, run_py, "-u", url, "-p", vroot], cwd=DL_SRC)
    if r.returncode != 0:
        sys.exit("下载失败(可能是 Cookie 过期或反爬): " + _san(r.stdout[-800:] or r.stderr[-800:]))
    rec = read_manifest(os.path.join(vroot, "download_manifest.jsonl"))
    if not rec:
        sys.exit("未读取到下载清单, 请检查下载日志")
    summary = clean_summary(rec.get("desc", ""))
    aweme_id = str(rec.get("aweme_id", "") or "")
    if not re.fullmatch(r"\d{5,}", aweme_id):
        sys.exit("清单缺少有效 aweme_id，无法定位下载目录")

    # 定位下载目录: 作者文件夹名可能与 manifest 略有差异(如下划线), 用 aweme_id 精确查找
    src_dir = None
    for d in os.listdir(vroot):
        dp = os.path.join(vroot, d)
        if not os.path.isdir(dp):
            continue
        if d.startswith(today) or d == "download_manifest.jsonl":
            continue
        if any(aweme_id in f for f in os.listdir(dp)):
            src_dir = dp
            break
    if src_dir is None:
        sys.exit(f"未找到下载目录 (aweme {aweme_id})")
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(VIDEO_EXTS + IMAGE_EXTS)]
    if not files:
        sys.exit(f"目录内无视频/图片: {os.path.basename(src_dir)}")

    st = _place_media(src_dir, files, summary, today)
    st["aweme_id"] = aweme_id
    save_state(st)
    print("[3/3] 内容类型: " + ("🎬 视频" if st["type"] == "video" else "🖼️ 图集"))


def _detect_local(p: str, today: str) -> None:
    """本地路径：直接复制/分类归位，不下载。目录按图集处理（全部图片）。"""
    if os.path.isdir(p):
        imgs = sorted(f for f in os.listdir(p) if f.lower().endswith(IMAGE_EXTS))
        if not imgs:
            sys.exit(f"目录内没有图片（支持整目录图片图集）: {os.path.basename(p)}")
        stem = clean_summary(os.path.basename(p))
        print("[1/3] 本地图集直用（不下载）...")
        st = _place_media(p, imgs, stem, today, move=False)
        save_state(st)
        print("[3/3] 内容类型: 🖼️ 图集")
        return
    if not os.path.isfile(p):
        sys.exit(f"本地路径不存在: {_san(p)}")
    kind = classify_path(p)
    if not kind:
        sys.exit(f"不支持的文件类型（支持 视频/图片/文本）: {os.path.basename(p)}")
    stem = clean_summary(os.path.splitext(os.path.basename(p))[0])
    print("[1/3] 本地文件直用（不下载）...")
    src_dir = os.path.dirname(p)
    if kind == "text":
        st = _place_text(p, stem, today, move=False)
        print("[3/3] 内容类型: 📄 文本")
    else:
        st = _place_media(src_dir, [os.path.basename(p)], stem, today, move=False)
        print("[3/3] 内容类型: " + ("🎬 视频" if st["type"] == "video" else "🖼️ 图集"))
    save_state(st)


def _detect_ytdlp(url: str, today: str) -> None:
    """YouTube/B站等来源：yt-dlp 下载 → 归位（需安装 yt-dlp）"""
    probe = run([YTDLP, "--version"], cwd=".", timeout=60)
    if probe.returncode != 0:
        sys.exit("未找到 yt-dlp。请先安装：pip install yt-dlp，或设置 DD_YTDLP 指向可执行文件")
    tr = run([YTDLP, "--no-warnings", "--get-title", url], cwd=".", timeout=120)
    summary = clean_summary(tr.stdout.strip()) if tr.returncode == 0 and tr.stdout.strip() else "ytdlp"
    tmp = os.path.join(BASE, "temp", "ytdlp_dl")
    shutil.rmtree(tmp, ignore_errors=True)  # 清掉上次残留，防止混入本次
    os.makedirs(tmp, exist_ok=True)
    print("[1/3] 用 yt-dlp 下载 (无水印)...")
    r = run([YTDLP, "-o", os.path.join(tmp, "%(id)s.%(ext)s"), "--no-playlist",
             "--no-warnings", "--newline", url], cwd=".", timeout=7200)
    if r.returncode != 0:
        sys.exit("yt-dlp 下载失败: " + _san(r.stderr[-800:] or r.stdout[-800:]))
    files = [f for f in os.listdir(tmp) if f.lower().endswith(VIDEO_EXTS + IMAGE_EXTS)]
    if not files:
        sys.exit("yt-dlp 下载完成但未找到媒体文件")
    st = _place_media(tmp, files, summary, today)
    save_state(st)
    print("[3/3] 内容类型: " + ("🎬 视频" if st["type"] == "video" else "🖼️ 图集"))


def detect(source: str) -> None:
    """阶段1 分发：按来源类型路由到对应下载/归位流程"""
    today = date.today().strftime("%Y%m%d")
    if is_url(source):
        if "douyin" in source.lower() or "iesdouyin" in source.lower():
            _detect_douyin(source, today)
        else:
            _detect_ytdlp(source, today)
    elif os.path.exists(source):
        _detect_local(source, today)
    else:
        sys.exit(f"无法识别的输入（需 URL 或存在的本地路径）: {_san(source[:200])}")
    print("→ 请向用户确认: 是否开启 GLM 视觉分析 (glm-4.6v-flashx)？然后运行 --glm yes|no")


def process(glm: str) -> None:
    """阶段2: 读状态 → 视频: ASR+多帧OCR(+GLM) / 图集: OCR(+GLM) / 文本: 直接整理"""
    st = load_state()
    ctype = st["type"]
    if ctype == "text":
        print(f"[1/1] 文本已就绪: {_san(st['tfile'])}")
        print("→ 请 Claude 读取文本 → 按 spec/note_style_spec.md 生成 AI 教材笔记")
        return
    if ctype == "video":
        # ① ASR 转写(必做)
        tjson = os.path.join(st["adir"], f"{st['summary']}.json")
        print("[1/3] FunASR 转写 (语音)...")
        rr = run([ASR_PY, os.path.join(SCRIPTS, "transcribe_funasr.py"),
                  st["audio"], tjson], cwd=".", timeout=7200)
        if rr.returncode != 0:
            print(_san(rr.stdout[-1000:])); print(_san(rr.stderr[-1000:]))
            sys.exit("转写失败")
        # ② 多帧 OCR(必做) + 可选 GLM
        vtxt = os.path.join(st["vdir"], f"{st['summary']}_visual.txt")
        print("[2/3] 多帧视觉分析 (OCR默认" + ("+GLM" if glm == "yes" else "") + ")...")
        rr = run([OCR_PY, os.path.join(SCRIPTS, "video_frames_ocr.py"), st["video"],
                  "--interval", "1", "--glm", glm, "--out", vtxt], cwd=".", timeout=7200)
        if rr.returncode != 0:
            print(_san(rr.stdout[-1000:])); print(_san(rr.stderr[-1000:]))
            sys.exit("视频视觉分析失败")
        print(f"[3/3] 转写: {_san(tjson)}")
        print(f"      视觉文本: {_san(vtxt)}")
    else:
        # 图集: OCR(必做) + 可选 GLM
        print("[1/2] OCR 识别图片文字...")
        ocr_txt = os.path.join(st["idir"], f"{st['summary']}_ocr.txt")
        rr = run([OCR_PY, os.path.join(SCRIPTS, "ocr_images.py")] + st["images"] + ["--out", ocr_txt], cwd=".", timeout=7200)
        if rr.returncode != 0:
            print(_san(rr.stdout[-1000:])); print(_san(rr.stderr[-1000:]))
            sys.exit("OCR 失败")
        if glm == "yes":
            print("[2/2] GLM 视觉理解每张图...")
            glm_txt = os.path.join(st["idir"], f"{st['summary']}_glm.txt")
            lines = []
            for img in st["images"]:
                rr = run([sys.executable, os.path.join(SCRIPTS, "glm_vision.py"),
                          "--image", img, "--prompt",
                          "请描述这张图片的内容：主体/图表/界面/文字信息，用于辅助制作学习笔记。简洁中文。"],
                         cwd=".", timeout=180)
                if rr.returncode != 0:
                    print(f"  [WARN] GLM 分析失败: {os.path.basename(img)}")
                    lines.append(f"【{os.path.basename(img)}】\n[GLM 分析失败: {_san((rr.stderr or rr.stdout or '').strip()[:200])}]")
                else:
                    lines.append(f"【{os.path.basename(img)}】\n{(rr.stdout or '').strip()[:500]}")
            with open(glm_txt, "w", encoding="utf-8") as f:
                f.write("\n\n".join(lines))
            print(f"      GLM 描述: {_san(glm_txt)}")
        print(f"[2/2] OCR 文本: {_san(ocr_txt)}")
    print("→ 请 Claude 读取以上文本 → 生成 AI 教材笔记")


def main():
    args = [a for a in sys.argv[1:] if a]
    # 优先识别来源（链接或本地路径）；有来源就先走阶段1 detect（与 --glm 同时出现时以 detect 为准）
    source = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--glm":            # 跳过 --glm 及其取值，避免把 yes/no 误当来源
            i += 2
            continue
        if a.startswith("--"):      # 其他选项参数（如 --detect）
            i += 1
            continue
        source = a                  # 首个非选项参数即来源（URL / 本地路径，含不存在的路径交给 detect() 给出明确报错）
        break
    if source:
        detect(source)
        return
    if "--glm" in args:
        i = args.index("--glm")
        glm = args[i + 1] if i + 1 < len(args) else "no"
        if glm not in ("yes", "no"):
            sys.exit("--glm 取值必须是 yes 或 no")
        process(glm)
        return
    sys.exit('用法: python media_to_notes.py "<链接或本地路径>" --detect  然后 python media_to_notes.py --glm yes|no')


if __name__ == "__main__":
    main()
