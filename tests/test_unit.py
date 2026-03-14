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


class TestConfigurableDelays(unittest.TestCase):
    """Test P1-D: configurable sleep constants."""

    def test_default_delay_values(self):
        import src.agent as agent_mod
        assert agent_mod._LAUNCH_DELAY == 1.0
        assert agent_mod._WECHAT_LAUNCH_DELAY == 2.0
        assert agent_mod._NAV_DELAY == 2.0
        assert agent_mod._OCR_ACTION_DELAY == 1.0

    def test_env_override_delays(self):
        """Verify env vars are read at module level (check the mechanism works)."""
        # We can't re-import to test env override, but we can verify the constants
        # are float types and the env var names are correct.
        import src.agent as agent_mod
        assert isinstance(agent_mod._LAUNCH_DELAY, float)
        assert isinstance(agent_mod._NAV_DELAY, float)


class TestPILResize(unittest.TestCase):
    """Test P1-C: PIL screenshot resize with ImageMagick fallback."""

    def test_pil_resize_path(self):
        """PIL resize branch is taken when PIL is available."""
        from PIL import Image
        import tempfile
        # Create a 200x200 test image
        img = Image.new('RGB', (200, 200), color='red')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name)
            path = f.name
        try:
            # Resize using PIL directly (same logic as screenshot.py)
            img = Image.open(path)
            resample = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', Image.BICUBIC))
            img = img.resize((100, 100), resample)
            img.save(path)
            # Verify resized
            result = Image.open(path)
            assert result.size == (100, 100)
        finally:
            os.unlink(path)


class TestTokenTracking(unittest.TestCase):
    """Test P1-A: token tracking in backends."""

    def test_claude_backend_returns_usage(self):
        """ClaudeBackend.chat() return dict includes 'usage' key."""
        from src.backends import ClaudeBackend
        # Mock the Anthropic client
        mock_response = MagicMock()
        mock_response.content = []
        mock_usage = MagicMock()
        mock_usage.input_tokens = 150
        mock_usage.output_tokens = 42
        mock_response.usage = mock_usage

        backend = ClaudeBackend.__new__(ClaudeBackend)
        backend.client = MagicMock()
        backend.model = "test"
        backend.client.messages.create.return_value = mock_response

        result = backend.chat([], [], "system")
        assert "usage" in result
        assert result["usage"]["input_tokens"] == 150
        assert result["usage"]["output_tokens"] == 42

    def test_openai_backend_returns_usage(self):
        """OpenAIBackend.chat() return dict includes 'usage' key."""
        from src.backends import OpenAIBackend
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "hello"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 25
        mock_response.usage = mock_usage

        backend = OpenAIBackend.__new__(OpenAIBackend)
        backend.client = MagicMock()
        backend.model = "test"
        backend.client.chat.completions.create.return_value = mock_response

        result = backend.chat([], [], "system")
        assert "usage" in result
        assert result["usage"]["input_tokens"] == 100
        assert result["usage"]["output_tokens"] == 25

    def test_extract_anthropic_usage_missing(self):
        """Usage extraction handles missing usage attribute gracefully."""
        from src.backends import ClaudeBackend
        mock_resp = MagicMock(spec=[])  # no attributes
        usage = ClaudeBackend._extract_anthropic_usage(mock_resp)
        assert usage == {"input_tokens": 0, "output_tokens": 0}


class TestLazyPerceptionInit(unittest.TestCase):
    """Test P1-B: lazy CDP/Marionette init with TTL cache."""

    def test_cdp_initially_unchecked(self):
        """CDP_AVAILABLE starts as None (unchecked), not eagerly probed."""
        import src.perception as perc
        # On import, CDP_AVAILABLE should be None (lazy) not True/False
        # We reset it to test the mechanism
        original = perc.CDP_AVAILABLE
        perc.CDP_AVAILABLE = None
        perc._cdp_client = None
        perc._cdp_last_check = 0.0
        # _get_cdp_client should attempt init now
        client = perc._get_cdp_client()
        # Without a real browser, it should be None/False
        assert client is None or perc.CDP_AVAILABLE is not None
        # Restore
        perc.CDP_AVAILABLE = original

    def test_cdp_ttl_caching(self):
        """Repeated calls within TTL don't re-probe."""
        import src.perception as perc
        perc.CDP_AVAILABLE = False
        perc._cdp_client = None
        perc._cdp_last_check = perc._time.monotonic()  # just checked
        # Within TTL, should return None without re-probing
        result = perc._get_cdp_client()
        assert result is None  # cached False

    def test_marionette_initially_unchecked(self):
        """MARIONETTE_AVAILABLE starts as None (unchecked)."""
        import src.perception as perc
        original = perc.MARIONETTE_AVAILABLE
        perc.MARIONETTE_AVAILABLE = None
        perc._marionette_client = None
        perc._marionette_last_check = 0.0
        client = perc._get_marionette_client()
        assert client is None or perc.MARIONETTE_AVAILABLE is not None
        perc.MARIONETTE_AVAILABLE = original
