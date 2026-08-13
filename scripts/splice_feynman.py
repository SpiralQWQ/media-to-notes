#!/usr/bin/env python3
"""把费曼思考题块（kpNN.md）拼回笔记对应知识点。

背景：笔记的「❓ 费曼思考题」可能先单独生成（每个知识点一个 kpNN.md），
再批量拼回笔记。本工具按「### N. 」知识点标题匹配，用新费曼块替换旧块。

用法:
  python splice_feynman.py <笔记.md> [--feynman-dir <目录>]

默认费曼目录：笔记同目录下的 `.feynman/`（可改用 --feynman-dir 指定）。
"""
import argparse
import os
import re
import sys

try:  # Windows GBK 控制台也能正常打印 emoji/中文，避免 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    parser = argparse.ArgumentParser(description="把费曼思考题块拼回笔记对应知识点")
    parser.add_argument("note", help="笔记 md 路径")
    parser.add_argument("--feynman-dir", default=None,
                        help="费曼块目录（默认: 笔记同目录下 .feynman/）")
    args = parser.parse_args()

    NOTE = args.note
    FEYN = args.feynman_dir or os.path.join(os.path.dirname(NOTE), ".feynman")
    if not os.path.exists(NOTE):
        sys.exit(f"笔记不存在: {NOTE}")
    if not os.path.isdir(FEYN):
        sys.exit(f"费曼块目录不存在: {FEYN}")

    with open(NOTE, encoding="utf-8") as f:
        content = f.read()

    # 按知识点段落切分
    sections = re.split(r"(?m)^(?=### \d+\. )", content)
    new_sections = []
    replaced = 0
    for sec in sections:
        m = re.match(r"### (\d+)\. ", sec)
        if not m:
            new_sections.append(sec)
            continue
        num = int(m.group(1))
        fpath = os.path.join(FEYN, f"kp{num:02d}.md")
        if not os.path.exists(fpath):
            print(f"  [跳过] kp{num:02d}.md 不存在")
            new_sections.append(sec)
            continue
        lines = open(fpath, encoding="utf-8").read().splitlines()
        # 去掉文件头 "# 知识点 N：..." 行
        while lines and lines[0].startswith("# 知识点"):
            lines.pop(0)
        block = "\n".join(lines).strip()
        idx = sec.find("- **❓ 费曼思考题")
        if idx != -1:
            sec = sec[:idx].rstrip() + "\n"   # 去掉旧费曼块
        new_sections.append(sec + block + "\n\n")
        replaced += 1

    content = "".join(new_sections)
    with open(NOTE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"完成: 替换 {replaced} 个知识点的费曼思考题")


if __name__ == "__main__":
    main()
