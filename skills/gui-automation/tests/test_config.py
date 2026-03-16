"""Tests for clawui.config module."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    get_config_value,
    get_config_bool,
    get_config_int,
    get_config_float,
    generate_default_config,
    init_config,
    set_config_value,
    reset_config_file,
    reset_cache,
)


@pytest.fixture(autouse=True)
def _clean_config(monkeypatch):
    """Reset config cache and point to a nonexistent file for isolation."""
    reset_cache()
    monkeypatch.setenv("CLAWUI_CONFIG", "/tmp/_clawui_test_nonexistent.toml")
    # Clear any CLAWUI_ env vars that might interfere
    for key in list(os.environ):
        if key.startswith("CLAWUI_") and key != "CLAWUI_CONFIG":
            monkeypatch.delenv(key, raising=False)
    yield
    reset_cache()


def test_env_var_overrides_config(monkeypatch):
    """Environment variable should take priority over config file."""
    monkeypatch.setenv("CLAWUI_LOG_LEVEL", "debug")
    assert get_config_value("LOG_LEVEL") == "debug"


def test_default_when_nothing_set():
    """Should return default when neither env nor config file is set."""
    assert get_config_value("LOG_LEVEL", default="info") == "info"


def test_none_when_nothing_set():
    """Should return None when no default and nothing set."""
    assert get_config_value("NONEXISTENT_KEY") is None


def test_config_file_loading(monkeypatch, tmp_path):
    """Should load values from a TOML config file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('log_level = "debug"\n\n[api]\nretry_max = 5\n')
    monkeypatch.setenv("CLAWUI_CONFIG", str(config_file))
    reset_cache()

    assert get_config_value("LOG_LEVEL") == "debug"
    assert get_config_value("API_RETRY_MAX") == "5"


def test_env_overrides_file(monkeypatch, tmp_path):
    """Env var should override config file value."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('log_level = "info"\n')
    monkeypatch.setenv("CLAWUI_CONFIG", str(config_file))
    monkeypatch.setenv("CLAWUI_LOG_LEVEL", "error")
    reset_cache()

    assert get_config_value("LOG_LEVEL") == "error"


def test_get_config_bool(monkeypatch):
    monkeypatch.setenv("CLAWUI_PARALLEL_TOOLS", "true")
    assert get_config_bool("PARALLEL_TOOLS") is True

    monkeypatch.setenv("CLAWUI_PARALLEL_TOOLS", "0")
    reset_cache()
    assert get_config_bool("PARALLEL_TOOLS") is False


def test_get_config_bool_default():
    assert get_config_bool("NONEXISTENT", default=True) is True
    assert get_config_bool("NONEXISTENT", default=False) is False


def test_get_config_int(monkeypatch):
    monkeypatch.setenv("CLAWUI_RETRY_MAX", "7")
    assert get_config_int("RETRY_MAX") == 7


def test_get_config_int_default():
    assert get_config_int("NONEXISTENT", default=42) == 42


def test_get_config_int_invalid(monkeypatch):
    monkeypatch.setenv("CLAWUI_RETRY_MAX", "not_a_number")
    assert get_config_int("RETRY_MAX", default=3) == 3


def test_get_config_float(monkeypatch):
    monkeypatch.setenv("CLAWUI_CACHE_TTL", "2.5")
    assert get_config_float("CACHE_TTL") == 2.5


def test_generate_default_config():
    config = generate_default_config()
    assert "log_level" in config
    assert "[api]" in config
    assert "retry_max" in config


def test_init_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    reset_cache()

    # Patch _default_config_path to use our tmp
    from src import config as config_mod

    def _patched():
        return tmp_path / "clawui" / "config.toml"

    monkeypatch.setattr(config_mod, "_default_config_path", _patched)

    path = init_config()
    assert path.exists()
    content = path.read_text()
    assert "log_level" in content

    # Second call should not overwrite
    path.write_text("# custom\n")
    init_config()
    assert path.read_text() == "# custom\n"


def test_set_config_value_top_level(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("CLAWUI_CONFIG", str(config_file))
    reset_cache()

    set_config_value("LOG_LEVEL", "debug")
    assert config_file.exists()
    assert get_config_value("LOG_LEVEL") == "debug"


def test_set_config_value_nested(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("CLAWUI_CONFIG", str(config_file))
    reset_cache()

    set_config_value("API_RETRY_MAX", 7)
    assert get_config_value("API_RETRY_MAX") == "7"
    text = config_file.read_text()
    assert "[api]" in text
    assert "retry_max = 7" in text


def test_reset_config_file(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("CLAWUI_CONFIG", str(config_file))
    reset_cache()

    set_config_value("LOG_LEVEL", "debug")
    reset_config_file()
    text = config_file.read_text()
    assert "# ClawUI Configuration" in text
    assert "log_level = \"info\"" in text
