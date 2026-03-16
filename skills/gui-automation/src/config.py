"""Configuration file support for ClawUI.

Loads settings from ~/.config/clawui/config.toml (or $CLAWUI_CONFIG).
Environment variables always override config file values.

Usage:
    from .config import get_config_value

    # Returns env var CLAWUI_LOG_LEVEL if set, else config file value, else default
    level = get_config_value("LOG_LEVEL", default="info")
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("clawui.config")

_config: dict[str, Any] | None = None
_CONFIG_LOADED = False


def _default_config_path() -> Path:
    """Return default config file path."""
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(xdg) / "clawui" / "config.toml"


def _load_config() -> dict[str, Any]:
    """Load and cache the TOML config file."""
    global _config, _CONFIG_LOADED
    if _CONFIG_LOADED:
        return _config or {}

    _CONFIG_LOADED = True
    config_path = os.environ.get("CLAWUI_CONFIG", str(_default_config_path()))
    path = Path(config_path)

    if not path.exists():
        _config = {}
        return _config

    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            logger.debug("No TOML parser available; config file ignored")
            _config = {}
            return _config

    try:
        with open(path, "rb") as f:
            _config = tomllib.load(f)
        logger.debug("Loaded config from %s", path)
    except Exception as e:
        logger.warning("Failed to load config %s: %s", path, e)
        _config = {}

    return _config


def _flatten_key(key: str) -> list[str]:
    """Convert CLAWUI_SECTION_KEY to config path [section, key].

    Examples:
        "LOG_LEVEL"        -> ["log_level"]
        "API_RETRY_MAX"    -> ["api", "retry_max"]
        "RETRY_MAX"        -> ["retry_max"]
        "PARALLEL_TOOLS"   -> ["parallel_tools"]
    """
    # Known top-level sections for disambiguation
    _SECTIONS = {"api", "retry", "vision", "atspi", "scroll", "context", "plan",
                 "exec", "verify", "replan", "cache"}
    parts = key.lower().split("_", 1)
    if len(parts) == 2 and parts[0] in _SECTIONS:
        return parts
    return [key.lower()]


def get_config_value(key: str, *, default: str | None = None) -> str | None:
    """Get a configuration value with priority: env var > config file > default.

    Args:
        key: Config key WITHOUT the CLAWUI_ prefix (e.g., "LOG_LEVEL").
        default: Fallback value if not found anywhere.

    Returns:
        The resolved value as a string, or default.
    """
    # 1. Environment variable always wins
    env_key = f"CLAWUI_{key}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return env_val

    # 2. Config file
    config = _load_config()
    path = _flatten_key(key)

    node: Any = config
    for part in path:
        if isinstance(node, dict):
            node = node.get(part)
        else:
            node = None
            break

    if node is not None:
        return str(node)

    return default


def get_config_bool(key: str, *, default: bool = False) -> bool:
    """Get a boolean config value."""
    val = get_config_value(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def get_config_int(key: str, *, default: int = 0) -> int:
    """Get an integer config value."""
    val = get_config_value(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def get_config_float(key: str, *, default: float = 0.0) -> float:
    """Get a float config value."""
    val = get_config_value(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def generate_default_config() -> str:
    """Generate a documented default config.toml template."""
    return '''\
# ClawUI Configuration
# Place at: ~/.config/clawui/config.toml
# Environment variables (CLAWUI_*) override these values.

# Logging level: debug, info, warning, error
log_level = "info"

# Grounding methods for element detection (comma-separated)
# Options: atspi, ocr, vision
# grounding_methods = "atspi,ocr,vision"

# Enable parallel tool execution
parallel_tools = true

# Enable action verification (screenshot after each action)
# verify_actions = false

# Allow shell command execution in agent mode
# allow_shell = false

# Firejail sandboxing for shell commands
# firejail = false

# Writable paths when firejail is enabled (comma-separated)
# writable_paths = "/tmp"

# Commands blocked from shell execution (JSON array)
# command_blocklist = "[]"

[api]
# API retry settings for vision backends
retry_max = 3
retry_delay = 2.0

[retry]
# Tool-level retry settings
max = 3
delay = 1.0

[vision]
# Vision-specific retry settings
retry_max = 3
retry_delay = 2.0

[atspi]
# AT-SPI query timeout in seconds
timeout = 5

[context]
# Maximum tokens for conversation context
# max_tokens = 120000

[scroll]
# Scroll-and-find settings
# find_max = 5
# find_pause = 1.0

[cache]
# Element cache TTL in seconds
# ttl = 5

[plan]
# Model for planning steps (if different from exec model)
# model = ""

[exec]
# Model for executing actions
# model = ""

[verify]
# Model for verifying action results
# model = ""

[replan]
# Enable dynamic replanning
# enabled = false
# interval = 5
'''


def init_config() -> Path:
    """Create default config file if it doesn't exist. Returns path."""
    path = _default_config_path()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_default_config())
    return path


def _format_toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _dump_simple_toml(data: dict[str, Any]) -> str:
    """Dump nested dict to TOML (supports scalars and one-level sections)."""
    lines: list[str] = []

    # top-level scalars first
    for k, v in data.items():
        if isinstance(v, dict):
            continue
        lines.append(f"{k} = {_format_toml_scalar(v)}")

    # nested tables
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        if lines:
            lines.append("")
        lines.append(f"[{k}]")
        for kk, vv in v.items():
            if isinstance(vv, dict):
                continue
            lines.append(f"{kk} = {_format_toml_scalar(vv)}")

    return "\n".join(lines).rstrip() + "\n"


def set_config_value(key: str, value: Any) -> Path:
    """Set config value in TOML file (creates file if missing). Returns config path."""
    path = Path(os.environ.get("CLAWUI_CONFIG", str(_default_config_path())))
    path.parent.mkdir(parents=True, exist_ok=True)

    cfg = dict(_load_config())
    parts = _flatten_key(key)
    if len(parts) == 1:
        cfg[parts[0]] = value
    else:
        section, subkey = parts[0], parts[1]
        section_node = cfg.get(section)
        if not isinstance(section_node, dict):
            section_node = {}
            cfg[section] = section_node
        section_node[subkey] = value

    path.write_text(_dump_simple_toml(cfg), encoding="utf-8")
    reset_cache()
    return path


def reset_config_file() -> Path:
    """Overwrite config file with defaults. Returns path."""
    path = Path(os.environ.get("CLAWUI_CONFIG", str(_default_config_path())))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_default_config(), encoding="utf-8")
    reset_cache()
    return path


def reset_cache():
    """Reset the config cache (for testing)."""
    global _config, _CONFIG_LOADED
    _config = None
    _CONFIG_LOADED = False
