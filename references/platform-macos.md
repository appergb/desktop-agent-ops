# macOS Path

## Preferred tools

For macOS, prefer these primitives:

- screenshot: `/usr/sbin/screencapture`
- app activation: `osascript`
- mouse/keyboard: prefer `cliclick` for macOS-native pointer/key events; use `pyautogui` as fallback
- optional future expansion: Accessibility API / Quartz

Use them through `scripts/desktop_ops.py`, not ad hoc each time.

For local setup, prefer a dedicated virtual environment outside the packaged skill directory and install runtime deps there before testing action commands. When running diagnostics, pass that interpreter through an environment variable such as `DESKTOP_AGENT_OPS_PYTHON`.

## Required permissions

macOS desktop automation may require:

- Accessibility
- Screen Recording
- Automation permissions for app control

If capture or input fails unexpectedly, suspect permissions first.

## Minimum macOS command set for MVP

Implement and use these first:

- `screenshot`
- `capture-region`
- `frontmost`
- `list-apps`
- `focus-app`
- `move`
- `click`
- `double-click`
- `drag`
- `scroll`
- `press`
- `type`
- `hotkey`
- `mouse-position`

## Recommended action order on macOS

## Timing notes for interactive apps

On macOS, app activation, focus transfer, and message-send UI updates may lag slightly behind the input event.

When working with chat apps such as WeChat:
- after `focus-app`, prefer a short settle wait before capturing if the window was previously occluded
- after a send trigger, wait a short moment before verification capture
- if the first verification capture is ambiguous, recapture once more at about 1 second total elapsed before treating it as a failure


### Bring an app forward

1. check frontmost app
2. if wrong, run `focus-app`
3. capture again
4. verify app switched

### Work inside a target UI

1. capture state
2. if target is unclear, capture a smaller region
3. perform one action
4. capture again
5. verify before continuing

## Notes

- `focus-window` may be added later, but `focus-app` is enough for MVP
- prefer explicit re-capture after activation because animation and focus changes can lag
- when a text search UI exists, use it instead of manual scanning/scrolling
ts/doctor.py`
