# Release Notes — v1.0.2 (2026-03-24)

## Summary

Major reliability and performance release. Fixes CJK text input, Enter-to-send, minimized window restoration, and 10+ other bugs. End-to-end WeChat message sending now works reliably and is 7.6x faster.

## Performance (7.6x faster end-to-end)

- `type`: clipboard paste is now the primary path on ALL platforms (was cliclick on macOS, which silently dropped CJK)
- `paste_text` macOS: single osascript call (`set clipboard` + `Cmd+V`), no separate `pbcopy` subprocess
- `paste_text` Windows: PowerShell `Set-Clipboard` for faster Unicode handling
- `focus-app`: fast path skips Dock traversal when app is already frontmost
- `focus-app`: reduced delays from 0.3s to 0.15s
- **Benchmark** (macOS, WeChat): focus 0.29s + type 0.17s + send 0.13s = **0.59s total** (was 4.49s)

## Critical Fixes

- **CJK text input** — cliclick `t:` silently dropped Chinese/Japanese/Korean characters; now clipboard paste is always used first
- **Enter-to-send** — cliclick `kp:return` was not recognized by WeChat; now AppleScript `key code 36` is the primary path on macOS
- **Hotkey with letters** — `hotkey --keys cmd a` failed because cliclick `kp:` doesn't support letter keys; now uses `t:` for characters
- **Minimized window restoration** — `focus-app` now clicks Dock icon to restore minimized windows (previously only handled hidden apps)

## Other Bug Fixes

- `cmd_scroll` horizontal direction removed duplicate execution
- `cmd_screenshot` file descriptor leak from `mkstemp` (fd never closed)
- `cmd_pixel_color` replaced deprecated `tempfile.mktemp` with safe `mkstemp`
- `cmd_front_window_bounds` crash when window title contains `|` character
- `cmd_insert_newline` now catches `SystemExit` and outputs JSON error via `jerror`
- `cmd_drag` cliclick path now respects `--duration` parameter (inserts `w:` wait)
- Added missing `find_running_app` function (2 tests were failing)
- `import time` moved to module top level

## Documentation Updates

- README.md: updated platform table with new backend priorities
- SKILL.md: added backend priority table, updated text input docs
- platform-macos.md: documented clipboard-first input, AppleScript key press, focus-app fast path
- platform-windows.md: documented PowerShell clipboard, pyautogui input
- CHANGELOG.md: complete v1.0.2 history

## Test Results

13/13 tests passing.

## End-to-End Verified

WeChat macOS: `focus-app` → `type --text "中文消息"` → `press --key return` → message sent successfully.
