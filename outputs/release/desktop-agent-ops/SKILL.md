---
name: desktop-agent-ops
description: Use when the user needs cross-platform desktop GUI control of a native app or window and no MCP server, native CLI, or OS API can safely complete the task.
version: 1.4.0
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

> This is the detailed reference manual. For the quick operations guide, see `desktop-agent-ops.md`.

# Desktop Agent Ops — Detailed Reference Manual

---

## Table of Contents

- [Tool Priority](#tool-priority)
- [Auto-setup Gate](#auto-setup-gate)
- [Core Execution Loop](#core-execution-loop)
- [Smart Targeting with Four-Layer Fallback](#smart-targeting-with-four-layer-fallback)
- [Failure Recovery](#failure-recovery)
- [Generalization: How to Apply This to ANY App](#generalization-how-to-apply-this-to-any-app)
- [Text Input and Send Rules](#text-input-and-send-rules)
- [DPI / HiDPI / Retina](#dpi--hidpi--retina)
- [CLI Reference](#cli-reference-key-commands-with-full-parameters)
- [Workflow Examples](#workflow-examples)
- [Reference Documents](#reference-documents)
- [Scope](#scope)
- [Hard Rules](#hard-rules)
- [Custom Workflows](#custom-workflows)

---

## Tool Priority

Use this skill ONLY as Priority 3 — after MCP servers/structured APIs (Priority 1) and native CLI/AppleScript (Priority 2). See `desktop-agent-ops.md` section 1 for the full decision framework.

> **Rule: Never use screen OCR to do what a structured API can do.**

---

## Auto-setup Gate

Run `first_run_setup.py --check` at session start. If not ready, run `first_run_setup.py` to auto-install all dependencies. Then set `$PY`. See `desktop-agent-ops.md` section 2 for details.

---

## Core Execution Loop

```
FOCUS → LOCATE (accessibility/OCR) → BOUNDS-CHECK → MOVE → READBACK → EXECUTE → VERIFY
```

**CRITICAL RULE: Click coordinates MUST come from accessibility or OCR output — NEVER from visual estimation of screenshots.** Models frequently confuse left/right and misjudge pixel distances. Structured accessibility and OCR output return exact pixel coordinates.

**CRITICAL RULE: Move → Readback → Click.** Before every click, move the cursor first, read back `mouse-position`, verify the offset is ≤ 5px, then click. Never click without readback.

**CRITICAL RULE: Re-locate before every click in multi-step tasks.** Window positions, dialog states, and UI layouts change between steps. Never reuse coordinates from a previous step.

See `desktop-agent-ops.md` section 3 for the full 7-step mandatory loop.

---

## Smart Targeting with Four-Layer Fallback

**NEVER do OCR or clicking on a full-screen screenshot.** Always scope to the target app window.

**ACCESSIBILITY-FIRST PRINCIPLE**: Use `accessibility_provider.py` as the cross-platform direct query path. It dispatches to macOS AXUIElement, Windows UI Automation, or Linux AT-SPI and returns structured JSON with zero screenshot overhead. Only fall to OCR for accessibility-degraded apps (WeChat, QQ, Electron) or when you need visual content.

```bash
# Direct accessibility query — no screenshot, structured coordinates
$PY scripts/accessibility_provider.py --app "AppName" --text "target text"

# Inspect full UI tree — understand app structure without any screenshot
$PY scripts/accessibility_provider.py --app "AppName" --elements
```

On macOS, `ax_provider.py` remains available as a direct backend when you specifically need raw AX data.

### Four-Layer Targeting Pipeline

`target_resolver.py` automatically selects the best targeting method:

```
┌────────────────────────────────────────────────────────────┐
│ Layer 1: ACCESSIBILITY API (fastest, most accurate)        │
│   macOS: AXUIElement via PyObjC                            │
│   Windows: UI Automation via PowerShell/.NET               │
│   Linux: AT-SPI via pyatspi (GNOME first-class)            │
│   → Queries UI element tree directly, no screenshot needed │
│   → Returns role, title, position, size for each element   │
│   → Returns exact element coordinates when the tree exists │
│   → Auto-degrades if element_count < 10 or the platform    │
│     blocks accessibility (WeChat, QQ, Electron, UIPI, etc.)│
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
| Finder, Safari, Notes, System Settings | Layer 1 (Accessibility) finds elements immediately |
| Native Windows apps (Notepad, Calculator) | Layer 1 (UIA) usually works when privileges match |
| GNOME apps with AT-SPI enabled | Layer 1 (AT-SPI) works without screenshots |
| WeChat, QQ, Electron apps | Layer 1 detects < 10 elements → auto-falls to Layer 2 (Vision OCR) |
| Linux or Windows apps without usable accessibility | Layer 2 skipped or blocked → Layer 3 (Tesseract) |
| Icons without text | Layer 4 (template match) |

### Shortcut (RECOMMENDED for most targeting):

```bash
$PY scripts/target_resolver.py --app "AppName" --text "按钮文字" --python $PY
```

This single command: focuses app → tries Accessibility → falls back to OCR if needed → returns `best_candidate` with `{x, y, within_window, source}`.

The `source` field tells you which layer found the target:
- `"accessibility"` — found via a structured accessibility tree (AX, UIA, or AT-SPI)
- `"ocr_vision"` — found via Vision OCR (no Tesseract needed)
- `"ocr_tesseract"` — found via Tesseract (fallback)

### Why window-scoped matters:

| Approach | Risk |
|----------|------|
| Full-screen OCR | "搜索" in WeChat AND Chrome → clicks wrong app |
| Window-scoped | "搜索" ONLY in WeChat window → correct click |

---

## Failure Recovery

Max 3 retries per action. Each retry MUST recapture fresh state. See `desktop-agent-ops.md` section 5 for the quick reference table.

### OCR finds nothing
1. Re-focus the app: `focus-app --name "AppName"`
2. Re-get bounds: `front-window-bounds --app "AppName"` (window may have moved/resized)
3. Take a fresh screenshot and read it visually
4. Try a different region label (e.g. `content_area` instead of `bottom_input`)
5. Try lowering OCR confidence: `--min-conf 30` (for `ocr_text.py`) or `--ocr-min-conf 30` (for `target_resolver.py`)

### Accessibility is blocked or degraded
1. Re-run `platform_probe.py` and `doctor.py` to confirm the backend and blockers
2. Windows: verify the agent and target app run at the same privilege level; elevated apps and UAC prompts may be blocked by UIPI
3. Linux: verify GNOME/AT-SPI is available and `pyatspi` is installed; non-GNOME or restricted sessions may need OCR fallback
4. If the tree is sparse (`element_count < 10`), treat it as degraded and continue with OCR instead of guessing

### Click doesn't work
1. Screenshot with cursor to check cursor position
2. The window may have moved — re-get bounds
3. Try clicking a few pixels offset from the OCR center
4. Check if a dialog/popup is blocking the target

### App state changed (login screen, dialog, etc.)
1. ALWAYS re-get window bounds after any major UI change
2. ALWAYS re-run OCR after navigation or state change
3. Never reuse old coordinates — they may be stale

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

## DPI / HiDPI / Retina

Handled automatically. OCR returns logical coordinates (use for mouse); `pixel_box` = raw pixels; `dpi_scale` = factor. No manual DPI work needed.

---

## CLI Reference (Key Commands with Full Parameters)

For the complete quick reference of all commands, see `desktop-agent-ops.md` section 8.

### desktop_ops.py (full parameter reference)

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

### target_resolver.py (four-layer smart targeting)

```bash
$PY scripts/target_resolver.py --app "AppName" --text "text" --python $PY
$PY scripts/target_resolver.py --app "AppName" --template /path/icon.png --python $PY
$PY scripts/target_resolver.py --app "AppName" --text "text" --region-label LABEL --python $PY
$PY scripts/target_resolver.py --app "AppName" --text "text" --providers "accessibility,ocr_text" --python $PY
```

### ocr_text.py (multi-backend OCR)

```bash
$PY scripts/ocr_text.py --app "AppName" --python $PY [--region-label LABEL] [--backend auto|vision|tesseract]
$PY scripts/ocr_text.py --image /path/to/capture.png --python $PY [--backend auto]
```

---

## Workflow Examples

### Example: Send a chat message (WeChat, Slack, etc.)

> **IMPORTANT: Before starting, discover the correct app name dynamically.**
> 1. Run `desktop_ops.py list-apps` to see all running apps
> 2. Find the chat app name (e.g. "微信", "WeChat", "Slack")
> 3. Use that exact name in all --app arguments below

```
0. $PY desktop_ops.py list-apps  → find the chat app name (e.g. "WeChat" or "微信")
1. $PY desktop_ops.py focus-app --name "$CHAT_APP"   ← replace with discovered name
2. $PY desktop_ops.py front-window-bounds --app "$CHAT_APP"
3. # Navigate to the right conversation (OCR sidebar or search)
4. $PY target_resolver.py --app "$CHAT_APP" --text "ContactName" --region-label left_sidebar --python $PY
5. $PY desktop_ops.py click --x <found_x> --y <found_y>
6. # Verify conversation is open
7. $PY desktop_ops.py screenshot → confirm conversation title
8. # Click the input field
9. $PY target_resolver.py --app "$CHAT_APP" --text "" --region-label bottom_input --python $PY
10. $PY desktop_ops.py click --x <found_x> --y <found_y>
11. $PY desktop_ops.py type --text "Hello!"
12. $PY desktop_ops.py screenshot → verify typed text visible in composer
13. # Send: MUST use --region-label to avoid matching message text that contains "发送"
14. $PY target_resolver.py --app "$CHAT_APP" --text "发送" --region-label primary_action --python $PY
    IF found: $PY desktop_ops.py click --x <x> --y <y>
    ELSE: $PY desktop_ops.py press --key return
15. $PY desktop_ops.py screenshot → verify message sent
```

### Example: Handle an unexpected dialog

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

See `desktop-agent-ops.md` section 12 for the complete on-demand reference table. Key references:

| Document | When to read |
|----------|-------------|
| `references/workflow.md` | Core task lifecycle (macro-level) |
| `references/platform-macos.md` | **MUST** when running on macOS |
| `references/platform-windows.md` | When running on Windows |
| `references/platform-linux.md` | When running on Linux |
| `references/precise-targeting.md` | **MUST** when OCR finds nothing or click misses |
| `references/target-providers.md` | Accessibility vs OCR vs Tesseract provider selection |
| `references/chat-app-macos.md` | **MUST** when target is a chat app |
| `references/app-wechat-desktop.md` | **MUST** when target is WeChat |
| `references/app-wechat-macos.md` | WeChat macOS compatibility pointer |
| `references/app-wechat-windows.md` | WeChat Windows compatibility pointer |
| `references/validation-patterns.md` | **MUST** for send, delete, or destructive actions |
| `references/operation-patterns.md` | Reusable operation patterns |
| `references/coordinate-reconstruction.md` | Rebuilding coordinates from screenshots |
| `references/collaboration-rules.md` | Multi-agent collaboration |
| `references/custom-workflows.md` | Authoring and running workflows |
| `references/cleanup-rules.md` | **MUST** cleanup rules at task end |
| `references/reproducible-setup.md` | Cross-host reproducible setup |
| `references/eval-scenarios.md` | Skill evaluation scenarios |
| `references/example-cases.md` | Public-safe repeatable examples |
| `references/app-names.md` | App name patterns: macOS process names vs Windows window titles, discovery rules |
| `references/market-precision-targeting-gap-analysis.md` | Precision targeting gaps |

---

## Scope

Use this skill ONLY when no structured API (MCP, CLI, AppleScript) can accomplish the task. Typical targets: chat apps (WeChat, QQ), native desktop apps without automation APIs, System Settings, any closed software where you must "see and click".

---

## Hard Rules

1. **MCP/API first: never use screen recognition when a structured tool can do the job**
2. **Accessibility before screenshot: use the platform accessibility tree to locate targets before taking screenshots — structured output costs ~200 tokens; a screenshot costs 30,000-60,000 tokens**
3. **NEVER estimate click coordinates from screenshots — always use accessibility or OCR output values. Models confuse left/right and misjudge distances. This is the #1 cause of click errors.**
4. **Move → Readback → Click: always move first, read back mouse-position, verify offset ≤ 5px, then click. Never click without readback.**
5. **Re-locate before every click in multi-step tasks — never reuse stale coordinates from a previous step**
6. **For close/quit: prefer CLI/AppleScript/process APIs; only click if no API exists, and use the platform accessibility tree to get the exact close button position at pixel level**
7. **Always run auto-setup gate first**
8. **Always use EXACT parameter names from CLI reference — never guess**
9. **Always scope targeting to the target app window — NEVER full-screen**
10. **Always: focus-app → front-window-bounds → accessibility/OCR locate → bounds-check → move → readback → click → verify**
11. **Always pass `--python $PY` to ocr_text.py and target_resolver.py**
12. **Always verify coordinates are within window bounds before clicking**
13. **Always re-get window bounds after any UI state change (login, dialog, navigation)**
14. **Use `insert-newline` for line breaks; never use `\n` in `type --text`**
15. **For send actions: prefer visible send button; use `press --key return` only when verified**
16. **One action at a time; verify after each**
17. **Maximum 3 retries per action; each retry must recapture fresh state**
18. **Cleanup is mandatory at task end**
19. **If verification fails, recapture and rebuild — do not retry blindly**
20. **Discard old screenshots from context after each action — only analyze the current capture. Prefer region captures over full-screen.**

---

## Custom Workflows

Users can create reusable multi-step workflows. See `references/custom-workflows.md` for full details on workflow CLI, safety review protocol, and sharing.

Workflow locations:
- Built-in: `skill/workflows/`
- User-created: `~/.claude/desktop-agent-ops/workflows/`
