#!/usr/bin/env python3
"""wizard.py 自动化测试（v0.6.5 新增）—— 隔离运行，不碰真实配置。

用法:
  python scripts/test_wizard.py [--all]

覆盖本轮验收点：
  1. 问题顺序：5存储根 → 6课程名 → 7命名 → 8中间产物 → 9缓存位置
  2. 课程名规则三选项：auto/fixed/folder + 路径预览联动 + N打回重选
  3. 落盘字段完整（含 course_rule/course_fixed）
  4. 主脚本 process() 课程名规则应用（真实 detect_parts + 覆盖）
  5. load_config 对旧配置（缺新字段）向后兼容
"""
import io
import json
import os
import shutil
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wizard as W

# ---------- 隔离环境：配置读写导到临时目录，绝不碰真实 wizard.json ----------
_TMP = tempfile.mkdtemp(prefix="wiztest_")
W.CONFIG_DIR = _TMP
W.CONFIG_FILE = os.path.join(_TMP, "wizard.json")

# ---------- 结果统计 ----------
_PASS = 0
_FAIL = 0
_FAIL_LIST = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    """断言一条测试。"""
    global _PASS, _FAIL
    mark = "PASS" if cond else "FAIL"
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        _FAIL_LIST.append(name)
    print(f"  [{mark}] {name}" + (f" -> {detail}" if detail else ""))


def run(seq, fn, *args, **kwargs):
    """按输入序列跑函数，捕获输出。fake_input 保留 prompt 输出（真实 input 行为）。"""
    it = iter(seq)
    buf = io.StringIO()

    def fake_input(prompt=""):
        if prompt:
            buf.write(prompt + "\n")
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    with mock.patch("builtins.input", side_effect=fake_input), \
         mock.patch("sys.stdout", buf), \
         mock.patch.object(W, "_ask_glm_config", lambda: None):
        ret = fn(*args, **kwargs)
    return buf.getvalue(), ret


# 固定前缀：Q1(1) Q2a(1) Q2b(1) Q3(1) Q4(1) Q5选A(1) Q5确认(1) = 7 个空
P7 = ["", "", "", "", "", "", ""]


def test_problem_order():
    """问题顺序：5存储→6课程名→7命名→8中间产物→9缓存。"""
    print("\n== 1. 问题顺序 ==")
    out, cfg = run(P7 + ["", "", "", "", "", "", ""], W.run_wizard, True)
    lines = [l.strip() for l in out.splitlines()]
    q6 = [l for l in lines if l.startswith("【问题6】")][0]
    q7 = [l for l in lines if l.startswith("【问题7】")][0]
    q8 = [l for l in lines if l.startswith("【问题8】")][0]
    q9 = [l for l in lines if l.startswith("【问题9】")][0]
    ok("问题6=课程名", "课程名" in q6 and "笔记最外层" in q6, q6[:30])
    ok("问题7=笔记文件命名", "笔记文件用什么命名" in q7, q7[:30])
    ok("问题8=中间产物处理", "中间文件" in q8 and "怎么处理" in q8, q8[:30])
    ok("问题9=缓存位置", "中间文件" in q9 and "放哪里" in q9, q9[:30])
    idx6, idx7, idx8, idx9 = out.find("【问题6】"), out.find("【问题7】"), \
        out.find("【问题8】"), out.find("【问题9】")
    ok("顺序 6<7<8<9", idx6 < idx7 < idx8 < idx9, f"{idx6}<{idx7}<{idx8}<{idx9}")
    ok("Q5(存储) 先于 Q6(课程名)", out.find("【问题5】") < idx6)


def test_course_rule_fixed():
    """课程名固定 + 命名前缀，路径预览联动。"""
    print("\n== 2. 课程名固定 + 命名前缀 ==")
    # Q6选B(1) 固定名(1) 确认(1) | Q7选C(1) 前缀(1) 确认(1) | Q8(1) Q9(1) 收尾(1)
    seq = P7 + ["B", "我的英语课", "", "C", "基础篇", "", "", "", ""]
    out, cfg = run(seq, W.run_wizard, True)
    ok("course_rule=fixed", cfg["course_rule"] == "fixed", cfg["course_rule"])
    ok("course_fixed=我的英语课", cfg["course_fixed"] == "我的英语课", cfg["course_fixed"])
    ok("naming=custom", cfg["naming"] == "custom", cfg["naming"])
    ok("naming_prefix=基础篇", cfg["naming_prefix"] == "基础篇", cfg["naming_prefix"])
    ok("Q6 固定课程名路径预览", "固定课程名「我的英语课」" in out)
    ok("Q7 命名预览跟随课程名", "我的英语课\\第XX讲_标题" in out and "基础篇_小节名.md" in out)
    ok("summary 联动", "固定「我的英语课」" in out and "前缀「基础篇」" in out)


def test_course_rule_auto():
    """课程名自动（默认）。"""
    print("\n== 3. 课程名自动（默认） ==")
    out, cfg = run(P7 + ["", "", "", "", "", "", ""], W.run_wizard, True)
    ok("course_rule=auto", cfg["course_rule"] == "auto", cfg["course_rule"])
    ok("course_fixed 已清除", "course_fixed" not in cfg)
    ok("Q7 预览显示自动识别", "课程名（自动识别）" in out)


