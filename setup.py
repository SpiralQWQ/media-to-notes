#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
media-to-notes 开箱即用配置向导 (setup.py)

拉取仓库后运行:  python setup.py
→ 交互式询问关键配置 → 自动生成 .env + 检测依赖 → 开箱即用

无需提前看任何文档——回答几个问题就能开始用。
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Windows GBK 控制台兼容
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def ask(question, default=None, options=None):
    """通用询问：支持 [Y/n] 或选项编号选择"""
    if options:
        print(f"\n{CYAN}{question}{RESET}")
        for i, opt in enumerate(options, 1):
            print(f"  {BOLD}{i}{RESET}. {opt[0]}")
        while True:
            raw = input(f"  选择 1-{len(options)} (默认 {default}): ").strip()
            if raw == "" and default:
                return options[int(default) - 1]
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return options[int(raw) - 1]
            print(f"  {RED}请输入 1-{len(options)}{RESET}")
    else:
        suffix = f" [{default}]" if default else ""
        while True:
            raw = input(f"{question}{suffix}: ").strip()
            if raw:
                return raw
            if default:
                return default


def check_cmd(name, hint=""):
    """检查系统命令是否存在"""
    found = shutil.which(name)
    if found:
        print(f"  {GREEN}✔{RESET} {name}: {found}")
        return True
    print(f"  {RED}✘{RESET} {name}: 未找到 {hint}")
    return False


