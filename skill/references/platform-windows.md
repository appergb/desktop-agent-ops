# Windows Path

This file defines the intended Windows branch for the skill.

## Preferred direction

For Windows, prefer a helper-script path that wraps:

- `pygetwindow` (Win32 window enumeration/activation)
- screenshot tooling such as Pillow/MSS
- pyautogui-like input control where appropriate

## MVP rule

Windows helpers are now **best-effort** via `pygetwindow` (frontmost, list windows, focus, bounds). If `pygetwindow` or its dependencies are missing, commands will return structured errors. Be explicit about dependency requirements when failures occur.

## Expected Windows command surface

Aim to match the macOS helper surface:

- screenshot
- capture-region
- frontmost
- list-apps or windows
- focus-app
- click / double-click / drag / scroll
- type / press / hotkey

## Behavior rule

Keep the top-level workflow the same across platforms; only the helper implementation should differ.
