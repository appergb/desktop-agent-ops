# Changelog

## v1.0.2 (2026-03-24)

### Performance (7.6x faster end-to-end)
- `cmd_type`: clipboard paste is now the primary path; cliclick `t:` silently dropped CJK characters
- `paste_text` macOS: merged pbcopy + Cmd+V into a single osascript call (saves one subprocess)
- `paste_text` Windows: use PowerShell `Set-Clipboard` for faster Unicode handling
- `cmd_focus_app`: fast path skips Dock traversal when app is already frontmost
- `cmd_focus_app`: reduced AppleScript delays from 0.3s to 0.15s; verification delay from 0.3s to 0.1s
- Benchmarks (macOS, WeChat already frontmost): focus 0.29s + type 0.17s + send 0.13s = **0.59s total** (was 4.49s)

### Bug Fixes
- Fixed minimized window restoration on macOS — `focus-app` now clicks dock icon to restore minimized windows (previously only handled hidden apps)
- Fixed `cmd_type` dropping CJK text — cliclick was first choice but silently skips non-ASCII; now clipboard paste is always first
- Fixed `cmd_press` on macOS — AppleScript `key code` is now the primary path; cliclick `kp:return` was not recognized by WeChat
- Fixed `cmd_hotkey` on macOS — cliclick `kp:` only accepts special keys; letter keys (a, c, v) now use `t:` so `cmd+a`, `cmd+c` etc. work correctly
- Fixed `cmd_scroll` horizontal direction executing twice (once in try/except, once unconditionally)
- Fixed `cmd_screenshot` file descriptor leak from `mkstemp` (fd was never closed)
- Fixed `cmd_pixel_color` using deprecated `tempfile.mktemp` (replaced with safe `mkstemp`)
- Fixed `cmd_front_window_bounds` crashing when window title contains `|` character (now uses `rsplit`)
- Fixed `cmd_insert_newline` not catching `SystemExit` — now properly outputs JSON error via `jerror`
- Fixed `cmd_drag` cliclick path ignoring `--duration` parameter (now inserts `w:` wait command)
- Added missing `find_running_app` function (2 tests were failing)
- Moved `import time` to module top level (was late-imported in function body)

### Documentation
- Added 8 new example cases (Case 12–19): right-click, drag-and-drop, system settings, form filling, dropdown, toggle/slider, cross-app copy-paste, browser tab management
- Added 8 matching reusable operation patterns
- Updated README.md platform table, SKILL.md backend priority table, platform-macos.md, platform-windows.md

## v1.0.1-urgent (2026-03-24)

### Urgent Fixes
- separated literal line breaks from send actions in `desktop_ops.py`
- added `insert-newline` so multi-line messages no longer depend on send-key behavior
- normalized Enter-like send keys so `press --key return` always maps to a real key press path
- documented that WeChat and similar direct-Enter chat apps should send via `press --key return`, not via `type --text` with `\n`
- documented that Windows WeChat should prefer the visible `发送` button instead of relying on Enter-to-send when the button is available

### Packaging
- prepared an urgent pure-skill ZIP package using the same base version with an `-urgent` suffix

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
