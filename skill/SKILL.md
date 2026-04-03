---
name: desktop-agent-ops
description: Execute cross-platform desktop tasks through a packaged desktop automation skill that guides the main agent to observe the screen, focus apps and windows, call helper scripts for screenshots and input actions, verify each step, clean up task context, and only escalate to multi-agent collaboration when tasks become clearly multi-window or multi-app. Use when the user wants desktop GUI control, native app operation, window focus, screenshots, click and type flows, or cross-platform desktop workflows on macOS, Windows, or Linux.
version: 1.2.1
metadata:
  openclaw:
    requires:
      bins: [python3]
      anyBins: [cliclick, xdotool]
    emoji: 🖥️
    os: [macos, windows, linux]
    install:
      brew: [cliclick]
---

# Desktop Agent Ops

Use this skill as a **main-agent operating manual** for desktop GUI tasks.

---

## IMPORTANT: Tool Priority — When to Use This Skill

**This skill is NOT the first choice.** Before using desktop screen recognition, always try higher-level tools first:

### Priority order (MUST follow):

```
┌─────────────────────────────────────────────────────────────────────┐
│ Priority 1: MCP Servers & Structured APIs                          │
│   If an MCP server can control the target app → USE IT FIRST       │
│   Examples:                                                         │
│   - Browser automation → use chrome-devtools MCP (navigate, click,  │
│     fill, screenshot via CDP)                                       │
│   - File operations → use filesystem tools directly                 │
│   - Database queries → use database MCP                             │
│   - Slack/GitHub/Notion → use their respective MCP servers          │
│   WHY: Structured APIs are faster, more reliable, no OCR needed     │
├─────────────────────────────────────────────────────────────────────┤
│ Priority 2: Native CLI / AppleScript / OS APIs                      │
│   If the app has a CLI or scriptable interface → USE IT             │
│   Examples:                                                         │
│   - `open -a "App"` to launch apps                                  │
│   - `osascript` for AppleScript-automatable apps                    │
│   - `defaults` for system settings                                  │
│   WHY: Direct control, no screen parsing needed                     │
├─────────────────────────────────────────────────────────────────────┤
│ Priority 3: Desktop Agent Ops (THIS SKILL)                          │
│   Use ONLY when:                                                    │
│   - No MCP server exists for the target app                         │
│   - The app has no CLI or scriptable API                            │
│   - The task requires visual GUI interaction that cannot be done     │
│     through any structured interface                                │
│   Examples:                                                         │
│   - WeChat desktop (no API, no MCP)                                 │
│   - Native desktop apps with no automation support                  │
│   - Any app where you must "see the screen and click"               │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision checklist before using this skill:

1. **Is there an MCP server** for this app? (check available MCP tools) → If yes, use MCP
2. **Does the app have a CLI** or API? → If yes, use that
3. **Can AppleScript/osascript control it?** → If yes, use that
4. **None of the above work?** → Use this skill (Desktop Agent Ops)

> **Rule: Never use screen OCR to do what a structured API can do.**
> Opening a URL in Chrome via `chrome-devtools MCP navigate` is always better than
> OCR-finding the address bar and typing into it.

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
2. `cliclick` (macOS via brew; Linux: xdotool/wmctrl guide printed)
3. Python venv + platform-specific dependencies (via uv or pip):
   - **macOS**: pyobjc (Accessibility API + Vision OCR) + pillow, pyautogui, opencv-python, numpy
   - **Windows/Linux**: pytesseract + pillow, pyautogui, opencv-python, numpy
4. OCR setup: macOS uses Vision Framework (built-in, no Tesseract needed); Linux/Windows uses Tesseract
5. OS permissions (Screen Recording, Accessibility, Automation) with auto-open System Settings
6. Smoke test (screenshot + mouse move verification)

After setup, set `$PY` for ALL subsequent calls:
```
PY=<output.env.DESKTOP_AGENT_OPS_PYTHON>
```

**Do NOT proceed if setup is not ready.**

---

## Core Execution Loop

Every desktop task follows this loop. No exceptions.

```
 1. auto-setup gate           ← run once per session
 2. init task context          ← create isolated temp directory
 3. FOCUS the target app       ← bring app to front, confirm frontmost
 4. GET window bounds          ← know exact position and size
 5. CAPTURE that window        ← screenshot ONLY the target window
 6. ANALYZE the capture        ← read screenshot or run OCR
 7. LOCATE target via OCR      ← find text/button within window bounds
 8. VERIFY before acting       ← move cursor, screenshot with cursor, confirm
 9. EXECUTE one action         ← click, type, scroll, press key