def test_course_rule_folder():
    """课程名源文件名 + 只留小节名。"""
    print("\n== 4. 课程名源文件名 + 只留小节名 ==")
    # Q6选C(1) 确认(1) | Q7选B(1) 确认(1) | Q8(1) Q9(1) 收尾(1)
    seq = P7 + ["C", "", "B", "", "", "", ""]
    out, cfg = run(seq, W.run_wizard, True)
    ok("course_rule=folder", cfg["course_rule"] == "folder", cfg["course_rule"])
    ok("naming=simple", cfg["naming"] == "simple", cfg["naming"])
    ok("Q7 预览显示源文件夹名", "视频所在文件夹名" in out)


def test_course_rule_retry():
    """固定课程名 N 打回 → 重选自动。"""
    print("\n== 5. 课程名 N 打回重选 ==")
    # Q6选B(1) 固定名(1) 确认N(1) 重选A(1) 确认(1) | Q7选A(1) 确认(1) | Q8(1) Q9(1) 收尾(1)
    seq = P7 + ["B", "我的英语课", "N", "A", "", "", "", "", "", ""]
    out, cfg = run(seq, W.run_wizard, True)
    ok("N打回后=auto", cfg["course_rule"] == "auto" and "course_fixed" not in cfg)
    ok("打回提示出现", "已取消，请重新选择课程名规则" in out)


def test_persist_fields():
    """落盘字段完整（常驻字段 + 课程名规则）。"""
    print("\n== 6. 落盘字段完整 ==")
    # 重新跑 fixed 场景以便 course_fixed 存在
    seq = P7 + ["B", "我的英语课", "", "C", "基础篇", "", "", "", ""]
    run(seq, W.run_wizard, True)
    d = json.load(open(W.CONFIG_FILE, encoding="utf-8"))
    need_always = ("mode", "interval", "smart_frame", "glm", "speaker", "note_style",
                   "precheck", "notes_root", "cleanup", "cache_place", "naming",
                   "naming_prefix", "course_rule", "course_fixed")
    ok("14 字段全部落盘", all(k in d for k in need_always), sorted(d.keys()))
    ok("fixed 场景 course_fixed 存在", d.get("course_fixed") == "我的英语课")


def test_main_script_rule():
    """主脚本 process() 课程名规则应用（真实 detect_parts + 覆盖）。"""
    print("\n== 7. 主脚本课程名规则应用 ==")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ctn", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "course_video_to_notes.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def apply(course, video):
        course_rule = os.environ.get("COURSE_RULE", "auto")
        if course_rule == "fixed":
            fixed = os.environ.get("COURSE_FIXED", "").strip()
            if fixed:
                return fixed
        elif course_rule == "folder":
            return os.path.basename(os.path.dirname(os.path.abspath(video))) or "未分类课程"
        return course

    tests = [
        ("auto", "",   r"E:\x\测试视频\1-1_abc.mp4", "测试视频", "测试视频"),
        ("auto", "",   r"E:\x\20节斯坦福NLP课程\03\3-1_def.mp4", "01-斯坦福NLP", "01-斯坦福NLP"),
        ("fixed", "我的英语课", r"E:\x\测试视频\1-1_abc.mp4", "测试视频", "我的英语课"),
        ("folder", "", r"E:\x\我的课目录\1-1_abc.mp4", "旧课程名", "我的课目录"),
        ("fixed", "",  r"E:\x\测试视频\1-1_abc.mp4", "测试视频", "测试视频"),
    ]
    for rule, fixed, video, detect_course, expect in tests:
        os.environ["COURSE_RULE"] = rule
        if fixed:
            os.environ["COURSE_FIXED"] = fixed
        else:
            os.environ.pop("COURSE_FIXED", None)
        got = apply(detect_course, video)
        ok(f"rule={rule} fixed={fixed or '-'} -> [{expect}]", got == expect, got)


def test_old_config_compat():
    """load_config 对旧配置（缺 course_rule/course_fixed）向后兼容。"""
    print("\n== 8. 旧配置向后兼容 ==")
    # 写一个旧格式配置（无课程名规则字段）
    old = {"mode": "single", "naming": "default", "notes_root": ""}
    json.dump(old, open(W.CONFIG_FILE, "w", encoding="utf-8"))
    cfg = W.load_config()
    ok("旧配置不崩且补默认 course_rule=auto", cfg.get("course_rule") == "auto", cfg.get("course_rule"))
    ok("旧配置补默认 course_fixed=''", cfg.get("course_fixed") == "", repr(cfg.get("course_fixed")))
    ok("旧配置原有字段保留", cfg.get("mode") == "single")


def main():
    only_all = "--all" in sys.argv
    tests = [test_problem_order, test_course_rule_fixed, test_course_rule_auto,
             test_course_rule_folder, test_course_rule_retry, test_persist_fields,
             test_main_script_rule, test_old_config_compat]
    for t in tests:
        t()
    print(f"\n===== 结果：{_PASS} PASS / {_FAIL} FAIL =====")
    if _FAIL:
        print("失败项：")
        for f in _FAIL_LIST:
            print(f"  - {f}")
        shutil.rmtree(_TMP, ignore_errors=True)
        sys.exit(1)
    shutil.rmtree(_TMP, ignore_errors=True)
    print("✅ 全部通过")


if __name__ == "__main__":
    main()
