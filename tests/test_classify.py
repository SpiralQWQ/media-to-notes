#!/usr/bin/env python3
"""cli.py _classify 单元测试：四模态识别 + 边界/防呆。

运行：python -m unittest tests.test_classify
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from cli import _classify


class TestClassify(unittest.TestCase):
    def test_video(self):
        for ext in (".mp4", ".webm", ".mkv", ".mov", ".flv", ".avi"):
            self.assertEqual(_classify(f"clip{ext}"), "video")

    def test_video_upper_case(self):
        self.assertEqual(_classify("CLIP.MP4"), "video")

    def test_image(self):
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
            self.assertEqual(_classify(f"pic{ext}"), "image")

    def test_audio(self):
        for ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"):
            self.assertEqual(_classify(f"voice{ext}"), "audio")

    def test_text(self):
        for ext in (".txt", ".md", ".markdown"):
            self.assertEqual(_classify(f"note{ext}"), "text")

    def test_nested_dir(self):
        self.assertEqual(_classify("x/y/z/我的视频.mp4"), "video")

    def test_no_ext(self):
        self.assertIsNone(_classify("video"))

    def test_unknown_ext(self):
        self.assertIsNone(_classify("setup.py"))
        self.assertIsNone(_classify("archive.zip"))

    def test_empty_string(self):
        self.assertIsNone(_classify(""))

    def test_none(self):
        self.assertIsNone(_classify(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
