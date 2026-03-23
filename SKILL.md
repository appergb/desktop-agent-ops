---
name: desktop-agent-ops
description: Execute cross-platform desktop tasks through a pure OpenClaw skill that guides the main agent to observe the screen, focus apps/windows, call helper scripts for screenshots and input actions, verify each step, clean up task context, and only escalate to multi-agent collaboration when tasks become clearly multi-window or multi-app. Use when the user wants desktop GUI control, native app operation, window focus, screenshots, click/type flows, or cross-platform desktop workflows on macOS, Windows, or Linux.
---

# Desktop Agent Ops

Use this skill as a **main-agent operating manual** for desktop GUI tasks.

---

## MANDATORY: Auto-setup gate (FIRST ACTION, every time)

```bash
python3 <SKILL_DIR>/scripts/first_run_setup.py --check
```

If `"ready": false`, run setup (installs EVERYTHING automatically):

```bash
python3 <SKILL_DIR>/scripts/first_run_setup.py
```

**Auto-installs on first run:**
1. Platform detection (macOS / Windows / Linux)
2. `cliclick` + `tesseract` (macOS via brew; Linux guide printed)
3. OCR language packs auto-detected from system locale (中文→chi_sim, 日本語→jpn, etc.)
4. Python venv + pillow, pyautogui, pytesseract, opencv-python, numpy (via uv or pip)
5. OS permissions (Screen Recording, Accessibility, Automation) with auto-open System Settings
6. Smoke test (screenshot + mouse move verification)

After setup, use these env vars for ALL subsequent calls:
```
DESKTOP_AGENT_OPS_PYTHON=<from output.env.DESKTOP_AGENT_OPS_PYTHON>
```

**Do NOT proceed if setup is not ready.**

---

## Core Execution Loop

```
1. auto-setup gate
2. initialize task context
3. FOCUS the target app         ← CRITICAL: lock onto ONE app
4. GET window bounds            ← know exactly where the window is
5. capture ONLY that window     ← never scan full screen
6. analyze the window content
7. locate target via OCR        ← within window bounds only
8. verify target position
9. execute ONE action
10. capture again and verify
11. repeat 6-10 until done
12. cleanup
```

---

## Window-Scoped Targeting (THE CORRECT WAY)

**NEVER do OCR or clicking on a full-screen screenshot.** Always scope to the target app window.
This prevents clicking buttons in the wrong app.

