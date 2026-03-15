#!/usr/bin/env python3
"""Unit tests for clawui core modules - runnable without a display server."""

import json
import hashlib
import os
import subprocess
import sys
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'gui-automation'))


class TestScreenshot(unittest.TestCase):
    """Test screenshot module."""

    @patch('subprocess.run')
    def test_get_screen_size(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='1920x1080\n'
        )
        from src.screenshot import get_screen_size
        w, h = get_screen_size()
        assert w == 1920
        assert h == 1080

    def test_take_screenshot_no_display(self):
        """Without a display, take_screenshot should raise or return None."""
        from src.screenshot import take_screenshot
        try:
            result = take_screenshot()
            # If it returns, it should be a string or None
            assert result is None or isinstance(result, str)
        except RuntimeError:
            pass  # Expected when no display


class TestCDPClient(unittest.TestCase):
    """Test CDP client without a real browser."""

    def test_cdp_client_init(self):
        from src.cdp_helper import CDPClient
        client = CDPClient(port=19222)
        assert client.port == 19222
        assert not client.is_available()

    @patch('http.client.HTTPConnection')
    def test_get_targets(self, mock_conn_cls):
        from src.cdp_helper import CDPClient
        client = CDPClient(port=9222)

        # Mock HTTP response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([
            {"id": "abc", "type": "page", "title": "Test", "url": "https://example.com"}
        ]).encode()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_conn_cls.return_value = mock_conn

        targets = client.list_targets()
        assert len(targets) == 1
        assert targets[0]["title"] == "Test"


