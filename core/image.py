#!/usr/bin/env python3
"""core/image.py — 图片/图集域链路编排（对齐视频画面那套 OCR+GLM，仅无时间线）。

每张图都输出「【图片N】 + [画面文字 OCR] + [GLM画面理解]」两块（glm=yes 才有 GLM 块），
与视频帧的「帧标记 + OCR + GLM」同引擎、同质量；区别仅是无 [MM:SS] 时间戳（用图片编号代替）。
组装：assemble/album.py 图序罗列（无时间轴，不能交错）。
"""
from __future__ import annotations

import os
import subprocess
import sys

import clean.plain as plain
import assemble.album as album
from engines import ocr

_ENGINES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engines")


def _glm_describe(image: str) -> str:
    """子进程调 engines/glm_vision.py 看懂单图；失败返回空串（不阻塞）。"""
    prompt = "请描述这张图片的内容（主体/场景/图表/界面/文字信息），用于辅助制作学习笔记。简洁。"
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(_ENGINES_DIR, "glm_vision.py"),
             "--image", image, "--prompt", prompt],
            capture_output=True, timeout=180)
        return (r.stdout or "").decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def process_image(images: list, out_root: str = "", glm: str = "no") -> dict:
    """图片/图集 → 半成品 md（图序，对齐视频那套 OCR+GLM）。返回 {txt, clean_md, chars, images}。"""
    if not images:
        return {"error": "无图片输入"}
    out_root = out_root or os.path.join("_转写缓存", "图片")
    os.makedirs(out_root, exist_ok=True)
    stem = os.path.splitext(os.path.basename(images[0]))[0]

    # ① OCR（必做，坐标排序）→ 每图文字
    texts = ocr.ocr_images_to_text(images)

    # ② 每图块：视频式「OCR 块 + GLM 块」，用【图片N】代替帧时间戳
    blocks = []
    for n, (p, t) in enumerate(zip(images, texts), 1):
        block = f"【图片{n}】"
        if t.strip():
            block += f"\n[画面文字 OCR]\n{t.strip()}"
        if glm == "yes":           # GLM 询问用户开/关（同视频：glm=yes 才看懂画面）
            d = _glm_describe(p)
            if d:
                block += f"\n[GLM画面理解]\n{d}"
        blocks.append(block)
    txt = "\n\n".join(b for b in blocks if b)

    # ③ 清洗（与视频同规：去水印/标签独立行，保留图片序号与内容）
    cleaned = plain.clean_plain_text(txt)

    # ④ 组装 → 图序 md
    md = album.assemble_album(cleaned, title=stem)
    txt_path = os.path.join(out_root, f"{stem}_ocr.txt")
    clean_md = os.path.join(out_root, f"{stem}_clean.md")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)
    with open(clean_md, "w", encoding="utf-8") as f:
        f.write(md)
    return {"txt": txt_path, "clean_md": clean_md, "chars": len(md), "images": len(images)}