### The 6-Step Targeting Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: FOCUS the target app                            │
│   desktop_ops.py focus-app --name "WeChat"              │
│   → brings WeChat to front, ensures it's the active app │
├─────────────────────────────────────────────────────────┤
│ Step 2: GET the app's window bounds                     │
│   desktop_ops.py front-window-bounds --app "WeChat"     │
│   → returns {x:100, y:50, width:800, height:600}        │
│   → these are LOGICAL coordinates (mouse-ready)         │
├─────────────────────────────────────────────────────────┤
│ Step 3: CAPTURE only that window region                 │
│   desktop_ops.py capture-region                         │
│     --x 100 --y 50 --width 800 --height 600             │
│     --output /tmp/wechat_window.png                     │
│   → screenshot contains ONLY the WeChat window          │
├─────────────────────────────────────────────────────────┤
│ Step 4: OCR within the window                           │
│   ocr_text.py --app "WeChat" --python $PY               │
│   → scans ONLY within WeChat's window bounds            │
│   → returns abs_box with absolute logical coordinates   │
│   → these coordinates are INSIDE the window, guaranteed │
├─────────────────────────────────────────────────────────┤
│ Step 5: VERIFY the target before clicking               │
│   desktop_ops.py move --x <target_x> --y <target_y>    │
│   desktop_ops.py screenshot --output /tmp/verify.png    │
│     --with-cursor                                       │
│   → check: is the cursor on the correct element?        │
│   → check: is the coordinate inside the window bounds?  │
├─────────────────────────────────────────────────────────┤
│ Step 6: CLICK only if verified                          │
│   desktop_ops.py click --x <target_x> --y <target_y>   │
│   → then capture again to verify the click worked       │
└─────────────────────────────────────────────────────────┘
```

### Or use the shortcut (RECOMMENDED):

```bash
$PY scripts/target_resolver.py --app "WeChat" --text "发送" --python $PY
```

This single command:
1. Focuses "WeChat"
2. Gets its window bounds
3. Runs OCR within the window only
4. Returns `best_candidate` with `{x, y}` in logical coordinates
5. Reports `within_window: true/false` to confirm the hit is inside the app

### Why this matters:

| Approach | Risk |
|----------|------|
| Full-screen OCR | "搜索" found in WeChat AND Chrome → clicks wrong app |
| Window-scoped OCR | "搜索" found ONLY in WeChat window → clicks correct element |

---

## DPI / HiDPI / Retina (All Platforms)

**Handled automatically.** No manual DPI work needed.

| Platform | Common scales | Detection method |
|----------|---------------|-----------------|
| macOS Retina | 2.0x | screenshot pixels ÷ logical screen bounds |
| macOS non-Retina | 1.0x | same |
| Windows HiDPI | 1.25x, 1.5x, 2.0x | screenshot pixels ÷ pyautogui.size() |
| Linux X11/Wayland | 1.0x, 1.5x, 2.0x | screenshot pixels ÷ pyautogui.size() |

OCR output fields:
- `box` = **logical coordinates** → use for mouse/click (DPI-corrected)
- `pixel_box` = raw pixel coordinates → for image analysis only
- `abs_box` = logical coordinates + window offset → absolute screen position
- `dpi_scale` = detected factor (e.g. `2.0`)

---

## CLI Quick Reference (EXACT parameter names)

**CRITICAL**: Use EXACTLY these names. Do NOT guess.

### desktop_ops.py

```bash
$PY scripts/desktop_ops.py screenshot [--output PATH] [--x X --y Y --width W --height H] [--with-cursor]
$PY scripts/desktop_ops.py capture-region --x X --y Y --width W --height H [--output PATH] [--with-cursor]
$PY scripts/desktop_ops.py frontmost
$PY scripts/desktop_ops.py list-apps
$PY scripts/desktop_ops.py front-window-bounds [--app NAME]
$PY scripts/desktop_ops.py focus-app --name "App Name"
$PY scripts/desktop_ops.py move --x X --y Y [--duration SECONDS]
$PY scripts/desktop_ops.py click [--x X --y Y] [--button left|right|middle]
$PY scripts/desktop_ops.py double-click [--x X --y Y] [--button left|right|middle]
$PY scripts/desktop_ops.py drag --x1 X1 --y1 Y1 --x2 X2 --y2 Y2 [--duration SEC] [--button left]
$PY scripts/desktop_ops.py scroll --amount N [--x X --y Y] [--direction vertical|horizontal]
# --x --y: move cursor here FIRST so scroll targets the correct window (RECOMMENDED)
# --direction horizontal: for left/right scrolling
# positive=up/right, negative=down/left
$PY scripts/desktop_ops.py mouse-position
$PY scripts/desktop_ops.py press --key KEY
$PY scripts/desktop_ops.py type --text "text to type"
$PY scripts/desktop_ops.py hotkey --keys cmd c
$PY scripts/desktop_ops.py screen-size
$PY scripts/desktop_ops.py pixel-color --x X --y Y
```

### ocr_text.py (window-scoped OCR)

```bash
# OCR within an app window (PREFERRED — window-scoped, safe)
$PY scripts/ocr_text.py --app "WeChat" --python $PY [--region-label bottom_input] [--lang auto]

# OCR from an image file (use only when you have a window-specific capture)
$PY scripts/ocr_text.py --image /path/to/window_capture.png --python $PY [--lang auto]
```

`--lang auto` (default) auto-detects system language.

### target_resolver.py (the RECOMMENDED targeting tool)

```bash
# Find element by text within app window
$PY scripts/target_resolver.py --app "WeChat" --text "发送" --python $PY