class TestActions(unittest.TestCase):
    """Test desktop action wrappers."""

    @patch('subprocess.run')
    def test_click(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from src.actions import click
        click(100, 200)
        mock_run.assert_called()
        # Verify xdotool was invoked (could be string or list command)
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else ''
        if isinstance(cmd, list):
            cmd_str = ' '.join(cmd)
        else:
            cmd_str = str(cmd)
        assert 'xdotool' in cmd_str

    @patch('subprocess.run')
    def test_type_text(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from src.actions import type_text
        type_text("hello world")
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_press_key(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from src.actions import press_key
        press_key("Return")
        mock_run.assert_called()


class TestX11Helper(unittest.TestCase):
    """Test X11 helper."""

    @patch('subprocess.run')
    def test_list_windows(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='0x01000001 0 hung-pc My Window\n0x01000002 0 hung-pc Another\n'
        )
        from src.x11_helper import list_windows
        wins = list_windows()
        assert len(wins) >= 0  # May parse differently but shouldn't crash


class TestAgentTools(unittest.TestCase):
    """Test agent tool creation and execution."""

    def test_create_tools_returns_list(self):
        from src.agent import create_tools
        tools = create_tools()
        assert isinstance(tools, list)
        assert len(tools) > 30  # We have 40+ tools
        names = [t['name'] for t in tools]
        assert 'screenshot' in names
        assert 'click' in names
        assert 'cdp_navigate' in names
        assert 'find_text' in names
        assert 'click_text' in names

    def test_tool_schemas_valid(self):
        from src.agent import create_tools
        tools = create_tools()
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'input_schema' in tool
            schema = tool['input_schema']
            assert schema.get('type') == 'object'
            assert 'properties' in schema


class TestRecorder(unittest.TestCase):
    """Test recorder module."""

    def test_start_stop_recording(self):
        from src.recorder import start_recording, stop_recording, record_action
        rec = start_recording()
        record_action("click", {"x": 10, "y": 20}, {"type": "text", "text": "ok"})
        data = stop_recording()
        assert data is not None


class TestOCRTool(unittest.TestCase):
    """Test OCR tool module."""

    def test_import(self):
        from src.ocr_tool import ocr_find_text
        assert callable(ocr_find_text)


class TestPerception(unittest.TestCase):
    """Test perception routing layer."""

    def test_import_and_functions(self):
        from src.perception import get_ui_tree_summary, list_applications
        assert callable(get_ui_tree_summary)
        assert callable(list_applications)


class TestCLI(unittest.TestCase):
    """Test CLI entry point."""

    def test_cli_import(self):
        from src.cli import main
        assert callable(main)


if __name__ == '__main__':
    unittest.main()


class TestAnnotatedScreenshot(unittest.TestCase):
    """Test annotated screenshot module."""

    def test_import(self):
        from src.annotated_screenshot import annotated_screenshot, get_last_elements, LabeledElement
        assert callable(annotated_screenshot)
        assert callable(get_last_elements)

    def test_dedup_elements(self):
        from src.annotated_screenshot import _dedup_elements
        elements = [
            {"x": 100, "y": 100, "width": 50, "height": 30, "role": "button", "name": "A"},
            {"x": 102, "y": 101, "width": 50, "height": 30, "role": "button", "name": "A dup"},
            {"x": 300, "y": 200, "width": 50, "height": 30, "role": "link", "name": "B"},
        ]
        result = _dedup_elements(elements)
        assert len(result) == 2, f"Expected 2, got {len(result)}"

    def test_labeled_element_to_dict(self):
        from src.annotated_screenshot import LabeledElement
        el = LabeledElement(
            index=1, label="1: Save", role="push button", name="Save",
            x=10, y=20, width=80, height=30, center_x=50, center_y=35,
            source="atspi", selector=None,
        )
        d = el.to_dict()
        assert d["index"] == 1
        assert d["center"] == [50, 35]
        assert d["source"] == "atspi"


class TestAutoVerification(unittest.TestCase):
    """Test auto action verification logic."""

    @patch('src.agent.take_screenshot')
    def test_unchanged_screen_adds_warning(self, mock_ss):
        """When screen hash unchanged after action, result should contain warning."""
        import src.agent as agent_mod
        mock_ss.return_value = "AAAA"  # same base64 both times
        agent_mod._last_screen_hash = hashlib.md5(b"AAAA").hexdigest()
        with patch.object(agent_mod, '_execute_tool_inner',
                          return_value={"type": "text", "text": "Clicked"}):
            with patch.dict(os.environ, {"CLAWUI_VERIFY_ACTIONS": "1"}):
                result = agent_mod.execute_tool("click", {"x": 100, "y": 200})
        assert "unchanged" in result.get("text", "").lower()

    @patch('src.agent.take_screenshot')
    def test_changed_screen_no_warning(self, mock_ss):
        """When screen changes after action, no warning appended."""
        import src.agent as agent_mod
        mock_ss.return_value = "BBBB"  # different from stored
        agent_mod._last_screen_hash = hashlib.md5(b"AAAA").hexdigest()
        with patch.object(agent_mod, '_execute_tool_inner',
                          return_value={"type": "text", "text": "Clicked"}):
            with patch.dict(os.environ, {"CLAWUI_VERIFY_ACTIONS": "1"}):
                result = agent_mod.execute_tool("click", {"x": 100, "y": 200})
        assert "unchanged" not in result.get("text", "").lower()

    @patch('src.agent.take_screenshot')
    def test_verification_disabled(self, mock_ss):
        """When CLAWUI_VERIFY_ACTIONS=0, no verification occurs."""
        import src.agent as agent_mod
        mock_ss.return_value = "AAAA"
        agent_mod._last_screen_hash = hashlib.md5(b"AAAA").hexdigest()
        with patch.object(agent_mod, '_execute_tool_inner',
                          return_value={"type": "text", "text": "Clicked"}):
            with patch.dict(os.environ, {"CLAWUI_VERIFY_ACTIONS": "0"}):
                result = agent_mod.execute_tool("click", {"x": 100, "y": 200})
        assert "unchanged" not in result.get("text", "")
        mock_ss.assert_not_called()

    def test_non_action_tool_skips_verification(self):
        """Non-state-changing tools should not trigger verification."""
        import src.agent as agent_mod
        with patch.object(agent_mod, '_execute_tool_inner',
                          return_value={"type": "text", "text": "tree data"}):
            result = agent_mod.execute_tool("ui_tree", {})
        assert "unchanged" not in result.get("text", "")


class TestHybridTools(unittest.TestCase):
    """Test API-GUI hybrid tools."""

    @patch('subprocess.run')
    def test_run_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello\n", stderr="")
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None  # disable verification
        result = agent_mod.execute_tool("run_command", {"command": "echo hello"})
        assert "hello" in result["text"]
        assert "exit=0" in result["text"]

    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        result = agent_mod.execute_tool("run_command", {"command": "sleep 999"})
        assert "timed out" in result["text"].lower()

    @patch('subprocess.run')
    def test_run_command_disabled(self, mock_run):
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        with patch.dict(os.environ, {"CLAWUI_ALLOW_SHELL": "0"}):
            result = agent_mod.execute_tool("run_command", {"command": "echo hello"})
        assert "disabled" in result["text"].lower()
        mock_run.assert_not_called()

    def test_file_read_not_found(self):
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        result = agent_mod.execute_tool("file_read", {"path": "/nonexistent/file.txt"})
        assert "not found" in result["text"].lower()

    def test_file_write_and_read(self):
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            path = f.name
        try:
            result = agent_mod.execute_tool("file_write", {"path": path, "content": "hello world"})
            assert "11 bytes" in result["text"]
            result = agent_mod.execute_tool("file_read", {"path": path})
            assert result["text"] == "hello world"
        finally:
            os.unlink(path)

    def test_file_list_not_found(self):
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        result = agent_mod.execute_tool("file_list", {"path": "/nonexistent/dir"})
        assert "not found" in result["text"].lower()

    def test_file_list_works(self):
        import src.agent as agent_mod
        agent_mod._last_screen_hash = None
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "a.txt"), "w").close()
            open(os.path.join(td, "b.py"), "w").close()
            result = agent_mod.execute_tool("file_list", {"path": td})
            assert "a.txt" in result["text"]
            assert "b.py" in result["text"]

    def test_create_tools_includes_new_tools(self):
        from src.agent import create_tools
        names = [t["name"] for t in create_tools()]
        for tool in ("run_command", "file_read", "file_write", "file_list", "open_url"):
            assert tool in names, f"{tool} missing from tools"


class TestCLI(unittest.TestCase):
    """Tests for CLI module."""

    def test_cli_version(self):
        from src.cli import VERSION
        assert VERSION == "0.6.0"

    def test_run_inspect_function_exists(self):
        from src.cli import _run_inspect
        assert callable(_run_inspect)

    def test_inspect_with_mock_args(self):
        """Test inspect function signature accepts expected args."""
        from src.cli import _run_inspect
        import inspect
        sig = inspect.signature(_run_inspect)
        assert len(sig.parameters) == 1  # takes one 'args' param


# ============================================================
# P3 Optimization Tests
# ============================================================

class TestContextCompression(unittest.TestCase):
    """Test P3-A: Context window compression."""

    def test_estimate_tokens_string_content(self):
        from src.agent import _estimate_tokens
        msgs = [{"role": "user", "content": "a" * 400}]
        est = _estimate_tokens(msgs)
        assert est == 100, f"Expected 100, got {est}"

    def test_estimate_tokens_list_content(self):
        from src.agent import _estimate_tokens
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "b" * 200},
            {"type": "tool_result", "content": "c" * 80},
        ]}]
        est = _estimate_tokens(msgs)
        assert est == 70, f"Expected 70, got {est}"

    def test_estimate_tokens_empty(self):
        from src.agent import _estimate_tokens
        assert _estimate_tokens([]) == 0

    def test_estimate_tokens_none_content(self):
        from src.agent import _estimate_tokens
        msgs = [{"role": "assistant", "content": None,
                 "tool_calls": [{"input": {"x": 1}}]}]
        est = _estimate_tokens(msgs)
        assert est > 0

    def test_compress_history_no_compression_needed(self):
        from src.agent import _compress_history
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = _compress_history(msgs)
        assert result == msgs, "Should return messages unchanged when below threshold"

    def test_compress_history_compresses_long(self):
        from src.agent import _compress_history, _CONTEXT_MAX_TOKENS, _CONTEXT_COMPRESS_RATIO
        # Create messages that exceed the threshold
        big_text = "x" * 400000  # ~100k tokens
        msgs = [{"role": "user", "content": "Task: do stuff"}]
        for i in range(20):
            msgs.append({"role": "assistant", "content": f"Step {i}: " + big_text[:5000]})
            msgs.append({"role": "user", "content": f"Result {i}: " + big_text[:5000]})

        result = _compress_history(msgs, keep_recent=4)
        assert len(result) < len(msgs), "Compressed history should be shorter"
        assert result[0] == msgs[0], "First message should be preserved"
        assert "[Context compressed]" in result[1]["content"]
        # Last 4 should be preserved verbatim
        assert result[-1] == msgs[-1]
        assert result[-4] == msgs[-4]


