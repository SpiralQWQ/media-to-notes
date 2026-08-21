#!/usr/bin/env python3
"""core/base.py 单元测试：human_size 边界 + write_text 往返。

运行：python -m unittest tests.test_base
"""
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from core.base import human_size, write_text


class TestHumanSize(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(human_size(0), "0K")

    def test_byte(self):
        self.assertEqual(human_size(1), "0K")

    def test_exact_kb(self):
        self.assertEqual(human_size(1024), "1K")

    def test_just_below_mb(self):
        # 1048575 字节 → 0.9999M < 1 → 走 K 分支
        self.assertEqual(human_size(1048575), "1023K")

    def test_exact_mb(self):
        self.assertEqual(human_size(1048576), "1.0M")

    def test_frac_mb(self):
        self.assertEqual(human_size(1572864), "1.5M")

    def test_large(self):
        self.assertEqual(human_size(1073741824), "1024.0M")

    def test_negative(self):
        # 负数不应崩溃，落在 K 分支
        self.assertEqual(human_size(-1024), "-1K")


class TestWriteText(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m2n_base_")

    def test_roundtrip(self):
        p = os.path.join(self._tmp, "a.txt")
        write_text(p, "你好 media-to-notes")
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), "你好 media-to-notes")

    def test_nested_parent_autocreated(self):
        p = os.path.join(self._tmp, "x", "y", "z.md")
        write_text(p, "nested")
        self.assertTrue(os.path.isfile(p))

    def test_empty_text(self):
        p = os.path.join(self._tmp, "empty.txt")
        write_text(p, "")
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
