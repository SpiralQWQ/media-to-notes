#!/usr/bin/env python3
"""三分支清洗测试：视频（json+txt→交错md）/ 图集（OCR txt）/ 文本。

运行：python tests/test_clean.py
全部样例在 tests/sample/（模拟数据，可复现、不侵权），输出写临时目录不污染样例。
"""
import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _ROOT)
from clean.transcript import clean_transcript_json
from clean.visual import clean_visual_timeline
from clean.plain import clean_plain_text
from assemble.interleave import assemble_interleaved

SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample")


class TestVideoBranch(unittest.TestCase):
    """分支1 视频：转写 json 清洗 + 画面 txt 清洗 + 时间轴交错 md"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m2n_test_")

    def _path(self, name):
        return os.path.join(self._tmp, name)

    def test_transcript_kept_structure_and_punct(self):
        """保结构清洗：段数不丢、标点乱码规范化（,,→,  ,.→.）"""
        out = clean_transcript_json(
            os.path.join(SAMPLE, "video_sample.json"), self._path("v_clean.json"))
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        segs = data["segments"]
        self.assertEqual(len(segs), 5, "6 段输入含 1 段重复（同文本同时间戳）→ 去重后应 5 段")
        self.assertNotIn(",，", segs[0]["text"], "标点乱码 ,, 应被规范化")
        self.assertNotIn("PowerShell对于AI不够友好 ,.", segs[1]["text"], ",. 应被规范化")
        self.assertTrue(any("中文教学讲解段永不删" in s["text"] for s in segs),
                        "中文教学段永不删")
        self.assertTrue(all("start_ms" in s for s in segs), "时间戳字段保留")

    def test_visual_timestamps_and_watermark(self):
        """画面清洗：时间戳保留、水印/标签删、GLM 描述保留"""
        out = clean_visual_timeline(
            os.path.join(SAMPLE, "video_sample_visual.txt"), self._path("v_clean.txt"))
        with open(out, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("[00:00]", txt, "时间戳保留")
        self.assertIn("[00:10]", txt, "末帧时间戳保留")
        self.assertNotIn("=====", txt, "帧标记删除")
        self.assertNotIn("[画面文字 OCR]", txt, "OCR 标签删除")
        self.assertNotIn("[GLM画面理解]", txt, "GLM 标签删除")
        self.assertNotIn("坚持打卡", txt, "界面水印删除")
        self.assertIn("厨房餐桌场景", txt, "GLM 描述保留")

    def test_interleave_has_speech_and_visual(self):
        """时间轴交错：同时含转写（🎤）和画面（🖼）"""
        cjson = clean_transcript_json(
            os.path.join(SAMPLE, "video_sample.json"), self._path("v_clean.json"))
        cvisual = clean_visual_timeline(
            os.path.join(SAMPLE, "video_sample_visual.txt"), self._path("v_clean.txt"))
        md = assemble_interleaved(cjson, cvisual, title="样例视频")
        self.assertIn("🎤", md, "转写带 🎤 标记")
        self.assertIn("🖼", md, "画面带 🖼 标记")
        self.assertGreater(md.count("🎤"), 0)
        self.assertGreater(md.count("🖼"), 0)


class TestAlbumBranch(unittest.TestCase):
    """分支2 图集：OCR txt → 清洗 md"""

    def test_album_clean(self):
        with open(os.path.join(SAMPLE, "album_sample.txt"), encoding="utf-8") as f:
            raw = f.read()
        out = clean_plain_text(raw)
        self.assertNotIn("坚持打卡", out, "界面水印删除")
        self.assertNotIn("点赞", out, "按钮碎片删除")
        self.assertNotIn("知识点", out, "界面词删除")
        self.assertIn("【图片1】", out, "图片序号保留")
        self.assertIn("Duncans are having dinner", out, "有效内容保留")
        self.assertIn("listen up means 认真听", out, "有效内容保留")


class TestTextBranch(unittest.TestCase):
    """分支3 文本：txt → 清洗 md"""

    def test_text_clean(self):
        with open(os.path.join(SAMPLE, "text_sample.txt"), encoding="utf-8") as f:
            raw = f.read()
        out = clean_plain_text(raw)
        self.assertNotIn("以上内容由AI生成", out, "AI 生成标记删除")
        self.assertNotIn("阅读全文", out, "阅读类 UI 删除")
        self.assertNotIn("相关推荐", out, "推荐类 UI 删除")
        self.assertIn("第一章 WSL 简介", out, "正文保留")
        self.assertIn("Windows Subsystem For Linux", out, "正文保留")


if __name__ == "__main__":
    unittest.main(verbosity=2)