# Find by template image within app window
$PY scripts/target_resolver.py --app "WeChat" --template /path/to/icon.png --python $PY

# Narrow to a region within the window
$PY scripts/target_resolver.py --app "WeChat" --text "搜索" --region-label top_search --python $PY
```

Output includes `window_bounds` and `best_candidate.within_window` for verification.

### task_context.py

```bash
$PY scripts/task_context.py init --task-id "my-task"     # aliases: create, --name
$PY scripts/task_context.py show --task-id "my-task"
```

### cleanup_task.py

```bash
$PY scripts/cleanup_task.py --task-id "my-task"
```

### click_and_verify.py

```bash
$PY scripts/click_and_verify.py --app "AppName" --label region_label \
  [--candidate-index 0] [--delay-ms 800] [--allow-pointer-mismatch] [--verify-diff]
```

### window_regions.py

```bash
$PY scripts/window_regions.py --window-x X --window-y Y --window-width W --window-height H [--label LABEL]
```

Labels: `top_search`, `left_sidebar`, `left_sidebar_top`, `title_header`, `content_area`, `toolbar_row`, `bottom_input`, `primary_action`

---

## Typical Workflow Examples

### Example 1: Click a button by text in WeChat

```
1. $PY first_run_setup.py --check                          → ready: true
2. $PY task_context.py init --task-id "wechat-send"
3. $PY desktop_ops.py focus-app --name "WeChat"             → WeChat is frontmost
4. $PY desktop_ops.py front-window-bounds --app "WeChat"    → {x:100, y:50, w:800, h:600}
5. $PY target_resolver.py --app "WeChat" --text "发送" --python $PY
   → best_candidate: {x:450, y:520, within_window:true}
6. $PY desktop_ops.py move --x 450 --y 520
7. $PY desktop_ops.py screenshot --output /tmp/v.png --with-cursor
   → visually confirm cursor is on "发送" button
8. $PY desktop_ops.py click --x 450 --y 520
9. $PY desktop_ops.py screenshot --output /tmp/after.png
   → verify the message was sent
10. $PY cleanup_task.py --task-id "wechat-send"
```

### Example 2: Type in a search box

```
1. $PY desktop_ops.py focus-app --name "Safari"
2. $PY target_resolver.py --app "Safari" --text "搜索" --region-label top_search --python $PY
   → finds search box → {x:300, y:80, within_window:true}
3. $PY desktop_ops.py click --x 300 --y 80
4. $PY desktop_ops.py type --text "hello world"
5. $PY desktop_ops.py press --key return
```

---

## Reference Documents

Load as needed:

| Document | When to read |
|----------|-------------|
| `references/workflow.md` | Core 8-step closed loop |
| `references/platform-macos.md` | macOS-specific tools and permissions |
| `references/platform-windows.md` | Windows setup |
| `references/platform-linux.md` | Linux X11/Wayland setup |
| `references/operation-patterns.md` | Reusable task templates |
| `references/validation-patterns.md` | Two-stage validation |
| `references/precise-targeting.md` | 5-layer precision targeting |
| `references/chat-app-macos.md` | Chat app workflow |
| `references/app-wechat-macos.md` | WeChat-specific guidance |
| `references/reproducible-setup.md` | Host bring-up checklist |

## Scope

Use this skill for: chat apps, browsers, file managers, editors, office apps, system settings, any closed desktop software with no usable API.

## Hard Rules

1. **Always run auto-setup gate first**
2. **Always use EXACT parameter names from CLI reference**
3. **Always scope OCR to the target app window — NEVER full-screen OCR**
4. **Always focus-app → front-window-bounds → window-scoped OCR → verify → click**
5. **Always pass `--python $PY` to ocr_text.py and target_resolver.py**
6. **Always verify the target coordinate is within the app window bounds before clicking**
7. One action at a time; verify after each
8. Cleanup is mandatory at task end
9. Do not send/delete/confirm until the target is validated
10. If verification fails, recapture and rebuild — do not retry blindly
