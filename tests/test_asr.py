#!/usr/bin/env python3
"""engines/asr.py 纯函数单元测试。

运行：python -m unittest tests.test_asr
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from engines.asr import (
    apply_corrections, merge_spaced_letters, merge_sensevoice_splits,
    clean_sensevoice, collapse_filler_repeats,
)


class TestApplyCorrections(unittest.TestCase):
    def test_ascii_word_boundary(self):
        corr = {"get up": "github"}
        self.assertEqual(apply_corrections("I get up early", corr),
                         "I github early")

    def test_ascii_no_partial_word(self):
        corr = {"up": "down"}
        # "upset" 中的 up 不应被替换（词边界守卫）
        self.assertEqual(apply_corrections("an upset guy", corr), "an upset guy")

    def test_case_insensitive_ascii(self):
        corr = {"ai": "AI"}
        self.assertEqual(apply_corrections("An AI tool and ai model", corr),
                         "An AI tool and AI model")

    def test_non_ascii_direct(self):
        corr = {"威而刚": "WSL"}
        self.assertEqual(apply_corrections("威而刚 是终极答案", corr),
                         "WSL 是终极答案")

    def test_empty(self):
        self.assertEqual(apply_corrections("", {"a": "b"}), "")


class TestMergeSpacedLetters(unittest.TestCase):
    def test_merge_continuous_letters(self):
        self.assertEqual(merge_spaced_letters("w s l"), "wsl")

    def test_sensevoice_syllable(self):
        self.assertEqual(merge_spaced_letters("O kay, go"), "Okay, go")

    def test_dont_merge_articles(self):
        self.assertEqual(merge_spaced_letters("a few A few"), "a few A few")


class TestMergeSensevoiceSplits(unittest.TestCase):
    def test_known_splits(self):
        self.assertEqual(merge_sensevoice_splits("W e are ready"), "We are ready")

    def test_unknown_untouched(self):
        self.assertEqual(merge_sensevoice_splits("X yz"), "X yz")


class TestCleanSensevoice(unittest.TestCase):
    def test_strip_tags(self):
        self.assertEqual(clean_sensevoice("<|zh|><|NEUTRAL|>你好"), "你好")

    def test_tags_with_spaces(self):
        self.assertEqual(clean_sensevoice("< | zh | > 哈喽"), "哈喽")

    def test_fold_repeated_punct(self):
        self.assertEqual(clean_sensevoice("好的，，然后。。"), "好的，然后。")

    def test_merge_letters_and_strip(self):
        self.assertEqual(clean_sensevoice(" <|zh|> W S L "), "WSL")


class TestCollapseFillerRepeats(unittest.TestCase):
    def test_chinese_filler(self):
        out = collapse_filler_repeats("嗯嗯嗯 对的")
        self.assertNotIn("嗯嗯嗯", out)

    def test_english_filler(self):
        out = collapse_filler_repeats("and and and then")
        self.assertNotIn("and and and", out)

    def test_meaningful_repeat_kept(self):
        out = collapse_filler_repeats("重要！重要！")
        self.assertIn("重要！重要！", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
