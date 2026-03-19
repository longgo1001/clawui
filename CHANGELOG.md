# Changelog

All notable changes to ClawUI are documented here.

## [0.9.0] - 2026-03-18

### Added
- Structured exception hierarchy (`clawui.exceptions`) with typed errors: `ClawUIError`, `BackendError`, `CDPError`, `PerceptionError`, `TimeoutError`, `AgentError`, `ConfigError`
- Retry decorator uses typed `RETRIABLE_EXCEPTIONS` for precise retry scoping
- 26 new exception hierarchy tests (161 total tests)
- `wait_for_element` tool — poll until an AT-SPI element appears (timeout + interval)
- `wait_for_text` tool — OCR-based text wait (poll until screen shows target text)
- Stream Capture module (`stream_capture.py`) — Mutter ScreenCast D-Bus API, ~40 FPS zero-dialog capture
- Game Perception module (`game_perception.py`) — auto ROI, threat/pickup detection, cross-frame tracking
- Recording/replay (`recorder.py`) — JSON action recording with dry-run support
- Firefox Marionette backend — full browser automation for Firefox
- `clawui status` CLI command — runtime backend status with JSON output
- GitHub Issues monitoring script (`tools/check_issues.py`)

### Changed
- Complete `print` → `logging` migration in agent.py, screenshot.py; added `--log-level` CLI flag and `CLAWUI_LOG_LEVEL` env var (v0.8.2)
- `cdp_fill` now targets by label/placeholder/aria-label with framework-safe input/change events
- ydotool backend completed for pure Wayland: press_key, scroll, drag, window ops
- X11 `list_windows()` detects all workspaces (removed `--onlyvisible` limit)
- CDP retry logic handles transient disconnects with reconnection

### Fixed
- CDP special-key dispatch normalized for reliable key events
- Window class fallback for Electron/NW.js apps on X11
- GUI environment inheritance for cron-triggered CDP runs
- Test assertions aligned with typed exception hierarchy

## [0.8.0] - 2026-03-10

### Added
- Initial public release
- AT-SPI desktop perception (GTK/Qt native apps)
- X11 perception backend (xdotool/XWayland)
- Perception routing layer (`perception.py`)
- CDP backend for Chromium automation
- Multi-backend AI model support (Ollama/GPT-4o/Gemini/AnyRouter)
- Agent tool set: 11 CDP tools + 10+ AT-SPI/X11 tools
- End-to-end test scripts
- CLI with `run`, `interactive`, `status` commands
