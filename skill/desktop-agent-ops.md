---
name: desktop-agent-ops
description: Use when the user needs cross-platform desktop GUI control of a native app or window and no MCP server, native CLI, or OS API can safely complete the task.
whenToUse: When no MCP server, native CLI, or OS API can accomplish the task, and the user needs to control a desktop application through verified GUI interaction. Prefer structured accessibility trees first, then OCR fallback. Typical targets include WeChat, QQ, native desktop apps without automation APIs, and System Settings.
effort: 4
tools:
  - Bash
  - Read
  - Glob
disallowedTools:
  - Write
  - Edit
  - NotebookEdit
---

# Desktop Agent Ops — Quick Operations Manual

## 1. Tool Priority (MUST follow before using this skill)

1. **MCP Servers & Structured APIs** — browser via chrome-devtools MCP, Slack/GitHub/Notion via their MCPs, file ops via filesystem tools
2. **Native CLI / AppleScript / OS APIs** — `open -a`, `osascript`, `defaults`, any app CLI
3. **Desktop Agent Ops (this skill)** — ONLY when none of the above can do the job

> **Rule: Never use screen OCR to do what a structured API can do.**

---

## 2. Auto-setup Gate (FIRST ACTION, every session)

```bash
python3 <SKILL_DIR>/scripts/first_run_setup.py --check
```

- If `"ready": false` → run `python3 <SKILL_DIR>/scripts/first_run_setup.py` (installs everything automatically)
- After setup, set `$PY` for ALL subsequent calls:
  ```
  PY=<output.env.DESKTOP_AGENT_OPS_PYTHON>
  ```
- **Do NOT proceed if setup is not ready.**

---

## 3. Core Execution Loop (MANDATORY — no shortcuts)

Every desktop task follows these phases. **No exceptions. No skipping steps.**

```
1. FOCUS       →  focus-app + front-window-bounds → record {wx, wy, ww, wh}
2. LOCATE      →  accessibility tree or OCR → get target {x, y} in absolute pixel coordinates
3. BOUNDS-CHECK →  assert wx ≤ x ≤ wx+ww AND wy ≤ y ≤ wy+wh
                   If FAILS → re-get bounds → re-locate → if still fails, STOP
4. MOVE        →  move --x X --y Y
5. READBACK    →  mouse-position → compare returned {mx, my} vs intended {x, y}
                   If |mx - x| > 5 or |my - y| > 5 → STOP, do not click
6. EXECUTE     →  one action only (click / type / scroll / press)
7. VERIFY      →  screenshot → confirm expected UI change happened
```

### CRITICAL: Never estimate positions from screenshots

**You MUST get click coordinates from AX or OCR output, NEVER from visually looking at a screenshot.**

Why: Models (especially smaller ones) frequently confuse left/right, misjudge distances, and estimate wrong pixel positions when interpreting images. AX and OCR return exact pixel coordinates — use those.

| Approach | Reliability | Use when |
|----------|-------------|----------|
| Accessibility `matches[].x, matches[].y` | **Exact** (pixel-perfect) | App exposes a usable accessibility tree |
| OCR `best_candidate.x, best_candidate.y` | **High** (text-anchored) | AX degraded, text visible |
| Model visually estimates from screenshot | **UNRELIABLE — FORBIDDEN** | Never for click targets |

### How to LOCATE (step 2) correctly:

```bash
# Method A: Accessibility-first (preferred — no screenshot, exact coordinates)
$PY scripts/accessibility_provider.py --app "AppName" --text "button text"
# Output: {"matches": [{"x": 523, "y": 347, "width": 80, "height": 24, ...}]}
# USE these x, y values directly — they are exact pixel positions

# Method B: Full pipeline with auto-fallback
$PY scripts/target_resolver.py --app "AppName" --text "button text" --python $PY
# Output: {"best_candidate": {"x": 523, "y": 347, "source": "accessibility"}}
# USE best_candidate.x, best_candidate.y directly

# Method C: OCR all text in window (when you need to find what's on screen)
$PY scripts/ocr_text.py --app "AppName" --python $PY
# Output: {"boxes": [{"text": "发送", "abs_box": {"x": 500, "y": 700, "width": 60, "height": 24}}]}
# Click position = abs_box.x + abs_box.width/2, abs_box.y + abs_box.height/2
```

**Every click coordinate MUST come from one of these three sources. Period.**

On macOS, for a known AX-friendly app where you specifically need raw AX details, `ax_provider.py` is still a valid direct backend. For cross-platform work, prefer `accessibility_provider.py`.

