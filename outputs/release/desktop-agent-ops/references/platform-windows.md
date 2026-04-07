# Windows Path

This file defines how the skill works on Windows. Read this when running on Windows.

## Core rule: do not guess coordinates

On Windows, click targets must come from:

- `scripts/accessibility_provider.py` when UI Automation exposes the target
- `scripts/target_resolver.py` when UIA is degraded or blocked

Never estimate a click by looking at a screenshot.

## Key principle: Discover app names dynamically

**NEVER hardcode Windows process names or window titles.** Always discover them at runtime.

Windows app names vary by:
- Language version (Chinese WeChat vs English WeChat)
- App version (different builds have different titles)
- User customization

Instead, the agent must discover the correct name dynamically.

## Step 1: Probe running apps first

Before targeting any app, run:

```bash
$PY scripts/desktop_ops.py list-apps
```

This returns all visible window titles on the current Windows desktop. Use the exact title returned.

## Step 2: If the app is not running

Try to launch it, then re-probe:

```bash
# Method A: via CLI
start "" "WeChat"
# Method B: via search
# The agent should use web search to find the correct launch command
```

## Step 3: If you don't know the correct app name

Use web search to find it:

```
Search: "WeChat Windows process name window title"
Search: "How to find window title of a running app Windows"
Search: "微信 Windows 进程名 窗口标题"
```

Common patterns to look for:
- Window title in Task Manager → Details tab
- Process name in Task Manager → Processes tab
- `tasklist /V` shows window titles

## Step 4: Focus the app

Once the correct window title is confirmed, use it with `focus-app`:

```bash
$PY scripts/desktop_ops.py focus-app --name "微信"
# or whatever title list-apps returned
```

## Preferred tools on Windows

- `accessibility_provider.py` — first choice for structured UIA targeting
- `target_resolver.py` — tries UIA first, then OCR/template fallback
- `list-apps` / `frontmost` — window enumeration via `pygetwindow` (requires `pywin32`)
- `focus-app` — uses `pygetwindow` `.activate()` / `.restore()`
- screenshot — via `pyautogui` (PIL/Pillow backend)
- mouse/keyboard — `pyautogui`
- text input — clipboard paste via PowerShell `Set-Clipboard` → `Ctrl+V`
- key press — `pyautogui.press()` or `pyautogui.hotkey()`
- close app — `taskkill /IM "app.exe"` (no GUI needed)

## Windows WeChat send mechanism

On Windows WeChat:
1. After typing the message, first try to find the visible `发送` button via UIA or OCR
2. If visible, click it (preferred — avoids accidental double-send)
3. If no visible send button and Enter-to-send is confirmed, use `press --key return`

The exact button position varies by WeChat version — always re-locate via accessibility or OCR before clicking.

## Windows DPI scaling

Windows display scaling (125%, 150%, 200%, etc.) can cause coordinate mismatches.

If clicks miss targets:
1. Use `desktop_ops.py screenshot` to visually verify target positions
2. Check Windows Display Settings → Scale (reset to 100% for best automation accuracy)
3. pyautogui coordinates are logical pixels — they should match Windows's reported coordinates

## UAC, UIPI, and permissions

Windows accessibility and input automation work best when the agent and the target app run at the same privilege level.

Watch for these cases:

- Elevated target app, non-elevated agent: UIA focus or lookup may fail with access denied
- UAC prompts or secure desktop: inaccessible to normal automation
- System windows or protected surfaces: may expose no usable UIA tree
- Enterprise controls such as AppLocker: may block helper subprocesses

Practical rule:

1. If UIA returns an access or permission-style error, treat it as a real platform boundary, not a targeting miss
2. Re-check whether the target app is elevated
3. If safe, fall back to OCR-based targeting through `target_resolver.py`
4. Do not guess the close button, taskbar button, or dialog position

## Preferred targeting order

1. `scripts/accessibility_provider.py --app "AppName" --text "Target"`
2. `scripts/target_resolver.py --app "AppName" --text "Target" --python $PY`
3. Template or heuristic fallback only when text and UIA are both insufficient