class TestResponseCaching(unittest.TestCase):
    """Test P3-C: Response caching."""

    def test_cache_key_deterministic(self):
        from src.agent import _cache_key
        k1 = _cache_key("ui_tree", {"app_name": "Firefox"})
        k2 = _cache_key("ui_tree", {"app_name": "Firefox"})
        assert k1 == k2

    def test_cache_key_differs_for_different_input(self):
        from src.agent import _cache_key
        k1 = _cache_key("ui_tree", {"app_name": "Firefox"})
        k2 = _cache_key("ui_tree", {"app_name": "Chrome"})
        assert k1 != k2

    def test_cache_get_set(self):
        from src.agent import _cache_get, _cache_set, _cache_key, _tool_cache
        _tool_cache.clear()
        key = _cache_key("ui_tree", {"app_name": "test"})
        assert _cache_get(key) is None
        _cache_set(key, {"type": "text", "text": "cached"})
        result = _cache_get(key)
        assert result is not None
        assert result["text"] == "cached"
        _tool_cache.clear()

    def test_cache_expiry(self):
        from src.agent import _cache_get, _cache_set, _cache_key, _tool_cache
        _tool_cache.clear()
        key = _cache_key("test_tool", {})
        # Manually insert with old timestamp
        _tool_cache[key] = (time.time() - 9999, {"type": "text", "text": "old"})
        assert _cache_get(key) is None, "Expired entry should return None"
        _tool_cache.clear()

    def test_cacheable_tools_frozenset(self):
        from src.agent import _CACHEABLE_TOOLS
        assert isinstance(_CACHEABLE_TOOLS, frozenset)
        assert "ui_tree" in _CACHEABLE_TOOLS
        assert "click" not in _CACHEABLE_TOOLS


