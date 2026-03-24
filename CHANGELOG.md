# Changelog

## v1.0.1 (2026-03-24)

### Packaging & Release
- Added `skill/agents/openai.yaml` so the packaged skill carries standard UI metadata
- Added a minimal GitHub Actions unit-test workflow to protect future releases
- Prepared a pure-skill package layout for direct installation from a release ZIP

### Bug Fixes
- Fixed task directory handling by centralizing `task_id` validation and safe path resolution in `task_paths.py`
- Fixed `task_context.py` and `cleanup_task.py` to reuse the same safe task path contract
- Fixed `desktop_ops.py` missing `escape_applescript_string()` and applied escaping to AppleScript interpolation points
- Fixed test imports so the suite resolves modules from `skill/scripts/`

### Documentation
- Unified repository-root command examples in `README.md`, `docs/README_zh.md`, and `docs/README_ja.md`
- Synced `skill/SKILL.md` with the full `references/` set and corrected example command paths

## v1.0.0 (2026-03-23)

### Features
- One-command auto-setup (`first_run_setup.py`) — installs all dependencies, OCR languages, Python venv, and OS permissions
- 17 cross-platform desktop operations via `desktop_ops.py`
- Window-scoped OCR targeting — prevents clicking elements in wrong apps
- OCR-first hybrid targeting pipeline (`target_resolver.py`)
- Auto DPI/HiDPI/Retina detection and coordinate scaling
- Multi-language OCR auto-detection (Chinese, Japanese, Korean, etc.)
- CJK text input via clipboard-paste fallback on all platforms
- Adjacent character merging for CJK OCR fragments
- Window-targeted scrolling with `--x --y` positioning
- AppleScript key/type fallback when cliclick fails on macOS

### Cross-Platform Support
- macOS: cliclick + screencapture + AppleScript + System Settings auto-open
- Windows: pyautogui + pygetwindow + clip.exe paste + locale.getdefaultlocale()
- Linux (X11): pyautogui + xdotool + wmctrl + xclip paste

### Bug Fixes
- Fixed `permission_bootstrap.py` falsely marking permissions as completed (checked return code instead of JSON ok field)
- Fixed `desktop_ops.py` `jerror()` exiting with code 0 on errors
- Fixed `capture-region` missing `--with-cursor` argument
- Fixed `task_context.py` hardcoded `/tmp` path (Windows incompatible)
- Fixed `click_and_verify.py` hardcoded `python3` command (Windows incompatible)
- Fixed `smoke_test.py` strict coordinate match failing on Retina displays
- Fixed System Settings fallback for different macOS versions