---

## 4. Position Verification Protocol (MANDATORY before every click)

This protocol catches stale coordinates, moved windows, and targeting errors.

```bash
# Step 1: Move cursor to target position (DO NOT CLICK YET)
$PY scripts/desktop_ops.py move --x <target_x> --y <target_y>

# Step 2: Read back actual cursor position
$PY scripts/desktop_ops.py mouse-position
# Returns: {"x": 523, "y": 347}

# Step 3: Compare — if offset > 5px, STOP
# If |returned_x - target_x| > 5 OR |returned_y - target_y| > 5 → do NOT click

# Step 4: Only now click
$PY scripts/desktop_ops.py click --x <target_x> --y <target_y>

# Step 5: Verify UI changed
$PY scripts/desktop_ops.py screenshot
```

**When to use cursor-visible screenshot** (high-stakes actions):

For destructive actions (send, delete, close, confirm), add a visual verification step between move and click:

```bash
$PY scripts/desktop_ops.py move --x <x> --y <y>
$PY scripts/desktop_ops.py screenshot --with-cursor    # verify cursor is visually over the right element
$PY scripts/desktop_ops.py click --x <x> --y <y>
$PY scripts/desktop_ops.py screenshot                   # verify result
```

---

## 5. Close / Quit / Destructive Operations

**NEVER guess where close/quit buttons are.** Always use the process tree to find exact positions.

### macOS: Close a window or quit an app

```bash
# Preferred: use AX to find close button at pixel level
$PY scripts/ax_provider.py --app "AppName" --text "close" --elements
# Look for role: "AXButton", description: "close" → use its exact {x, y}

# Alternative: use native API (no GUI interaction needed)
osascript -e 'tell application "AppName" to quit'
# or
osascript -e 'tell application "System Events" to tell process "AppName" to click menu item "Quit AppName" of menu "AppName" of menu bar 1'

# For window close (not quit):
osascript -e 'tell application "System Events" to tell process "AppName" to click button 1 of window 1'
```

### Windows: Close a window

```bash
# Use UI Automation through the unified provider
$PY scripts/accessibility_provider.py --app "AppName" --text "Close"

# Alternative: use taskkill (no GUI needed)
taskkill /IM "app.exe"
```

### Linux: Close a window

```bash
# GNOME / AT-SPI session: structured lookup first
$PY scripts/accessibility_provider.py --app "AppName" --text "Close"

# Alternative: window-manager or process-level close if available
wmctrl -c "AppName"
```

### Taskbar / Dock interactions

```bash
# macOS Dock: use AX to find app icon position
$PY scripts/ax_provider.py --app "Dock" --text "AppName"
# Returns exact pixel position of the Dock icon

# Windows Taskbar: use UIA to find the taskbar button
$PY scripts/accessibility_provider.py --app "Shell_TrayWnd" --text "AppName"
```

**Rule: For close/quit, prefer CLI/AppleScript/API (no click needed). Only use click when no API exists, and ALWAYS use the platform accessibility tree to get the exact button position.**

---

## 6. Smart Targeting (Accessibility-first for Token Efficiency)

**Prefer the platform accessibility tree over screenshot+OCR whenever possible.** Structured accessibility output is JSON text, so it avoids image-token overhead and avoids model-side position guessing.

| Layer | Method | Speed | Token cost | Notes |
|-------|--------|-------|------------|-------|
| 1 | **Accessibility API** (`accessibility_provider.py`) | ~34ms to ~200ms | **~200 tokens** (JSON text) | macOS AX, Windows UIA, Linux AT-SPI; no screenshot needed |
| 2 | Vision Framework OCR (macOS) | ~147ms | ~30,000-60,000 tokens (screenshot) | Built-in, no Tesseract; superior CJK |
| 3 | Tesseract OCR | slower | ~30,000-60,000 tokens (screenshot) | Cross-platform fallback when accessibility is blocked or unavailable |
| 4 | Template match / heuristic | varies | ~30,000-60,000 tokens (screenshot) | Last resort for icons without text |

```bash
# PREFERRED: direct accessibility query (no screenshot, exact pixels)
$PY scripts/accessibility_provider.py --app "AppName" --text "button text"

# FULL PIPELINE: auto-fallback (use when unsure if accessibility will work)
$PY scripts/target_resolver.py --app "AppName" --text "button text" --python $PY

# INSPECT UI TREE: see all elements without any screenshot
$PY scripts/accessibility_provider.py --app "AppName" --elements
```

