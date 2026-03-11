# GUI Automation Skill for OpenClaw

AI-driven GUI automation for Linux desktop. Control applications, click buttons, type text, and navigate UIs using natural language. Uses AT-SPI accessibility API + screenshot hybrid mode. Designed to be driven by the OpenClaw agent directly — no external AI API needed.

## Features

- **Perception**: AT-SPI (structural UI tree) and screenshot (visual) modes.
- **Actions**: Mouse clicks, keyboard input, scrolling, dragging, window focus.
- **Multi-backend**: Supports multiple AI models for autonomous operation (Claude, GPT-4o, Gemini, Ollama).
- **OpenClaw-native**: The agent acts as the AI brain; no external API calls required.

## Requirements

- **OS**: Linux (tested on Ubuntu 24.04 with Wayland/GNOME + XWayland).
- **Python packages**: `pyatspi` (`python3-pyatspi`), `gir1.2-atspi-2.0`.
- **CLI tools**: `xdotool`, `gnome-screenshot`. Optional: `ydotool` for native Wayland input.
- **Permissions**: For `ydotool`, `/dev/uinput` permissions must be set (e.g., `chmod 666` + udev rule).

## Quick Start

The skill is located in `~/.openclaw/workspace/skills/gui-automation/`.

### From the command line

```bash
cd ~/.openclaw/workspace/skills/gui-automation

# List running GUI applications
python3 -m src.main apps

# Get UI element tree (structural)
python3 -m src.main tree                    # all apps
python3 -m src.main tree --app "firefox"    # specific app

# Take a screenshot
python3 -m src.main screenshot -o /tmp/screen.png
```

### From Python (direct integration)

```python
import sys
sys.path.insert(0, '/home/hung/.openclaw/workspace/skills/gui-automation')

from src.atspi_helper import list_applications, find_elements, get_ui_tree_summary, do_action, set_text
from src.screenshot import take_screenshot
from src.actions import click, double_click, right_click, type_text, press_key, scroll, drag, mouse_move, focus_window

# List apps
apps = list_applications()  # e.g., ['firefox', 'nautilus']

# Get a summary of an app's UI tree
tree = get_ui_tree_summary("firefox", max_depth=5)

# Find and click a button by name/role
buttons = find_elements(role="push button", name="Save")
if buttons:
    do_action(buttons[0], "click")

# Alternatively, click by coordinates
click(100, 200)

# Type text
type_text("Hello world")
press_key("Return")

# Focus a window
focus_window(name="Firefox")

# Take a screenshot (base64 PNG)
img_b64 = take_screenshot()
```

## Strategy: AT-SPI vs Screenshot

- **Prefer AT-SPI first**: It provides element names, roles, and coordinates; fast and precise.
- **Use screenshot when**: AT-SPI returns an empty tree, the app lacks accessibility support, or you need visual context.

## Autonomous Mode (Optional)

The `src/backends.py` module supports multiple AI backends for running the agent without OpenClaw driving it:

- `AnyRouterBackend` (OpenClaw internal)
- `ClaudeBackend` (Anthropic API)
- `OpenAIBackend` (GPT-4o)
- `GeminiBackend` (Google Gemini)
- `OllamaBackend` (Local models)

Set `GUI_AI_MODEL` to select the backend:

```bash
GUI_AI_MODEL=llava:7b python3 -m src.main run "Open Firefox and search for cats"
```

Note: Autonomous mode requires appropriate API keys or local models. The default OpenClaw integration does not need any external AI API.

## Environment Notes

- Under Wayland with GNOME and XWayland, `xdotool` works fine through XWayland.
- If using native Wayland input, `ydotool` is available but ensure `--absolute` parameter is not used (older versions may not support it).
- `gnome-screenshot` is used for screen capture; it functions via XWayland.
- AT-SPI is provided by `python3-pyatspi` and `gir1.2-atspi-2.0`.

## Project Structure

- `src/screenshot.py` – screen capture
- `src/atspi_helper.py` – UI tree parsing and element actions
- `src/actions.py` – low-level input operations
- `src/backends.py` – AI model backends
- `src/agent.py` – main decision loop
- `src/query.py` – query parsing
- `src/main.py` – CLI entrypoint

For full reference, see `SKILL.md` in this directory.

## Troubleshooting

- **AT-SPI shows no elements**: Ensure the target application supports accessibility; fall back to screenshot mode.
- **Input not working**: Check xdotool/ydotool permissions. For ydotool, `/dev/uinput` must be writable.
- **Crash reporter popups**: Disable Apport (`sudo systemctl disable apport` and set `enabled=0` in `/etc/default/apport`).

