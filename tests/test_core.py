#!/usr/bin/env python3
"""core/{video,image,audio} 编排单元测试（mock 引擎/子进程，验证断点/失败/闭环）。

运行：python -m unittest tests.test_core
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
_SAMPLE = os.path.join(_ROOT, "tests", "sample")

from core.video import process_video
from core.audio import process_audio
from core.image import process_image


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestVideo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m2n_v_")
        self.video = os.path.join(self.tmp, "clip.mp4")
        _write(self.video, "fake video bytes")

    def test_missing_video(self):
        r = process_video(os.path.join(self.tmp, "nope.mp4"), out_root=self.tmp)
        self.assertIn("error", r)

    def test_resume_with_existing_products(self):
        """预置 json+visual → 断点跳过引擎 → 真实 clean+assemble → clean.md"""
        shutil.copy(os.path.join(_SAMPLE, "video_sample.json"),
                    os.path.join(self.tmp, "clip.json"))
        shutil.copy(os.path.join(_SAMPLE, "video_sample_visual.txt"),
                    os.path.join(self.tmp, "clip_visual.txt"))
        with mock.patch("core.video.ffmpeg.extract_audio", return_value=True):
            r = process_video(self.video, glm="no", out_root=self.tmp)
        self.assertIn("clean_md", r)
        self.assertTrue(os.path.isfile(r["clean_md"]))
        self.assertGreater(r["chars"], 0)

    def test_engine_failure_no_crash(self):
        """无产物 + 引擎失败 → 不崩溃，返回 dict"""
        cp = subprocess.CompletedProcess([], 0)
        with mock.patch("core.video.ffmpeg.extract_audio", return_value=True), \
             mock.patch("core.video._run", return_value=cp):
            r = process_video(self.video, glm="no", out_root=self.tmp)
        self.assertIsInstance(r, dict)


class TestAudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m2n_a_")
        self.audio = os.path.join(self.tmp, "voice.wav")
        _write(self.audio, "fake wav")

    def test_missing_audio(self):
        r = process_audio(os.path.join(self.tmp, "nope.wav"), out_root=self.tmp)
        self.assertIn("error", r)

    def test_resume_with_existing_json(self):
        shutil.copy(os.path.join(_SAMPLE, "video_sample.json"),
                    os.path.join(self.tmp, "voice.json"))
        r = process_audio(self.audio, out_root=self.tmp)
        self.assertTrue(os.path.isfile(r["clean_md"]))
        self.assertGreater(r["chars"], 0)

    def test_engine_failure_no_crash(self):
        cp = subprocess.CompletedProcess([], 0)
        with mock.patch("core.audio.subprocess.run", return_value=cp):
            r = process_audio(self.audio, out_root=self.tmp)
        self.assertIsInstance(r, dict)


class TestImage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m2n_i_")

    def test_empty_images(self):
        r = process_image([], out_root=self.tmp)
        self.assertIn("error", r)

    def test_glm_no(self):
        with mock.patch("core.image.ocr.ocr_images_to_text",
                        return_value=["画面文字A"]):
            r = process_image(["a.png"], glm="no", out_root=self.tmp)
        self.assertTrue(os.path.isfile(r["clean_md"]))
        self.assertEqual(r["images"], 1)
        with open(r["clean_md"], encoding="utf-8") as f:
            md = f.read()
        self.assertIn("画面文字A", md)
        self.assertNotIn("GLM画面理解", md)

    def test_glm_yes_adds_block(self):
        with mock.patch("core.image.ocr.ocr_images_to_text",
                        return_value=["画面文字A"]), \
             mock.patch("core.image._glm_describe", return_value="描述A"):
            r = process_image(["a.png"], glm="yes", out_root=self.tmp)
        with open(r["clean_md"], encoding="utf-8") as f:
            md = f.read()
        # 清洗规范：GLM 标签行删除，描述内容保留
        self.assertNotIn("GLM画面理解", md)
        self.assertIn("描述A", md)

    def test_glm_failure_no_crash(self):
        def _boom(_img):
            raise RuntimeError("glm 挂了")
        with mock.patch("core.image.ocr.ocr_images_to_text",
                        return_value=["画面文字A"]), \
             mock.patch("core.image._glm_describe", side_effect=_boom):
            r = process_image(["a.png"], glm="yes", out_root=self.tmp)
        self.assertTrue(os.path.isfile(r["clean_md"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