10. CAPTURE again              ← screenshot to see result
11. VERIFY the result          ← did the UI change as expected?
12. → if more steps, go to 5
13. CLEANUP                    ← remove task temp directory
```

**Key principles:**
- One action at a time. Never chain blind actions.
- Always verify after each action. If verification fails, recapture and retry — do NOT guess.
- Always work within a specific window. Never click based on full-screen assumptions.

---

## Smart Targeting with Three-Layer Fallback

**NEVER do OCR or clicking on a full-screen screenshot.** Always scope to the target app window.

### Three-Layer Targeting Pipeline

`target_resolver.py` automatically selects the best targeting method:

```
┌────────────────────────────────────────────────────────────┐
│ Layer 1: ACCESSIBILITY API (fastest, most accurate)        │
│   macOS: AXUIElement via PyObjC                            │
│   → Queries UI element tree directly, no screenshot needed │
│   → Returns role, title, position, size for each element   │
│   → 100% text accuracy, native CJK, ~34ms                 │
│   → Auto-degrades if element_count < 10 (WeChat, QQ, etc.)│
├────────────────────────────────────────────────────────────┤
│ Layer 2: SYSTEM OCR (fast, no external deps)               │
│   macOS: Apple Vision Framework                            │
│   → Built-in OCR, no Tesseract install needed              │
│   → Superior CJK (no character splitting), ~147ms          │
│   → Handles DPI natively                                   │
├────────────────────────────────────────────────────────────┤
│ Layer 3: TESSERACT OCR (cross-platform fallback)           │
│   All platforms: pytesseract                               │
│   → Used when Vision is unavailable (Linux, Windows)       │
│   → Requires external tesseract binary + language packs    │
├────────────────────────────────────────────────────────────┤
│ Layer 4: TEMPLATE MATCH + HEURISTIC (last resort)          │
│   → Image-based icon matching or geometry-based targeting  │
└────────────────────────────────────────────────────────────┘
```

### How it works in practice:

| App type | What happens |
|----------|-------------|
| Finder, Safari, Notes, System Settings | Layer 1 (Accessibility) finds elements in ~34ms |
| WeChat, QQ, Electron apps | Layer 1 detects < 10 elements → auto-falls to Layer 2 (Vision OCR) |
| Linux / Windows apps | Layer 2 skipped → Layer 3 (Tesseract) |
| Icons without text | Layer 4 (template match) |

### Shortcut (RECOMMENDED for most targeting):

```bash
$PY scripts/target_resolver.py --app "AppName" --text "按钮文字" --python $PY
```

This single command: focuses app → tries Accessibility → falls back to OCR if needed → returns `best_candidate` with `{x, y, within_window, source}`.

The `source` field tells you which layer found the target:
- `"accessibility"` — found via AX element tree (fastest, most reliable)
- `"ocr_vision"` — found via Vision OCR (no Tesseract needed)
- `"ocr_tesseract"` — found via Tesseract (fallback)

### Why window-scoped matters:

| Approach | Risk |
|----------|------|
| Full-screen OCR | "搜索" in WeChat AND Chrome → clicks wrong app |
| Window-scoped | "搜索" ONLY in WeChat window → correct click |

---

## Failure Recovery (CRITICAL)

When something fails, follow these rules:

### OCR finds nothing
1. Re-focus the app: `focus-app --name "AppName"`
2. Re-get bounds: `front-window-bounds --app "AppName"` (window may have moved/resized)
3. Take a fresh screenshot and read it visually
4. Try a different region label (e.g. `content_area` instead of `bottom_input`)
5. Try lowering OCR confidence: `--min-conf 30`

### Click doesn't work
1. Screenshot with cursor to check cursor position
2. The window may have moved — re-get bounds
3. Try clicking a few pixels offset from the OCR center
4. Check if a dialog/popup is blocking the target

### App state changed (login screen, dialog, etc.)
1. ALWAYS re-get window bounds after any major UI change
2. ALWAYS re-run OCR after navigation or state change
3. Never reuse old coordinates — they may be stale

### General retry rule
- Maximum 3 retries per action
- Each retry must recapture fresh state
- If 3 retries fail, report the failure with screenshots and stop

---

## Generalization: How to Apply This to ANY App

The pipeline works for any desktop application. Here is how to reason about new apps:

### Step-by-step for ANY new app:

1. **Identify the app name** exactly as it appears in the system (e.g. "Google Chrome", "微信", "System Settings")
2. **Focus and get bounds** — this tells you the window's exact position
3. **Screenshot the window** — look at what's on screen
4. **Identify the target** — what text, button, or area do you need to interact with?
5. **Use OCR to find it** — `target_resolver.py --app "AppName" --text "target text"`
6. **Verify and click**

### Common patterns across apps:

| Task | How to do it |
|------|-------------|
| Click a button | OCR find text → verify → click |
| Type in a field | OCR find field label → click field → `type --text` |
| Search for something | OCR find search box → click → type query → press return |
| Scroll a list | Get window bounds → scroll at window center with `--x --y` |
| Switch between apps | `focus-app --name "OtherApp"` → re-get bounds |
| Handle a dialog | Screenshot → OCR for dialog buttons → click appropriate one |
| Navigate menus | Click menu item → wait → screenshot → OCR new menu → click |
| Select from dropdown | Click dropdown → wait → OCR options → click selection |
| Read screen content | OCR the window → extract all text boxes |
| Verify an action | Screenshot before and after → compare or OCR for expected text |

### App-specific adaptations:

| App type | Special considerations |
|----------|----------------------|
| Chat apps (WeChat, Slack, etc.) | Verify conversation title before typing; use `insert-newline` for multi-line; verify send mechanism |
| Browsers (Chrome, Safari, etc.) | Address bar at top; content area varies; may need to handle tabs |
| System Settings | Deep navigation; panels change; re-get bounds after each navigation |
| File managers (Finder, Explorer) | Sidebar + content area; double-click to open; path bar for navigation |
| Editors (VS Code, TextEdit, etc.) | Tab bar + editor area; use hotkeys for save/undo; type in editor area |

---

## Text Input and Send Rules

### Typing text
```bash
$PY scripts/desktop_ops.py type --text "your message"
```
- Uses **clipboard paste** as primary method on all platforms — reliable for all languages including CJK
- macOS: `set the clipboard to` + `Cmd+V` (single osascript call)
- Windows: PowerShell `Set-Clipboard` + `Ctrl+V` (falls back to `clip.exe`)
- Linux: `xclip` + `Ctrl+V`
- First click on the input field to focus it before typing

### Multi-line messages
```bash
$PY scripts/desktop_ops.py type --text "first line"
$PY scripts/desktop_ops.py insert-newline
$PY scripts/desktop_ops.py type --text "second line"
```
- Use `insert-newline` for literal line breaks
- Do NOT use `\n` in `type --text` — it may trigger send in some apps

### Sending a message
1. **Preferred**: Look for a visible send button (e.g., `发送`) via OCR, then click it
2. **Alternative**: Use `press --key return` ONLY when the app is verified to use Enter-to-send
3. **Never guess** which send method to use — verify first

### Backend priority (macOS)
| Operation | Primary | Fallback |
|-----------|---------|----------|
| `type` | Clipboard paste | cliclick (ASCII only) |
| `press` | AppleScript `key code` | cliclick `kp:` |
| `hotkey` | cliclick `kd:/t:/ku:` | pyautogui |
| `click` | cliclick | pyautogui |

> **Important**: cliclick `kp:return` is NOT recognized by WeChat — always use AppleScript for key press.
> **Important**: cliclick `t:` silently drops CJK characters — always use clipboard paste for text input.

---

## DPI / HiDPI / Retina (All Platforms)

**Handled automatically.** No manual DPI work needed.

| Platform | Common scales | Detection method |
|----------|---------------|-----------------|
| macOS Retina | 2.0x | screenshot pixels ÷ logical screen bounds |
| Windows HiDPI | 1.25x, 1.5x, 2.0x | screenshot pixels ÷ pyautogui.size() |
| Linux X11 | 1.0x, 1.5x, 2.0x | screenshot pixels ÷ pyautogui.size() |

OCR output: `box` = logical (use for mouse), `pixel_box` = raw pixels, `dpi_scale` = factor.

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
$PY scripts/desktop_ops.py mouse-position
$PY scripts/desktop_ops.py press --key KEY
$PY scripts/desktop_ops.py type --text "text to type"
$PY scripts/desktop_ops.py insert-newline [--count N]
$PY scripts/desktop_ops.py hotkey --keys cmd c
$PY scripts/desktop_ops.py screen-size
$PY scripts/desktop_ops.py pixel-color --x X --y Y
```

