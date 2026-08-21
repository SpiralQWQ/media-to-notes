#!/usr/bin/env python3
"""engines/ocr.py 纯函数单元测试（不依赖 cv2）。

运行：python -m unittest tests.test_ocr
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from engines.ocr import fmt_ts, _ocr_reading_order


def _box(x, y, w=20, h=20):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


class TestFmtTs(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(fmt_ts(0), "00:00")

    def test_seconds(self):
        self.assertEqual(fmt_ts(59), "00:59")

    def test_minutes(self):
        self.assertEqual(fmt_ts(60), "01:00")

    def test_hour(self):
        self.assertEqual(fmt_ts(3661), "61:01")

    def test_float_truncated(self):
        self.assertEqual(fmt_ts(61.9), "01:01")

    def test_negative_no_crash(self):
        self.assertIsInstance(fmt_ts(-1), str)


class TestOcrReadingOrder(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_ocr_reading_order([]), "")

    def test_blank_text_filtered(self):
        items = [[_box(0, 0), "   ", 0.9]]
        self.assertEqual(_ocr_reading_order(items), "")

    def test_row_left_to_right(self):
        # 同行内 x 乱序 → 左→右拼接
        items = [
            [_box(200, 0), "右", 0.9],
            [_box(100, 0), "左", 0.9],
        ]
        self.assertEqual(_ocr_reading_order(items), "左 右")

    def test_rows_top_to_bottom(self):
        # 上排/下排按 y 分行；下排 y=100 与上排 y=0 差 >40 → 分行
        items = [
            [_box(50, 100), "下", 0.9],
            [_box(0, 0), "上", 0.9],
        ]
        self.assertEqual(_ocr_reading_order(items), "上\n下")

    def test_same_row_within_40px(self):
        items = [
            [_box(200, 30), "右", 0.9],
            [_box(0, 0), "左", 0.9],
        ]
        self.assertEqual(_ocr_reading_order(items), "左 右")

    def test_mixed_full_scene(self):
        items = [
            [_box(50, 100), "下", 0.9],
            [_box(200, 0), "右", 0.9],
            [_box(100, 0), "左", 0.9],
        ]
        self.assertEqual(_ocr_reading_order(items), "左 右\n下")


if __name__ == "__main__":
    unittest.main(verbosity=2)
