"""Tests for ClawUI CLI module.

Covers argument parsing, subcommand dispatch, and output formatting
for doctor, status, selftest, version, config, and other subcommands.
"""

import importlib
import json
import os
import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*argv: str, expect_exit: bool = False) -> int:
    """Import cli.main() and run it with the given argv, returning exit code.

    If expect_exit is True, re-raises SystemExit so callers can assert on it.
    """
    from clawui.cli import main
    with patch("sys.argv", ["clawui", *argv]):
        try:
            return main() or 0
        except SystemExit as exc:
            if expect_exit:
                raise
            return exc.code if exc.code is not None else 0


# ---------------------------------------------------------------------------
# version / help
# ---------------------------------------------------------------------------

class TestVersionHelp:
    def test_version_subcommand(self, capsys):
        rc = _run_cli("version")
        assert rc == 0
        out = capsys.readouterr().out
        assert "clawui" in out.lower()

    def test_version_flag(self):
        """--version should cause SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            _run_cli("--version", expect_exit=True)
        assert exc_info.value.code == 0

    def test_no_command_shows_help(self, capsys):
        """Running with no subcommand should print help and return 0."""
        rc = _run_cli()
        assert rc == 0
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "clawui" in out.lower()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

class TestDoctor:
    """Test the doctor subcommand (environment diagnostics)."""

    def test_doctor_runs(self, capsys):
        """Doctor should complete without crashing."""
        rc = _run_cli("doctor")
        out = capsys.readouterr().out
        assert "ClawUI Doctor" in out
        assert rc in (0, 1)  # 1 is OK if issues found

    def test_doctor_checks_display(self, capsys):
        rc = _run_cli("doctor")
        out = capsys.readouterr().out
        assert "Display Server" in out or "display" in out.lower()

    def test_doctor_checks_python_deps(self, capsys):
        rc = _run_cli("doctor")
        out = capsys.readouterr().out
        assert "Python" in out

    def test_doctor_checks_x11_tools(self, capsys):
        rc = _run_cli("doctor")
        out = capsys.readouterr().out
        assert "X11" in out

    def test_doctor_fix_flag_accepted(self, capsys):
        """--fix flag should be accepted (may or may not fix anything)."""
        rc = _run_cli("doctor", "--fix")
        out = capsys.readouterr().out
        assert "ClawUI Doctor" in out


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestStatus:
    """Test the status subcommand (runtime health)."""

    def test_status_runs(self, capsys):
        rc = _run_cli("status")
        out = capsys.readouterr().out
        assert "ClawUI" in out
        assert rc == 0

    def test_status_json(self, capsys):
        rc = _run_cli("status", "--json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "version" in data
        assert "backends" in data
        assert rc == 0

    def test_status_json_has_backends(self, capsys):
        _run_cli("status", "--json")
        data = json.loads(capsys.readouterr().out)
        backends = data["backends"]
        for key in ("atspi", "x11", "cdp", "marionette", "screenshot", "ocr"):
            assert key in backends, f"Missing backend: {key}"


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

class TestConfig:
    """Test config subcommands."""

    def test_config_path(self, capsys):
        rc = _run_cli("config", "path")
        out = capsys.readouterr().out.strip()
        assert "config" in out.lower()
        assert rc == 0

    def test_config_show_no_file(self, capsys):
        """Show should work even when no config file exists."""
        rc = _run_cli("config", "show")
        assert rc == 0

    def test_config_get_unset(self, capsys):
        rc = _run_cli("config", "get", "NONEXISTENT_KEY_12345")
        out = capsys.readouterr().out.strip()
        assert "not set" in out.lower()
        assert rc == 0

    def test_config_init(self, capsys, tmp_path, monkeypatch):
        """config init should create a file."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        # Clear cached config path if any
        import clawui.config as cfg_mod
        if hasattr(cfg_mod, "_config_cache"):
            cfg_mod._config_cache = {}
        rc = _run_cli("config", "init")
        assert rc == 0

    def test_config_no_action(self, capsys):
        """config with no subaction should print usage."""
        rc = _run_cli("config")
        assert rc == 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

class TestSelftest:
    """Test the selftest subcommand."""

    def test_selftest_quick(self, capsys):
        """Quick selftest should run without browser tests."""
        rc = _run_cli("selftest", "--quick")
        out = capsys.readouterr().out
        assert "Self-Test" in out
        assert "Browser tests skipped" in out
        assert rc in (0, 1)

    def test_selftest_step_timeout(self, capsys):
        """Custom step-timeout should be accepted."""
        rc = _run_cli("selftest", "--quick", "--step-timeout", "5")
        out = capsys.readouterr().out
        assert "Self-Test" in out


# ---------------------------------------------------------------------------
# Argument parsing edge cases
# ---------------------------------------------------------------------------

class TestArgParsing:
    """Test CLI argument parsing for various subcommands."""

    def test_run_requires_task(self):
        """'clawui run' without a task should error."""
        with pytest.raises(SystemExit) as exc_info:
            _run_cli("run", expect_exit=True)
        assert exc_info.value.code == 2

    def test_click_no_args_shows_usage(self, capsys):
        """'clawui click' with no args should show usage."""
        rc = _run_cli("click")
        err = capsys.readouterr().err
        assert "Usage" in err or "clawui click" in err
        assert rc == 1

    def test_wait_requires_text_or_element(self):
        """'clawui wait' without --text or --element should error."""
        with pytest.raises(SystemExit):
            _run_cli("wait", expect_exit=True)

    def test_log_level_flag(self, capsys):
        """--log-level should be accepted globally."""
        rc = _run_cli("--log-level", "debug", "version")
        assert rc == 0


# ---------------------------------------------------------------------------
# _run_doctor internals (unit-level)
# ---------------------------------------------------------------------------

class TestDoctorInternals:
    """Unit tests for doctor helper functions."""

    def test_doctor_without_display(self, capsys, monkeypatch):
        """Doctor should report issue when no display is set."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        rc = _run_cli("doctor")
        out = capsys.readouterr().out
        assert "issue" in out.lower() or "not set" in out.lower() or "No display" in out


# ---------------------------------------------------------------------------
# inspect (basic smoke)
# ---------------------------------------------------------------------------

class TestInspect:
    def test_inspect_json(self, capsys):
        """Inspect --json should produce valid JSON."""
        rc = _run_cli("inspect", "--json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "timestamp" in data or "elements" in data
        assert rc == 0


# ---------------------------------------------------------------------------
# apps / tree (smoke — may fail without AT-SPI but shouldn't crash hard)
# ---------------------------------------------------------------------------

class TestAppsTree:
    def test_apps_json(self, capsys):
        rc = _run_cli("apps", "--json")
        out = capsys.readouterr().out
        # Should be valid JSON (list or error message)
        try:
            data = json.loads(out)
            assert isinstance(data, list)
        except json.JSONDecodeError:
            pass  # AT-SPI may not be available
        assert rc in (0, 1, 2)
