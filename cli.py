#!/usr/bin/env python3
"""cli.py — media-to-notes 薄入口：四模态（视频/图集/音频/文本）+ 类型向导。

视频/图集/音频走 core.{video,image,audio}（分层：engines/clean/assemble）；
文本用 clean.plain 清洗出 *_clean.md。`--wizard` 按媒体类型弹对应向导。
旧 media_to_notes.py（下载/detect/文本）保留为兼容入口。
"""
from __future__ import annotations

import os
import sys

import core.base as base


def _classify(path: str):
    if not path:
        return None
    low = path.lower()
    if low.endswith(base.VIDEO_EXTS):
        return "video"
    if low.endswith(base.IMAGE_EXTS):
        return "image"
    if low.endswith(base.AUDIO_EXTS):
        return "audio"
    if low.endswith((".txt", ".md", ".markdown")):
        return "text"
    return None


def _wizard_cfg(kind: str) -> dict:
    """按类型弹向导（scripts/wizard.py 类型感知版）；未启用/失败返回 {}。"""
    try:
        import importlib.util as u
        here = os.path.dirname(os.path.abspath(__file__))
        for p in (os.path.join(here, "scripts", "wizard.py"),
                  os.path.join(here, "configs", "wizard.py")):
            if os.path.exists(p):
                spec = u.spec_from_file_location("_w", p)
                w = u.module_from_spec(spec)
                spec.loader.exec_module(w)
                return w.run_wizard(media_type=kind)
    except Exception as e:
        print(f"[WARN] 向导未完成，用默认: {type(e).__name__}: {e}")
    return {}


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        sys.exit('用法: python cli.py "<视频/图片/音频/文本路径>" [--glm yes|no] [--wizard]')

    glm = "no"
    wizard_flag = False
    paths = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--glm" and i + 1 < len(args):
            glm = args[i + 1]
            i += 2
            continue
        if a == "--wizard":
            wizard_flag = True
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        paths.append(a)
        i += 1
    if not paths:
        sys.exit('用法: 缺少输入路径')

    videos, images, audios, texts = [], [], [], []
    for p in paths:
        if not os.path.exists(p):
            print(f"错误: 路径不存在: {p}")
            continue
        k = _classify(p)
        if k is None:
            print(f"错误: 不支持的扩展名: {p}")
            continue
        (videos if k == "video" else images if k == "image"
         else audios if k == "audio" else texts).append(p)

    for p in videos:
        try:
            cfg = _wizard_cfg("video") if wizard_flag else {}
            g = cfg.get("glm", glm) if cfg else glm
            import core.video as v
            r = v.process_video(p, glm=g)
            print(f"视频完成: {r.get('clean_md')}" if "error" not in r else f"错误: {r['error']}")
        except Exception as e:
            print(f"处理失败 {p}: {type(e).__name__}: {e}")

    for p in audios:
        try:
            if wizard_flag:
                _wizard_cfg("audio")
            import core.audio as a
            r = a.process_audio(p)
            print(f"音频完成: {r.get('clean_md')}" if "error" not in r else f"错误: {r['error']}")
        except Exception as e:
            print(f"处理失败 {p}: {type(e).__name__}: {e}")

    if images:
        try:
            cfg = _wizard_cfg("image") if wizard_flag else {}
            g = cfg.get("glm", glm) if cfg else glm
            import core.image as im
            r = im.process_image(images, glm=g)
            print(f"图集完成: {r.get('clean_md')}" if "error" not in r else f"错误: {r['error']}")
        except Exception as e:
            print(f"图集处理失败: {type(e).__name__}: {e}")

    for p in texts:
        try:
            import clean.plain as pl
            raw = open(p, encoding="utf-8", errors="replace").read()
            cleaned = pl.clean_plain_text(raw)
            if not cleaned:
                print(f"文本为空或清洗后为空: {p}")
                continue
            md = "## 内容（清洗后）\n\n" + cleaned
            out = os.path.splitext(p)[0] + "_clean.md"
            with open(out, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"文本完成: {out}")
        except Exception as e:
            print(f"文本处理失败 {p}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()