### ax_provider.py (macOS Accessibility API)

```bash
$PY scripts/ax_provider.py --app "AppName" --text "text" [--text-match contains|exact|regex] [--max-depth 6]
$PY scripts/ax_provider.py --app "AppName" --text "text" --elements  # include full element tree
```

### vision_ocr.py (macOS Vision Framework OCR)

```bash
$PY scripts/vision_ocr.py --image /path/to/capture.png [--lang zh-Hans,en-US] [--level fast|accurate]
```

### ocr_text.py (multi-backend OCR)

```bash
$PY scripts/ocr_text.py --app "AppName" --python $PY [--region-label LABEL] [--backend auto|vision|tesseract]
$PY scripts/ocr_text.py --image /path/to/capture.png --python $PY [--backend auto]
```

### target_resolver.py (three-layer smart targeting)

```bash
$PY scripts/target_resolver.py --app "AppName" --text "text" --python $PY
$PY scripts/target_resolver.py --app "AppName" --template /path/icon.png --python $PY
$PY scripts/target_resolver.py --app "AppName" --text "text" --region-label LABEL --python $PY
# Provider order (default: accessibility first):
$PY scripts/target_resolver.py --app "AppName" --text "text" --providers "accessibility,ocr_text" --python $PY
```

### task_context.py / cleanup_task.py

