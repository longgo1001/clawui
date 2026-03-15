"""Tests for OCR fuzzy matching functionality."""

import pytest
from src.ocr_tool import _fuzzy_match, _levenshtein


class TestLevenshtein:
    def test_identical(self):
        assert _levenshtein("hello", "hello") == 0

    def test_empty(self):
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("abc", "") == 3

    def test_one_edit(self):
        assert _levenshtein("cat", "bat") == 1  # substitution
        assert _levenshtein("cat", "cats") == 1  # insertion
        assert _levenshtein("cats", "cat") == 1  # deletion

    def test_multiple_edits(self):
        assert _levenshtein("kitten", "sitting") == 3


class TestFuzzyMatch:
    def test_exact_substring(self):
        assert _fuzzy_match("OK", "Click OK to continue")

    def test_case_insensitive(self):
        assert _fuzzy_match("ok", "Click OK to continue")

    def test_ocr_zero_vs_o(self):
        # OCR commonly confuses O and 0
        assert _fuzzy_match("O0PS", "OOPS", max_distance=1)

    def test_ocr_l_vs_1(self):
        # OCR commonly confuses l and 1
        assert _fuzzy_match("he11o", "hello", max_distance=2)

    def test_no_match(self):
        assert not _fuzzy_match("completely", "different", max_distance=2)

    def test_empty_needle(self):
        assert _fuzzy_match("", "anything")

    def test_max_distance_zero_exact(self):
        assert _fuzzy_match("hello", "say hello", max_distance=0)

    def test_max_distance_zero_no_match(self):
        assert not _fuzzy_match("hell0", "say hello", max_distance=0)

    def test_chinese_text(self):
        assert _fuzzy_match("确认", "请点击确认按钮")

    def test_single_char_tolerance(self):
        # "Sbmit" vs "Submit" — one char off
        assert _fuzzy_match("Sbmit", "Submit", max_distance=1)


class TestOcrFindTextFuzzy:
    """Integration tests for ocr_find_text with fuzzy parameter."""

    def test_fuzzy_param_accepted(self):
        """Ensure ocr_find_text accepts fuzzy parameter without error."""
        from src.ocr_tool import ocr_find_text
        import base64
        # 1x1 white PNG
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()
        # Should not raise
        result = ocr_find_text(tiny_png, "test", fuzzy=True, max_edit_distance=2)
        assert isinstance(result, list)
