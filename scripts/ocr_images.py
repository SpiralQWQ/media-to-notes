#!/usr/bin/env python3
"""图片 OCR：PaddleOCR(最准)优先，RapidOCR(轻量)兜底。识别图中文字并输出。
用法: python ocr_images.py <图片1> [图片2...] [--out 输出.txt]
"""
import argparse
import sys
from pathlib import Path


def _make_paddle():
    from paddleocr import PaddleOCR
    try:
        return PaddleOCR(use_doc_orientation_classify=False,
                         use_doc_unwarping=False,
                         use_textline_orientation=False,
                         show_log=False)
    except TypeError:
        try:
            return PaddleOCR(show_log=False)
        except TypeError:
            return PaddleOCR()


def _ocr_paddle(images):
    ocr = _make_paddle()
    out = []
    for img in images:
        try:
            if hasattr(ocr, "predict"):  # PaddleOCR 3.x
                res = ocr.predict(input=img)
                texts = [t for r in res for t in (r.get("rec_texts") or [])]
            else:                        # PaddleOCR 2.x
                res = ocr.ocr(img, cls=True)
                texts = [item[1][0] for line in res for item in (line or [])]
            out.append("\n".join(texts))
        except Exception as e:
            print(f"  [WARN] 跳过 {img}: {e}", file=sys.stderr)
            out.append("")
    return out


def _ocr_rapid(images):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    out = []
    for img in images:
        try:
            result, _ = ocr(img)
            out.append("\n".join(item[1] for item in (result or [])))
        except Exception as e:
            print(f"  [WARN] 跳过 {img}: {e}", file=sys.stderr)
            out.append("")
    return out


def main():
    parser = argparse.ArgumentParser(description="图片 OCR → 文字")
    parser.add_argument("images", nargs="+", help="图片路径")
    parser.add_argument("--out", help="输出文本文件路径")
    args = parser.parse_args()

    engine = "?"
    try:
        texts = _ocr_paddle(args.images)
        engine = "PaddleOCR"
    except ImportError:
        texts = _ocr_rapid(args.images)
        engine = "RapidOCR(未装PaddleOCR)"
    except Exception as e:
        try:
            texts = _ocr_rapid(args.images)
            engine = f"RapidOCR(兜底: PaddleOCR异常 {e})"
        except Exception as e2:
            print(f"OCR 全部失败: Paddle={e} Rapid={e2}", file=sys.stderr)
            sys.exit(1)

    for img, t in zip(args.images, texts):
        print(f"[{Path(img).name}] 识别 {len(t)} 字")
    print(f"[引擎] {engine}")

    # 每张图加文件名分隔头，便于后续按图归属文本
    blocks = [f"【{Path(img).name}】\n{t}" for img, t in zip(args.images, texts)]
    combined = "\n\n".join(blocks).strip()
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(combined, encoding="utf-8")
        print(f"[OK] OCR 文本已保存: {args.out}")
    else:
        print(combined)


if __name__ == "__main__":
    main()