def check_python_module(interp, module):
    """检查某个 Python 解释器里有没有某模块"""
    try:
        r = subprocess.run([interp, "-c", f"import {module}"],
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def main():
    print(f"""
{BOLD}{'='*60}{RESET}
  media-to-notes  开箱即用配置向导
  回答几个问题 → 自动生成 .env → 开箱即用
{'='*60}
""")

    # ═══════════ ① 使用场景 ═══════════
    scenario = ask(
        "你要转什么内容？（决定默认配置）",
        default="1",
        options=[
            ("抖音/B站/YouTube 链接 → 笔记（下载+转写+OCR）", "online"),
            ("本地视频文件 → 笔记（直接转写+OCR）", "local_video"),
            ("本地图片/图集 → 笔记（OCR+GLM）", "local_image"),
            ("本地文本 → 笔记（纯整理）", "local_text"),
        ],
    )[1]

    print(f"\n  {YELLOW}使用场景: {scenario}{RESET}")

    # ═══════════ ② 数据根目录 ═══════════
    default_base = str(ROOT)
    base = ask(
        "数据根目录（视频/图片/笔记/temp 建在这；回车用默认=仓库根）",
        default=default_base,
    )

    # ═══════════ ③ OCR 频率 ═══════════
    ocr_opt = ask(
        "视频画面 OCR 频率？（提取 PPT/字幕/画面文字）",
        default="2",
        options=[
            ("每秒 1 帧（快，覆盖大多数画面）", "1"),
            ("每秒 2 帧（更细，OCR 时间约翻倍）", "0.5"),
            ("只关键帧（画面变化才抽，最省）", "scene"),
            ("不需要 OCR（纯听语音）", "no"),
        ],
    )[1]

    # ═══════════ ④ GLM 视觉分析 ═══════════
    glm_opt = ask(
        "开启 GLM 视觉分析？（glm-4.6v-flashx 按量计费，理解画面含义）",
        default="2",
        options=[
            ("开启，只对关键帧（推荐，省钱）", "yes"),
            ("开启，对每张 OCR 帧（很准但贵）", "all"),
            ("不开启（只 OCR 文字，零花费）", "no"),
        ],
    )[1]

    glm_key = ""
    if glm_opt != "no":
        # 允许空回车跳过（稍后在 .env 补填），不无限循环
        print(f"\n{CYAN}粘贴 GLM API Key（bigmodel.cn 申请；回车跳过，稍后可填）{RESET}: ", end="")
        try:
            glm_key = input().strip()
        except (EOFError, KeyboardInterrupt):
            glm_key = ""
        if not glm_key:
            print(f"  {YELLOW}已跳过。可在 .env 里补填 GLM_API_KEY，或重跑 setup.py{RESET}")

    # ═══════════ ⑤ 笔记语言 ═══════════
    lang_opt = ask(
        "笔记正文用什么语言？（转写保留原语言）",
        default="1",
        options=[
            ("中文（面向零基础中文学习者，术语中英对照）", "zh"),
            ("英文", "en"),
            ("跟随内容语言（内容中文→中文，英文→英文）", "auto"),
        ],
    )[1]

    # ═══════════ ⑥ 完整转写附录 ═══════════
    appendix = ask(
        "笔记末尾保留完整转写附录吗？（AI 核对用，可追溯原话）",
        default="y",
    )
    appendix_yn = appendix.lower() in ("y", "yes", "是")

    # ═══════════ ⑦ 费曼思考题密度 ═══════════
    feynman_opt = ask(
        "费曼思考题数量？（每知识点配开放题助复习）",
        default="2",
        options=[
            ("核心10/重要8/一般6（详尽）", "10"),
            ("核心6/重要4/一般3（精简）", "6"),
            ("不要思考题", "0"),
        ],
    )[1]

    # ═══════════ ⑧ 中间产物 ═══════════
    keep_opt = ask(
        "转写中间产物（音频/JSON/OCR文本）怎么处理？",
        default="1",
        options=[
            ("保留到缓存目录（可复查/重生成）", "keep"),
            ("转完即删（省磁盘）", "delete"),
        ],
    )[1]

    # ═══════════ ⑨ 笔记组织 ═══════════
    org_opt = ask(
        "笔记目录怎么组织？",
        default="1",
        options=[
            ("按日期（NoteBooks\\日期\\顺序_概要，适合日常随手转）", "date"),
            ("按课程/主题分目录（适合系列课程）", "topic"),
        ],
    )[1]

    # ═══════════ 写入 .env ═══════════
    lines = [
        "# media-to-notes 自动生成的配置（由 setup.py 生成）",
        "# 如需修改：重跑 python setup.py，或直接编辑本文件",
        "",
    ]
    env_map = {
        "DD_BASE": base,
        "OCR_INTERVAL": ocr_opt,
        "GLM_MODE": glm_opt,
    }
    if glm_key:
        env_map["GLM_API_KEY"] = glm_key
    env_map["NOTE_LANG"] = lang_opt
    env_map["KEEP_APPENDIX"] = "true" if appendix_yn else "false"
    env_map["FEYNMAN_DENSITY"] = feynman_opt
    env_map["KEEP_MIDDLE"] = "true" if keep_opt == "keep" else "false"
    env_map["NOTE_ORGANIZE"] = org_opt

    for k, v in env_map.items():
        lines.append(f"{k}={v}")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n  {GREEN}✔{RESET} 已生成 .env：{ENV_PATH}")
    print("      内容（密钥已隐藏）:")
    for k, v in env_map.items():
        shown = "***" if "KEY" in k.upper() and v else v
        print(f"      {k}={shown}")

    # ═══════════ ⑩ 依赖检测 ═══════════
    print(f"\n{BOLD}依赖检测{RESET}")
    print("  ── 系统命令 ──")
    check_cmd("ffmpeg", "(需加入 PATH)")
    check_cmd("ffprobe", "(随 ffmpeg 安装)")
    if scenario == "online":
        check_cmd("yt-dlp", "(仅抖音链接可省略)")

    print("  ── Python 模块 ──")
    interp = sys.executable
    for mod in ["funasr", "rapidocr_onnxruntime", "soundfile", "dotenv"]:
        ok = check_python_module(interp, mod)
        if not ok:
            print(f"    {YELLOW}建议安装: pip install -r requirements.txt{RESET}")

    # ═══════════ ⑪ 生成用户偏好档（Claude 生成笔记时遵循） ═══════════
    prefs_path = ROOT / "spec" / "user_prefs.md"
    prefs = [
        "# 用户偏好（由 setup.py 生成，Claude 生成笔记时遵循）",
        "",
        f"- **使用场景**: {scenario}",
        f"- **笔记正文语言**: {lang_opt}（{'中文，术语中英对照' if lang_opt=='zh' else '英文' if lang_opt=='en' else '跟随内容'}）",
        f"- **保留完整转写附录**: {'是' if appendix_yn else '否'}",
        f"- **费曼思考题密度**: {feynman_opt}（{'核心10/重要8/一般6' if feynman_opt=='10' else '核心6/重要4/一般3' if feynman_opt=='6' else '不要'}）",
        f"- **转写中间产物**: {'保留到缓存' if keep_opt=='keep' else '转完即删'}",
        f"- **笔记目录组织**: {'按日期' if org_opt=='date' else '按课程/主题分目录'}",
        "",
        "> 修改: 重跑 `python setup.py`，或直接编辑本文件 + `.env`。",
    ]
    with open(prefs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(prefs) + "\n")
    print(f"  {GREEN}✔{RESET} 已生成用户偏好档: spec/user_prefs.md")

    print(f"""
{BOLD}{'='*60}{RESET}
  {GREEN}配置完成！{RESET}
  快速开始:
    python scripts/media_to_notes.py "<链接或本地路径>" --detect
  详细用法见 README.md / README_zh.md
{'='*60}
""")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}已取消，未写入配置{RESET}")
        sys.exit(0)
