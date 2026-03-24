# Release Notes — v1.0.2 (2026-03-24)

## Summary

Bug-fix release addressing 10 issues found during comprehensive code review. Key fix: minimized windows on macOS can now be restored by `focus-app`.

## Bug Fixes

### Critical
- **Minimized window restoration** — `focus-app` now clicks the Dock icon to restore minimized windows on macOS. Previously only handled hidden (`Cmd+H`) apps, not minimized (`Cmd+M`) windows. Dock-click approach is reliable across native and non-native apps (e.g., WeChat).
- **Missing `find_running_app` function** — added case-insensitive exact-match lookup; 2 previously failing tests now pass.

### High
- **`cmd_scroll` horizontal double-execution** — removed duplicate `hscroll()` call that ran once in a try/except and again unconditionally.
- **`cmd_screenshot` fd leak** — `os.close(fd)` now called after `mkstemp` before unlinking.
- **`cmd_pixel_color` unsafe tempfile** — replaced deprecated `mktemp` with safe `mkstemp`.
- **`cmd_front_window_bounds` crash on `|` in title** — switched from `split('|')` to `rsplit('|', 2)` with validation.
- **`cmd_insert_newline` silent failure** — now catches `SystemExit` and outputs JSON error via `jerror`.

### Medium
- **`cmd_drag` cliclick ignoring duration** — now inserts `w:<ms>` wait between mouse-down and mouse-up for reliable drag recognition.
- **`cmd_type` CJK silent skip** — final pyautogui fallback now errors with hint instead of silently dropping non-ASCII characters.
- **Late `import time`** — moved to module-level import.

## Test Results

13/13 tests passing.

## Files Changed

- `skill/scripts/desktop_ops.py` — all fixes
- `CHANGELOG.md` — version history updated

## Package

- `desktop-agent-ops-v1.0.2.zip` (74 KB)
- SHA256: `8fbcfa36c713dc123cea50edaa3f6299ed9fc3dfd929a548d1f6f1dbbc4821de`
