# Linux Path

This file defines how the Linux branch works now. Linux is not a single platform path, so always branch by session capabilities first.

## First branch

Always detect whether Linux is:

- X11
- Wayland

Use `scripts/platform_probe.py` before assuming available tools.

## Core rule: do not guess coordinates

On Linux, click targets must come from:

- `scripts/accessibility_provider.py` when AT-SPI is available
- `scripts/target_resolver.py` when AT-SPI is degraded, unavailable, or blocked

Never estimate click targets from screenshots.

## Preferred direction

For Linux helper logic, tool families include:

- GNOME / AT-SPI: `accessibility_provider.py` for structured element trees
- X11: `xdotool`, `wmctrl`, screenshot tools for focus, bounds, and input
- Wayland: compositor-specific screenshot and input tools, with stricter limits

If X11 tools are missing, report which dependency is absent and suggest installation.

## Preferred targeting order

1. `scripts/accessibility_provider.py --app "AppName" --text "Target"` when GNOME/AT-SPI is available
2. `scripts/target_resolver.py --app "AppName" --text "Target" --python $PY`
3. Template or heuristic fallback only when text and AT-SPI are both insufficient

## AT-SPI rule

GNOME with `pyatspi` is the first-class Linux path for structured targeting.

- If `pyatspi` is installed and the accessibility bus is available, use it first
- If the session bus or bindings are unavailable, report that clearly and fall back to OCR
- Non-GNOME or locked-down sessions may expose no usable AT-SPI tree

## Input and window-management rule

Linux helpers remain **best-effort** for focus, frontmost app, and bounds:

- X11: `xdotool` and `wmctrl` are the preferred helpers
- Wayland: some compositors restrict simulated input or window enumeration
- If tools are missing or the session forbids automation, return a structured error instead of improvising

Keep the skill workflow identical where possible; only the helper implementation should branch.
