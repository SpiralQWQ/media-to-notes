#!/usr/bin/env python3
"""assemble/album + assemble/timeline 单元测试。

运行：python -m unittest tests.test_assemble
"""
import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from assemble.album import assemble_album
from assemble.timeline import assemble_timeline


class TestAlbum(unittest.TestCase):
    def test_empty_returns_blank(self):
        self.assertEqual(assemble_album(""), "")
        self.assertEqual(assemble_album(None), "")

    def test_whitespace_only_returns_blank(self):
        self.assertEqual(assemble_album("   \n  "), "")

    def test_no_title(self):
        out = assemble_album("【图1】abc\n【图2】def")
        self.assertFalse(out.startswith("# "))
        self.assertIn("## 🖼️ 图集", out)
        self.assertLess(out.index("【图1】"), out.index("【图2】"))

    def test_with_title(self):
        out = assemble_album("【图1】abc", title="我的图集")
        self.assertTrue(out.startswith("# 我的图集"))
        self.assertIn("## 🖼️ 图集", out)

    def test_keeps_blocks_order(self):
        blocks = "\n\n".join(f"【图{i}】内容{i}" for i in range(1, 6))
        out = assemble_album(blocks)
        idxs = [out.index(f"【图{i}】") for i in range(1, 6)]
        self.assertEqual(idxs, sorted(idxs))


class TestTimeline(unittest.TestCase):
    def _write(self, data):
        fd, path = tempfile.mkstemp(suffix=".json", prefix="m2n_tl_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path

    def test_timestamps_format(self):
        data = {"sentences": [
            {"text": "第一句", "start_ms": 0},
            {"text": "第二句", "start_ms": 61234},
            {"text": "第三句", "start_ms": 6600000},
        ]}
        out = assemble_timeline(self._write(data))
        self.assertIn("[00:00] 🎤 第一句", out)
        self.assertIn("[01:01] 🎤 第二句", out)
        self.assertIn("[110:00] 🎤 第三句", out)
        self.assertIn("## 🎧 转写", out)

    def test_sorted_by_time(self):
        data = {"sentences": [
            {"text": "后", "start_ms": 9000},
            {"text": "先", "start_ms": 1000},
        ]}
        out = assemble_timeline(self._write(data))
        self.assertLess(out.index("[00:01]"), out.index("[00:09]"))

    def test_empty_text_skipped(self):
        data = {"sentences": [
            {"text": "  ", "start_ms": 100},
            {"text": "有效", "start_ms": 2000},
        ]}
        out = assemble_timeline(self._write(data))
        self.assertNotIn("[00:00]", out)
        self.assertIn("[00:02] 🎤 有效", out)

    def test_no_valid_sentence_raises(self):
        data = {"sentences": [{"text": "  ", "start_ms": 1}]}
        with self.assertRaises(ValueError):
            assemble_timeline(self._write(data))

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            assemble_timeline(os.path.join(tempfile.gettempdir(), "no_such_m2n.json"))

    def test_non_dict_data_raises(self):
        with self.assertRaises(ValueError):
            assemble_timeline(self._write([1, 2]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