```bash
$PY scripts/task_context.py init --task-id "my-task"   # aliases: create, --name
$PY scripts/task_context.py show --task-id "my-task"
$PY scripts/cleanup_task.py --task-id "my-task"
```

### window_regions.py

```bash
$PY scripts/window_regions.py --window-x X --window-y Y --window-width W --window-height H [--label LABEL]
```

Labels: `top_search`, `left_sidebar`, `left_sidebar_top`, `title_header`, `content_area`, `toolbar_row`, `bottom_input`, `primary_action`

---

## Workflow Examples

### Example 1: Click a button by text (any app)

```
1. $PY first_run_setup.py --check                           → ready: true
2. $PY task_context.py init --task-id "click-button"
3. $PY desktop_ops.py focus-app --name "AppName"
4. $PY desktop_ops.py front-window-bounds --app "AppName"    → {x, y, w, h}
5. $PY target_resolver.py --app "AppName" --text "OK" --python $PY
   → best_candidate: {x:450, y:520, within_window:true}
6. $PY desktop_ops.py move --x 450 --y 520
7. $PY desktop_ops.py screenshot --with-cursor               → verify cursor on "OK"
8. $PY desktop_ops.py click --x 450 --y 520
9. $PY desktop_ops.py screenshot                             → verify result
10. $PY cleanup_task.py --task-id "click-button"
```