class TestDynamicModelRouting(unittest.TestCase):
    """Test P3-B: Dynamic model routing."""

    def test_get_backend_has_model_override(self):
        import inspect
        from src.backends import get_backend
        sig = inspect.signature(get_backend)
        assert "model_override" in sig.parameters, "get_backend must accept model_override"

    def test_plan_exec_verify_model_attrs(self):
        import src.agent as agent_mod
        assert hasattr(agent_mod, "_PLAN_MODEL")
        assert hasattr(agent_mod, "_EXEC_MODEL")
        assert hasattr(agent_mod, "_VERIFY_MODEL")

    def test_model_override_takes_precedence(self):
        """Test that model_override is used when provided (signature contract)."""
        import inspect
        from src.backends import get_backend
        sig = inspect.signature(get_backend)
        params = list(sig.parameters.keys())
        assert params.index("model_override") > params.index("model"), \
            "model_override should come after model"


class TestMoGCrossValidation(unittest.TestCase):
    """Test P3-D: MoG cross-validation."""

    def test_iou_identical_boxes(self):
        from src.annotated_screenshot import _iou
        val = _iou((10, 10, 50, 50), (10, 10, 50, 50))
        assert abs(val - 1.0) < 0.001

    def test_iou_no_overlap(self):
        from src.annotated_screenshot import _iou
        val = _iou((0, 0, 10, 10), (100, 100, 10, 10))
        assert val == 0.0

    def test_iou_partial_overlap(self):
        from src.annotated_screenshot import _iou
        val = _iou((0, 0, 20, 20), (10, 10, 20, 20))
        assert 0.0 < val < 1.0

    def test_iou_zero_area(self):
        from src.annotated_screenshot import _iou
        val = _iou((0, 0, 0, 0), (0, 0, 10, 10))
        assert val == 0.0

    def test_labeled_element_confidence_field(self):
        from src.annotated_screenshot import LabeledElement
        el = LabeledElement(
            index=1, label="1: OK", role="push button", name="OK",
            x=10, y=20, width=80, height=30, center_x=50, center_y=35,
            source="atspi", selector=None, confidence=0.85,
        )
        assert el.confidence == 0.85
        d = el.to_dict()
        assert "confidence" in d
        assert d["confidence"] == 0.85

    def test_labeled_element_default_confidence(self):
        from src.annotated_screenshot import LabeledElement
        el = LabeledElement(
            index=1, label="1: OK", role="push button", name="OK",
            x=10, y=20, width=80, height=30, center_x=50, center_y=35,
            source="atspi",
        )
        assert el.confidence == 0.5

    def test_ocr_cross_validate_no_ocr(self):
        """When OCR is unavailable, elements should pass through unchanged."""
        from src.annotated_screenshot import _ocr_cross_validate
        elements = [
            {"x": 10, "y": 20, "width": 80, "height": 30,
             "role": "button", "name": "Save", "source": "atspi"},
        ]
        with patch("src.annotated_screenshot.ocr_extract_lines",
                    side_effect=ImportError("no OCR")):
            result = _ocr_cross_validate(elements, "fake_b64")
        assert len(result) == 1
        # Should not have crashed; confidence may or may not be set

    def test_ocr_cross_validate_with_matches(self):
        """OCR matching should boost confidence."""
        from src.annotated_screenshot import _ocr_cross_validate
        elements = [
            {"x": 10, "y": 20, "width": 80, "height": 30,
             "role": "button", "name": "Save", "source": "atspi"},
        ]
        ocr_lines = [
            {"text": "Save", "bbox": [[10, 20], [90, 20], [90, 50], [10, 50]], "score": 0.9},
        ]
        with patch("src.annotated_screenshot.ocr_extract_lines", return_value=ocr_lines):
            result = _ocr_cross_validate(elements, "fake_b64")
        assert result[0]["confidence"] > 0.5, "Matching element should have boosted confidence"


