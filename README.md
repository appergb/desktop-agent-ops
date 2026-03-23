# Desktop Agent Ops

Cross-platform desktop GUI automation skill for AI agents. Enables agents to observe screens, focus apps, click buttons, type text, and verify actions — all through a structured, window-scoped pipeline.

## Features

- **One-command setup**: `first_run_setup.py` auto-installs all dependencies, OCR language packs, and requests OS permissions
- **Window-scoped OCR targeting**: Never clicks the wrong app — all OCR is scoped to the target window
- **DPI-aware**: Auto-detects Retina/HiDPI scaling on macOS, Windows, and Linux
- **Multi-language OCR**: Auto-detects system language and installs matching Tesseract packs (Chinese, Japanese, Korean, etc.)
- **CJK text input**: Clipboard-paste fallback for reliable Unicode input on all platforms
- **17 desktop operations**: screenshot, click, type, scroll, drag, hotkey, focus-app, and more

## Supported Platforms

| Platform | Screenshot | Mouse/Keyboard | Window Management | OCR |
|----------|-----------|----------------|-------------------|-----|
| macOS | screencapture | cliclick + pyautogui | AppleScript | pytesseract |
| Windows | pyautogui | pyautogui | pygetwindow | pytesseract |
| Linux (X11) | pyautogui/scrot | pyautogui | xdotool + wmctrl | pytesseract |

## Quick Start

### As a Codex/Claude Skill

1. Copy the `SKILL.md`, `scripts/`, and `references/` directories to your skill location
2. The agent will auto-run `first_run_setup.py` on first use
3. Everything is installed automatically — no manual setup needed

### Manual Setup

```bash
# Run the one-command setup
python3 scripts/first_run_setup.py

# Check readiness
python3 scripts/first_run_setup.py --check
```

### Basic Usage

```bash
PY=/path/to/venv/bin/python  # from setup output

# Screenshot
$PY scripts/desktop_ops.py screenshot --output screen.png

# Focus an app
$PY scripts/desktop_ops.py focus-app --name "WeChat"

# Find text by OCR (window-scoped)
$PY scripts/target_resolver.py --app "WeChat" --text "发送" --python $PY

# Click at coordinates
$PY scripts/desktop_ops.py click --x 500 --y 300

# Type text (CJK supported)
$PY scripts/desktop_ops.py type --text "你好世界"

# Scroll within a window
$PY scripts/desktop_ops.py scroll --amount -5 --x 500 --y 400
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   SKILL.md                       │
│          (Agent operating manual)                │
├─────────────────────────────────────────────────┤
│              target_resolver.py                  │
│    (OCR-first hybrid targeting pipeline)         │
│    ocr_text.py → template_match.py → heuristic  │
├─────────────────────────────────────────────────┤
│              desktop_ops.py                      │
│    (17 cross-platform desktop operations)        │
│    cliclick / pyautogui / AppleScript / xdotool  │
├─────────────────────────────────────────────────┤
│            first_run_setup.py                    │
│    (Auto: deps → OCR langs → venv → perms)      │
└─────────────────────────────────────────────────┘
```

## Targeting Pipeline

The skill uses a 6-step window-scoped targeting pipeline to prevent clicking the wrong app:

1. **Focus** the target app → ensures it's frontmost
2. **Get window bounds** → knows exact position on screen
3. **Capture** only that window region
4. **OCR** within the window → finds text with coordinates
5. **Verify** the target before clicking
6. **Click** only if verified

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `first_run_setup.py` | One-command auto-setup (deps + OCR langs + venv + permissions + smoke test) |
| `desktop_ops.py` | Core operations: screenshot, click, type, scroll, focus, move, hotkey, etc. |
| `target_resolver.py` | OCR-first hybrid element targeting within app windows |
| `ocr_text.py` | Multi-language OCR with DPI scaling and auto-language detection |
| `permission_bootstrap.py` | OS permission requests with platform-specific guidance |
| `click_and_verify.py` | Safe click pipeline with pre/post screenshot verification |
| `window_regions.py` | Semantic regions (sidebar, toolbar, input area, etc.) |
| `target_report.py` | Structured targeting reports with candidate points |
| `region_diff.py` | Before/after image diff for action verification |
| `template_match.py` | OpenCV template matching for icon-based targeting |
| `smoke_test.py` | Full system readiness verification |
| `doctor.py` | Dependency and permission health check |
| `task_context.py` | Per-task state management |
| `cleanup_task.py` | Task temp directory cleanup |
| `platform_probe.py` | OS and display server detection |

## Auto-Setup Details

`first_run_setup.py` handles everything in one command:

| Stage | What it does |
|-------|-------------|
| Platform | Detects macOS / Windows / Linux (+ X11 vs Wayland) |
| System deps | macOS: `brew install cliclick tesseract` |
| OCR languages | Auto-detects system locale → installs matching Tesseract packs |
| Python env | Creates venv via `uv` (or pip fallback), installs pillow, pyautogui, pytesseract, opencv-python, numpy |
| Permissions | macOS: triggers Screen Recording, Accessibility, Automation prompts |
| Smoke test | Verifies screenshot, mouse movement, and pixel reading |

## License

MIT