### Example 2: Type and search

```
1. $PY desktop_ops.py focus-app --name "Safari"
2. $PY target_resolver.py --app "Safari" --text "Search" --region-label top_search --python $PY
   → {x:300, y:80, within_window:true}
3. $PY desktop_ops.py click --x 300 --y 80
4. $PY desktop_ops.py type --text "hello world"
5. $PY desktop_ops.py press --key return
6. $PY desktop_ops.py screenshot                             → verify search results
```

### Example 3: Send a chat message (WeChat, Slack, etc.)

```
1. $PY desktop_ops.py focus-app --name "WeChat"
2. $PY desktop_ops.py front-window-bounds --app "WeChat"
3. # Navigate to the right conversation (OCR sidebar or search)
4. $PY target_resolver.py --app "WeChat" --text "ContactName" --region-label left_sidebar --python $PY
5. $PY desktop_ops.py click --x <found_x> --y <found_y>
6. # Verify conversation is open
7. $PY desktop_ops.py screenshot → confirm conversation title
8. # Click the input field
9. $PY target_resolver.py --app "WeChat" --text "" --region-label bottom_input --python $PY
10. $PY desktop_ops.py click --x <found_x> --y <found_y>
11. $PY desktop_ops.py type --text "Hello!"
12. $PY desktop_ops.py screenshot → verify typed text visible in composer
13. # Send: MUST use --region-label to avoid matching message text that contains "发送"
14. $PY target_resolver.py --app "WeChat" --text "发送" --region-label primary_action --python $PY
    IF found: $PY desktop_ops.py click --x <x> --y <y>
    ELSE: $PY desktop_ops.py press --key return
15. $PY desktop_ops.py screenshot → verify message sent
```

### Example 4: Scroll a list and find an item

```
1. $PY desktop_ops.py focus-app --name "AppName"
2. $PY desktop_ops.py front-window-bounds --app "AppName"   → {x:100, y:50, w:800, h:600}
3. # Scroll down in the window center
   $PY desktop_ops.py scroll --amount -5 --x 500 --y 350
4. $PY desktop_ops.py screenshot                             → check if target visible
5. $PY target_resolver.py --app "AppName" --text "target item" --python $PY
6. IF not found: scroll more and retry (max 5 scrolls)
7. IF found: click it
```

### Example 5: Handle an unexpected dialog

```
1. # During any operation, if the expected UI doesn't match:
2. $PY desktop_ops.py screenshot → examine what's on screen
3. # If a dialog is visible, OCR it:
   $PY ocr_text.py --app "AppName" --python $PY
4. # Find and click the appropriate button (OK, Cancel, Allow, etc.)
   $PY target_resolver.py --app "AppName" --text "OK" --python $PY
5. $PY desktop_ops.py click --x <x> --y <y>
6. # After dialog is dismissed, re-get window bounds and continue
   $PY desktop_ops.py front-window-bounds --app "AppName"
```

---

## Reference Documents

**MUST-read rules**: Read the matching reference BEFORE starting the task. Do not skip.