The `source` field in output tells you which layer found the target: `accessibility`, `ocr_vision`, or `ocr_tesseract`.

**When to use `accessibility_provider.py` directly vs `target_resolver.py`:**
- **Known accessibility-friendly apps**: use `accessibility_provider.py` directly
- **Unknown apps or accessibility-degraded apps** (WeChat, QQ, many Electron apps): use `target_resolver.py` — it tries structured lookup first and then falls to OCR
- **Need raw macOS AX details**: use `ax_provider.py` directly on macOS
- **Need to see actual screen content**: take a screenshot — accessibility only gives structure, not rendered pixels
- **Windows note**: UIA works best when the agent and target app run at the same privilege level; elevated apps and UAC prompts may be blocked by UIPI
- **Linux note**: AT-SPI is first-class for GNOME sessions with `pyatspi`; other sessions may fall back to OCR

---

## 7. Long Task Coordination Rules

In long multi-step tasks, state drifts. Follow these extra rules:

1. **Re-get window bounds before EVERY click** — windows move, dialogs appear, focus changes
2. **Re-run accessibility/OCR before EVERY click** — never reuse coordinates from a previous step
3. **Never assume previous coordinates are still valid** — even 1 step later, they may be stale
4. **After any app switch, dialog, or navigation**: full re-FOCUS + re-LOCATE cycle
5. **If a step fails, do NOT skip it** — re-locate from scratch and retry (max 3 times)

```
WRONG (stale coordinates):
  Step 1: AX finds "发送" at (523, 700)
  Step 2: type message
  Step 3: click (523, 700)          ← WRONG: window may have moved during typing

RIGHT (fresh coordinates each time):
  Step 1: AX finds "发送" at (523, 700), click input field
  Step 2: type message
  Step 3: AX finds "发送" again → now at (523, 705) ← position may have shifted
  Step 4: move to (523, 705), readback, verify, click
```

---

## 8. Failure Recovery

**General rule: max 3 retries per action. Each retry MUST recapture fresh state.**

| Failure | Recovery steps |
|---------|---------------|
| Accessibility/OCR finds nothing | Re-focus app → re-get bounds → try `--elements` to see full tree → try different text → lower `--min-conf 30` (ocr_text.py) or `--ocr-min-conf 30` (target_resolver.py) |
| Click misses target | mouse-position readback to check where cursor actually is → re-get bounds → re-locate with accessibility/OCR → try again |
| App state changed | Full re-FOCUS + re-LOCATE cycle → never reuse old coordinates |
| Permission or session blocked | Windows: check same privilege level and UIPI. Linux: check GNOME/AT-SPI session and `pyatspi`. Then fall back to OCR if safe. |
| Left/right confusion | **NEVER visually estimate** — always re-run accessibility/OCR for exact pixel coordinates |

If 3 retries fail, report the failure with the accessibility/OCR output and stop.

---

## 9. Screenshot Context Management

- **Discard old screenshots** — only analyze the current/latest capture.
- **Prefer region captures** over full-screen: `capture-region --x X --y Y --width W --height H`
- **Screenshots are for VERIFICATION only** — never use them to estimate click positions.
- After any UI state change (navigation, dialog, login), take a fresh screenshot before proceeding.
- DPI/Retina is handled automatically — accessibility/OCR return logical coordinates ready for mouse actions.

---

## 10. Hard Rules

1. **MCP/API first** — never use screen recognition when a structured tool can do the job.
2. **Accessibility before screenshot** — use the platform accessibility tree to locate targets before taking screenshots. Structured output costs ~200 tokens; a screenshot costs 30,000-60,000 tokens.
3. **NEVER estimate click coordinates from screenshots** — always use accessibility or OCR output values. Models confuse left/right and misjudge distances.
4. **Always run auto-setup gate** before any desktop operation.
5. **Use EXACT parameter names** from CLI reference — never guess or invent flags.
6. **Always scope to target window** — NEVER OCR or click on full-screen screenshots.
7. **Always pass `--python $PY`** to `ocr_text.py` and `target_resolver.py`.
8. **Bounds-check every coordinate** — assert target is within window bounds before clicking.
9. **Move → readback → click** — always move first, read back mouse-position, then click. Never click without readback.
10. **Re-get window bounds** after any UI state change (login, dialog, navigation, typing).
11. **Re-locate before every click** in multi-step tasks — never reuse stale coordinates.
12. **Use `insert-newline`** for line breaks; never use `\n` in `type --text`.
13. **For send actions**: prefer a visible send button via accessibility/OCR; use `press --key return` only when verified.
14. **For close/quit**: prefer CLI/AppleScript/process APIs; only click if no API exists, and use the platform accessibility tree for exact position.
15. **One action at a time; verify after each.** Never chain blind actions.

