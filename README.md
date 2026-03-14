# ClawUI

AI-driven desktop and browser automation for Linux. Control GUI applications, fill web forms, click buttons, and navigate UIs — all from Python or the command line.

[![CI](https://github.com/longgo1001/clawui/actions/workflows/ci.yml/badge.svg)](https://github.com/longgo1001/clawui/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

- **Multi-backend perception** — AT-SPI (Wayland-native), X11 (xdotool), CDP (Chromium), Marionette (Firefox)
- **Smart routing** — `perception.py` auto-detects app type and picks the right backend
- **60+ automation tools** — click, type, screenshot, OCR, wait-for-element, annotated screenshots, record/replay
- **CLI** — `clawui apps|tree|screenshot|click|type|inspect|doctor|record|replay|wait` (v0.5.0)
- **AI agent loop** — feed tasks in natural language, get autonomous GUI automation
- **Browser automation** — CDP for Chromium, Marionette for Firefox (navigation, forms, JS eval, tabs)

## Install

```bash
# From source
git clone https://github.com/longgo1001/clawui.git
cd clawui
pip install -e .

# System dependencies (Ubuntu/Debian)
sudo apt install python3-pyatspi gir1.2-atspi-2.0 xdotool gnome-screenshot tesseract-ocr
```

## Quick Start

### CLI

```bash
# List running GUI apps
clawui apps

# Get accessibility tree
clawui tree

# Take a screenshot
clawui screenshot

# Diagnose your setup
clawui doctor

# Find interactive elements with numbered labels
clawui elements

# Click element by index
clawui click 5

# Type text
clawui type "Hello, world!"

# Record and replay
clawui record my_flow
clawui replay my_flow.json
```

### Python

```python
from src.perception import list_applications, find_elements, get_ui_tree_summary
from src.actions import click, type_text, press_key
from src.cdp_helper import CDPHelper

# Desktop apps
apps = list_applications()
buttons = find_elements(app_name="Calculator", role="push button")

# Browser automation (Chromium via CDP)
cdp = CDPHelper()
cdp.navigate("https://example.com")
cdp.click_element("#submit-btn")
cdp.type_text("#search", "hello")
```

### AI Agent

```python
from src.agent import run_agent

# Natural language GUI automation
run_agent("Open Calculator and compute 42 * 17")
```

## Architecture

```
perception.py  ← smart router (auto-selects backend)
├── atspi_helper.py    (Wayland-native: GNOME apps, GTK/Qt)
├── x11_helper.py      (XWayland: Firefox, Chrome, Electron)
├── cdp_helper.py      (Chromium DevTools Protocol)
└── marionette_helper.py (Firefox Marionette)

agent.py       ← AI tool loop (60+ tools)
cli.py         ← command-line interface
recorder.py    ← record/replay actions
annotated_screenshot.py ← numbered element labels
ocr_tool.py    ← Tesseract OCR integration
```

## Troubleshooting

Run `clawui doctor` to diagnose common issues:

| Issue | Fix |
|-------|-----|
| AT-SPI not detecting apps | Install `gir1.2-atspi-2.0`, enable accessibility |
| XWayland apps invisible | Use X11 session or xdotool backend |
| CDP won't connect | Launch Chromium with `--remote-debugging-port=9222` |
| Screenshots fail | Install `gnome-screenshot` or use Pillow fallback |
| OCR not working | Install `tesseract-ocr` |

## License

MIT