| Document | When to read |
|----------|-------------|
| `references/workflow.md` | Core 8-step closed loop |
| `references/platform-macos.md` | **MUST** when running on macOS |
| `references/platform-windows.md` | **MUST** when running on Windows |
| `references/platform-linux.md` | **MUST** when running on Linux |
| `references/operation-patterns.md` | Reusable task templates |
| `references/validation-patterns.md` | **MUST** when task involves send, delete, or other destructive actions |
| `references/precise-targeting.md` | **MUST** when OCR finds nothing or click misses target |
| `references/target-providers.md` | Provider ordering and fallback contract |
| `references/coordinate-reconstruction.md` | Rebuild click coordinates from screenshot evidence |
| `references/chat-app-macos.md` | **MUST** when target app is a chat app (WeChat, Slack, Telegram, etc.) |
| `references/app-wechat-desktop.md` | **MUST** when target app is WeChat |
| `references/cleanup-rules.md` | Cleanup timing and scope |
| `references/collaboration-rules.md` | When multi-agent collaboration is justified |
| `references/example-cases.md` | Repeatable task examples |
| `references/reproducible-setup.md` | Host bring-up checklist |

## Scope

**Use this skill ONLY when no structured API (MCP, CLI, AppleScript) can accomplish the task.**

Typical use cases:
- Chat apps with no API (WeChat, QQ, Telegram desktop)
- Native desktop apps with no automation support
- System Settings / Preferences navigation
- Any closed desktop software where you must "see and click"

**Do NOT use this skill for:**
- Browser automation → use `chrome-devtools` MCP instead
- File operations → use filesystem tools directly
- Apps with MCP servers → use MCP
- Tasks achievable via CLI or AppleScript

## Hard Rules

1. **MCP/API first: never use screen recognition when a structured tool can do the job**
2. **Always run auto-setup gate first**
3. **Always use EXACT parameter names from CLI reference — never guess**
4. **Always scope targeting to the target app window — NEVER full-screen**
5. **Always: focus-app → front-window-bounds → target (AX or OCR) → verify → act**
6. **Always pass `--python $PY` to ocr_text.py and target_resolver.py**
7. **Always verify coordinates are within window bounds before clicking**
8. **Always re-get window bounds after any UI state change (login, dialog, navigation)**
9. **Use `insert-newline` for line breaks; never use `\n` in `type --text`**
10. **For send actions: prefer visible send button; use `press --key return` only when verified**
11. **One action at a time; verify after each**
12. **Maximum 3 retries per action; each retry must recapture fresh state**
13. **Cleanup is mandatory at task end**
14. **If verification fails, recapture and rebuild — do not retry blindly**

---

## Custom Workflows

Users can create reusable multi-step workflows and share them with the community.

### Workflow CLI

```bash
# List available workflows (built-in + user-created)
$PY scripts/workflow_runner.py list

# Show workflow details
$PY scripts/workflow_runner.py show --workflow "send-chat-message"

# Validate a workflow (format check)
$PY scripts/workflow_runner.py validate --workflow "send-chat-message"

# Preview resolved commands (for safety review before execution)
$PY scripts/workflow_runner.py preview --workflow "send-chat-message" --param contact="John" --param message="Hello"

# Run a workflow
$PY scripts/workflow_runner.py run --workflow "send-chat-message" --param contact="John" --param message="Hello"

# Share a workflow to the community via GitHub PR
$PY scripts/workflow_share.py share --workflow "send-chat-message"
```

### Agent Safety Review Protocol

Before running any workflow, the agent MUST:
1. Call `preview` to see all resolved commands
2. Review each command using your own reasoning — judge whether it is safe
3. If any command looks risky (deletion, network exfiltration, system config changes), explain the risk to the user and ask for confirmation
4. Only call `run` after confirming safety

This is NOT a whitelist approach — workflows can contain any command for maximum extensibility. Safety relies on the agent's judgment, not hardcoded rules.

### Workflow File Location

- Built-in workflows: `skill/workflows/`
- User workflows: `~/.openclaw-desktop-agent-ops/workflows/`
- User workflows override built-in ones with the same name

### Sharing Workflows

After a user creates a custom workflow, ask: "Workflow validated. Would you like to share it with the community?"

If yes, run `workflow_share.py share --workflow "name"`. The script will:
1. Validate workflow format
2. Scan for sensitive information (API keys, passwords, personal paths are blocked)
3. Fork the repo and create a GitHub PR to contribute the workflow
4. Return the PR URL to the user