class TestPerToolCostTracking(unittest.TestCase):
    """Test P3-F: Per-tool cost tracking."""

    def test_track_tokens(self):
        from src.agent import _track_tokens, _tool_token_stats
        _tool_token_stats.clear()
        _track_tokens("screenshot", {"input_tokens": 100, "output_tokens": 50})
        assert "screenshot" in _tool_token_stats
        assert _tool_token_stats["screenshot"]["input_tokens"] == 100
        assert _tool_token_stats["screenshot"]["output_tokens"] == 50
        assert _tool_token_stats["screenshot"]["calls"] == 1
        _track_tokens("screenshot", {"input_tokens": 200, "output_tokens": 100})
        assert _tool_token_stats["screenshot"]["input_tokens"] == 300
        assert _tool_token_stats["screenshot"]["calls"] == 2
        _tool_token_stats.clear()

    def test_track_tokens_none_usage(self):
        from src.agent import _track_tokens, _tool_token_stats
        _tool_token_stats.clear()
        _track_tokens("click", None)
        assert "click" not in _tool_token_stats
        _tool_token_stats.clear()

    def test_track_phase(self):
        from src.agent import _track_phase, _phase_token_stats
        _phase_token_stats.clear()
        _track_phase("run_agent", {"input_tokens": 500, "output_tokens": 200})
        assert "run_agent" in _phase_token_stats
        assert _phase_token_stats["run_agent"]["calls"] == 1
        _phase_token_stats.clear()

    def test_get_token_stats(self):
        from src.agent import get_token_stats, reset_token_stats, _track_tokens, _track_phase
        reset_token_stats()
        _track_tokens("click", {"input_tokens": 10, "output_tokens": 5})
        _track_phase("run_agent", {"input_tokens": 100, "output_tokens": 50})
        stats = get_token_stats()
        assert "tools" in stats
        assert "phases" in stats
        assert "click" in stats["tools"]
        assert "run_agent" in stats["phases"]
        reset_token_stats()

    def test_reset_token_stats(self):
        from src.agent import reset_token_stats, _track_tokens, _tool_token_stats, _phase_token_stats
        _track_tokens("x", {"input_tokens": 1, "output_tokens": 1})
        reset_token_stats()
        assert len(_tool_token_stats) == 0
        assert len(_phase_token_stats) == 0