---

## 11. Key CLI Commands (Quick Reference)

```bash
# Setup & diagnostics
$PY scripts/first_run_setup.py --check
$PY scripts/doctor.py
$PY scripts/platform_probe.py

# Window management
# IMPORTANT: Always discover the correct app name first
#   1. Run: $PY scripts/desktop_ops.py list-apps  (to see all running apps)
#   2. Use the exact name returned by list-apps
#   3. If app not running, try: open -a "AppName" (macOS) or start "" "AppName" (Windows)
#   4. If name is uncertain, use web search to find the correct process/window name
$PY scripts/desktop_ops.py list-apps                        # Probe: discover app names first
$PY scripts/desktop_ops.py focus-app --name "App Name"   # Use exact name from list-apps
$PY scripts/desktop_ops.py front-window-bounds [--app NAME]
$PY scripts/desktop_ops.py frontmost

# Capture (for VERIFICATION only — not for estimating click positions)
$PY scripts/desktop_ops.py screenshot [--output PATH] [--with-cursor]
$PY scripts/desktop_ops.py capture-region --x X --y Y --width W --height H

# Mouse & keyboard
$PY scripts/desktop_ops.py click [--x X --y Y] [--button left|right|middle]
$PY scripts/desktop_ops.py double-click [--x X --y Y]
$PY scripts/desktop_ops.py move --x X --y Y
$PY scripts/desktop_ops.py scroll --amount N [--x X --y Y]
$PY scripts/desktop_ops.py type --text "text"
$PY scripts/desktop_ops.py insert-newline [--count N]
$PY scripts/desktop_ops.py press --key KEY
$PY scripts/desktop_ops.py hotkey --keys cmd c
$PY scripts/desktop_ops.py drag --x1 X1 --y1 Y1 --x2 X2 --y2 Y2

# Targeting — these return EXACT PIXEL COORDINATES for clicking
$PY scripts/target_resolver.py --app "App" --text "text" --python $PY
$PY scripts/ocr_text.py --app "App" --python $PY [--region-label LABEL]
$PY scripts/accessibility_provider.py --app "App" --text "text"
$PY scripts/accessibility_provider.py --app "App" --elements    # full UI tree
$PY scripts/ax_provider.py --app "App" --text "text"            # macOS raw AX backend
$PY scripts/vision_ocr.py --image /path/to/img.png

# Task context
$PY scripts/task_context.py init --task-id "my-task"
$PY scripts/cleanup_task.py --task-id "my-task"

# Window regions
$PY scripts/window_regions.py --window-x X --window-y Y --window-width W --window-height H [--label LABEL]
```

---

## 12. On-demand Deep References

| Need | File to read |
|------|-------------|
| Full skill manual | `Read skill/SKILL.md` |
| Core task lifecycle (macro-level) | `Read skill/references/workflow.md` |
| macOS platform specifics | `Read skill/references/platform-macos.md` |
| Windows platform specifics | `Read skill/references/platform-windows.md` |
| Linux platform specifics | `Read skill/references/platform-linux.md` |
| Precise targeting troubleshooting | `Read skill/references/precise-targeting.md` |
| Target provider ordering & fallback | `Read skill/references/target-providers.md` |
| Chat app rules (WeChat, Slack, etc.) | `Read skill/references/chat-app-macos.md` |
| WeChat-specific reference | `Read skill/references/app-wechat-desktop.md` |
| Validation patterns (send/delete safety) | `Read skill/references/validation-patterns.md` |
| Reusable operation patterns | `Read skill/references/operation-patterns.md` |
| Coordinate reconstruction from screenshots | `Read skill/references/coordinate-reconstruction.md` |
| Multi-agent collaboration rules | `Read skill/references/collaboration-rules.md` |
| Custom workflows | `Read skill/references/custom-workflows.md` |
| Cleanup rules (mandatory) | `Read skill/references/cleanup-rules.md` |
| Reproducible cross-host setup | `Read skill/references/reproducible-setup.md` |
| Precision targeting gap analysis | `Read skill/references/market-precision-targeting-gap-analysis.md` |
| Evaluation scenarios | `Read skill/references/eval-scenarios.md` |
| Example cases (repeatable) | `Read skill/references/example-cases.md` |
| App name patterns (Windows/macOS) | `Read skill/references/app-names.md` |
