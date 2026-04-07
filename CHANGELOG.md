# Changelog

## v1.4.0 (2026-04-06)

### Bug Fixes — Comprehensive Audit & Hardening

- **desktop_ops.py** — 8 fixes
  - CRITICAL: Fixed `cmd_pixel_color` producing double JSON output (broken every call)
  - CRITICAL: Fixed Windows `paste_text` encoding raw text as PowerShell command (code injection + broken primary path)
  - Fixed all `run()` callers to catch `SystemExit` and return structured JSON errors instead of plain text
  - Fixed `focus-app` using substring match (`in`) — now uses exact match to prevent "Mail" matching "Airmail"
  - Fixed `_key_to_keycode` silently defaulting unknown keys to Return (keycode 36) — now raises JSON error
  - Fixed middle-click and multi-click falling through to `SystemExit` — now gracefully falls back to pyautogui
  - Fixed `paste_text` failing on multi-line text via AppleScript — now detects newlines and uses `pbcopy` directly
  - Fixed `drag` command raising `SystemExit` with plain text for non-left buttons

- **first_run_setup.py** — 4 fixes
  - Fixed missing `FileNotFoundError` handler in `stage_permissions` (crash risk)
  - Fixed `locale.getdefaultlocale()` deprecated since Python 3.11 — replaced with `locale.getlocale()`
  - Fixed `brew` variable not used in tesseract prefix lookup (bare "brew" could fail on non-standard PATH)
  - Updated docstring from "5 stages" to "6 stages" to match actual implementation

- **accessibility_provider.py** — 3 fixes
  - CRITICAL: Fixed unconditional cross-platform imports crashing on every platform (e.g. importing `pyatspi` on macOS)
  - Fixed double `_normalize_payload` wrapping (wasted computation, confusing intent)
  - Added exception handling around provider calls in CLI entry point
  - Added `confidence: 1.0` default to accessibility matches for consistent scoring in `choose_best()`

- **target_resolver.py** — 7 fixes
  - Fixed `heuristic_region` branch missing `break`/`continue` — silently fell through to `unknown_provider`
  - Added try/except around all provider subprocess calls — prevent cascade crash on Tesseract/template errors
  - Fixed window bounds check truthy for missing `ok` key and using 99999 fallback defaults
  - Fixed `ok: true` always emitted even when no target found — now `ok` reflects whether best_candidate exists
  - Removed dead code: redundant `len(q) == 1` branch in `match_text`
  - Fixed `heuristic_provider` using bare `[]` indexing on potentially missing `region.absolute` keys
  - Fixed CJK merge producing overlapping duplicate matches — now tracks consumed indices
  - Updated docstring from "three-layer" to "four-layer"

- **ocr_text.py** — 2 fixes
  - Fixed `tempfile.mktemp` (deprecated, TOCTOU race) — replaced with `tempfile.mkstemp`
  - Added cleanup for DPI probe temporary files (previously leaked to `/tmp`)

- **vision_ocr.py** — 3 fixes
  - Fixed aggressive `zh-Hans` fallback for all non-detected locales — now only adds if system locale is Chinese
  - Replaced magic number `3` in `setRevision_` with named constant
  - Fixed `tempfile.mktemp` in `detect_dpi_scale` — replaced with `tempfile.mkstemp` + `finally` cleanup

- **workflow_loader.py** — 1 fix
  - Fixed f-string `${{pname}}` producing literal `${pname}` — parameter validation now correctly checks actual parameter names

- **workflow_runner.py** — 2 fixes
  - Fixed `$PY` plain `.replace()` corrupting longer variables like `$PYTHON_PATH` — now uses regex word-boundary matching
  - Fixed retry state corruption — `prev_result` is now copied before each attempt, only committed on success

- **click_and_verify.py** — 3 fixes
  - Fixed no bounds checking on `candidate_index` — `IndexError` crash with no JSON output
  - Fixed `tempfile.mktemp` — replaced with `tempfile.mkstemp`
  - Added cleanup of pre/post screenshot temp files

- **targeting.py** — 2 fixes
  - Fixed small elements (< 2×inset) producing inverted/wrong click coordinates — inset now clamped to half of element size
  - Fixed `SystemExit` with plain text breaking JSON error protocol — now outputs structured JSON error

### Documentation

- Updated "three-layer" references to "four-layer" across SKILL.md
- Fixed "8-step closed loop" → "Core task lifecycle (macro-level)" to distinguish from per-click 7-step loop
- Clarified `--min-conf` (ocr_text.py) vs `--ocr-min-conf` (target_resolver.py) in failure recovery sections
- Updated test fixtures for new accessibility provider behavior

## v1.3.0 (2026-04-04)

### Features

- **AX-First Execution Flow** — Accessibility API is now the primary targeting method
  - `ax_provider.py` returns structured JSON (~200 tokens) vs screenshots (~30,000-60,000 tokens)
  - Core loop changed: Focus → AX query → (fallback to screenshot+OCR) → Verify → Act
  - New Hard Rule #2: "AX before screenshot"
  - Token cost comparison added to targeting pipeline docs

- **Standard Claude Code Skill Entry File** — `desktop-agent-ops.md`
  - Proper frontmatter: name, description, whenToUse, effort, tools, disallowedTools
  - Concise 200-line quick operations manual
  - On-demand deep reference loading via `Read skill/SKILL.md`

- **Enhanced Task State Management** — `task_context.py`
  - New fields: step_count, current_step_retries, max_retries, total_actions, error_log
  - New CLI subcommands: `step`, `retry`, `finalize`, `record-error`
  - `cleanup_task.py` now archives `summary.json` to `~/.openclaw-desktop-agent-ops/task-history/`

- **Workflow Step Enhancements** — `workflow_runner.py`
  - `$STEP_N_field` syntax for cross-step variable references
  - Per-step timeout (workflow-level and step-level `timeout` field)

- **Wayland Support Improvements** — `platform_probe.py`
  - Outputs `limitations` and `workarounds` when Wayland session detected
  - Checks for `ydotool` availability

### Changes

- `SKILL.md` reduced from 610 to ~360 lines (-43%), repositioned as detailed reference manual
- Three-layer documentation: entry file → SKILL.md (core rules) → references/ (deep docs)
- Hard Rules expanded from 14 to 16 (added AX-first and screenshot management rules)
- `target-providers.md` updated with token cost comparison table

## v1.2.2 (2026-04-04)

### Bug Fixes

- **`doctor.py`**: wrapped top-level execution in `if __name__ == "__main__"` guard — importing
  the module no longer triggers live system checks (screenshot, mouse move, subprocess calls)
- **`platform_probe.py`**: same guard added — importing no longer executes platform detection
  and prints JSON as a side effect
- **`SKILL.md` CLI Reference**: documented three previously undocumented scripts:
  - `platform_probe.py` — platform detection, returns `{ok, platform, linux_session}`
  - `target_report.py` — region candidate points, called internally by `target_resolver.py`
    and `click_and_verify.py`
  - `doctor.py` — health diagnostics for post-setup failures

## v1.2.1 (2026-04-03)

### Features

- **Tool Priority Decision Flow** — SKILL.md entry point now enforces MCP/API-first
  - Priority 1: MCP Servers (chrome-devtools, fetch, etc.)
  - Priority 2: Native CLI / AppleScript
  - Priority 3: Desktop Agent Ops (screen recognition as last resort)
  - Decision checklist and scope exclusions added

- **Three-Layer Smart Targeting** — Accessibility API → Vision OCR → Tesseract
  - `ax_provider.py`: macOS AXUIElement, ~34ms, 100% accuracy
  - `vision_ocr.py`: macOS Vision Framework, ~147ms, no Tesseract needed
  - Auto-degradation for apps hiding UI (WeChat, QQ)

### Changes

- `target_resolver.py`: default providers now `accessibility,ocr_text,template_match,heuristic_region`
- `ocr_text.py`: multi-backend with `--backend auto|vision|tesseract`
- `first_run_setup.py`: macOS installs pyobjc; Tesseract optional on macOS
- Hard Rule #1: "MCP/API first — never use screen recognition when a structured tool can do the job"

## v1.2.0 (2026-04-03)

### New Features

- **Tool Priority System** — SKILL.md now enforces MCP/API-first decision flow
  - Priority 1: MCP Servers (chrome-devtools, fetch, etc.) — always prefer structured APIs
  - Priority 2: Native CLI / AppleScript — direct control without screen parsing
  - Priority 3: Desktop Agent Ops — only when no structured tool can do the job
  - Decision checklist added to skill entry point
  - Hard Rule #1 updated: "MCP/API first: never use screen recognition when a structured tool can do the job"

- **Three-Layer Smart Targeting** — `target_resolver.py` now uses Accessibility API → System OCR → Tesseract fallback chain
  - Layer 1: macOS Accessibility API (`ax_provider.py`) — queries UI element tree directly, ~34ms, 100% text accuracy
  - Layer 2: macOS Vision Framework OCR (`vision_ocr.py`) — built-in OCR, ~147ms, no Tesseract needed
  - Layer 3: Tesseract OCR — cross-platform fallback (now optional on macOS)
  - Auto-degrades: if Accessibility returns < 10 elements (WeChat, QQ), falls through to OCR

- **macOS Accessibility Provider** (`ax_provider.py`)
  - Uses PyObjC AXUIElement to walk app UI trees
  - Returns structured {role, title, description, value, position, size} for each element
  - 65x faster than Tesseract OCR for native apps (Finder, Safari, Notes, etc.)

- **macOS Vision Framework OCR** (`vision_ocr.py`)
  - Apple's built-in OCR engine, no external binary needed
  - Native CJK support — no character splitting (eliminates `_merge_adjacent_boxes` workaround)
  - 15x faster than Tesseract, better accuracy
  - Two modes: fast (~147ms) and accurate (~686ms)

### Changes

- **`ocr_text.py` multi-backend** — auto-selects Vision (macOS) or Tesseract (Linux/Windows)
  - New `--backend auto|vision|tesseract` flag
  - Backward compatible: existing calls work unchanged
- **`first_run_setup.py`** — platform-specific dependency installation
  - macOS: installs pyobjc frameworks (Accessibility + Vision + Quartz)
  - Tesseract is now optional on macOS (kept as fallback)
  - `brew install tesseract` removed from mandatory install on macOS
- **`target_resolver.py`** — default provider order changed to `accessibility,ocr_text,template_match,heuristic_region`
- **SKILL.md** — updated targeting pipeline docs, CLI reference for new scripts

## v1.1.0 (2026-04-02)

### New Features

- **Custom Workflow System** — Define reusable multi-step desktop automations in Markdown + YAML frontmatter
  - `workflow_loader.py`: Discover and parse workflows from bundled and user directories
  - `workflow_runner.py`: Execute workflows with parameter substitution, retry logic, and task context
  - `preview` command for Agent safety review before execution (no hardcoded whitelist)
  - 3 bundled example workflows: send-chat-message, browser-search, open-app-and-click

- **Secret Scanner** — Pre-upload security scanning (`secret_scanner.py`)
  - 13 regex patterns: AWS keys, GitHub tokens, API keys, private keys, connection strings, etc.
  - Shannon entropy detection for unknown secret formats
  - Severity levels: `error` (blocks upload) / `warning` (skippable with --force)

- **Workflow Sharing** — Contribute workflows to community via GitHub PR (`workflow_share.py`)
  - Automated preflight: format validation + secret scan + gh auth check
  - One-command fork → branch → commit → PR creation
  - PR body auto-generated with workflow metadata and scan results

### Fixes

- **OCR ambiguity guard** — Example 3 send-button lookup now uses `--region-label primary_action` to prevent false-positive when message text contains "发送"
- **Removed vague "OR" fallback** — Input field targeting no longer offers "click at bottom center" as alternative; `window_regions.py --label bottom_input` is now mandatory
- **Reference doc trigger rules** — Changed from "Load as needed" to explicit **MUST-read** conditions for platform, chat-app, WeChat, validation, and targeting docs
- Added post-type screenshot verification step in Example 3

### Documentation

- Added `skill/references/custom-workflows.md` workflow authoring guide
- Updated `SKILL.md` with Custom Workflows section and Agent Safety Review Protocol
- Updated README with workflow system documentation

## v1.0.3 (2026-03-25)

### Performance (7.6x faster end-to-end)
- `cmd_type`: clipboard paste is now the primary path; cliclick `t:` silently dropped CJK characters
- `paste_text` macOS: merged pbcopy + Cmd+V into a single osascript call (saves one subprocess)
- `paste_text` Windows: use PowerShell `Set-Clipboard` for faster Unicode handling
- `cmd_focus_app`: fast path skips Dock traversal when app is already frontmost
- `cmd_focus_app`: reduced AppleScript delays from 0.3s to 0.15s; verification delay from 0.3s to 0.1s
- Benchmarks (macOS, WeChat already frontmost): focus 0.29s + type 0.17s + send 0.13s = **0.59s total** (was 4.49s)

### Bug Fixes
- Fixed minimized window restoration on macOS — `focus-app` now clicks dock icon to restore minimized windows (previously only handled hidden apps)
- Fixed `cmd_type` dropping CJK text — cliclick was first choice but silently skips non-ASCII; now clipboard paste is always first
- Fixed `cmd_press` on macOS — AppleScript `key code` is now the primary path; cliclick `kp:return` was not recognized by WeChat
- Fixed `cmd_hotkey` on macOS — cliclick `kp:` only accepts special keys; letter keys (a, c, v) now use `t:` so `cmd+a`, `cmd+c` etc. work correctly
- Fixed `cmd_scroll` horizontal direction executing twice (once in try/except, once unconditionally)
- Fixed `cmd_screenshot` file descriptor leak from `mkstemp` (fd was never closed)
- Fixed `cmd_pixel_color` using deprecated `tempfile.mktemp` (replaced with safe `mkstemp`)
- Fixed `cmd_front_window_bounds` crashing when window title contains `|` character (now uses `rsplit`)
- Fixed `cmd_insert_newline` not catching `SystemExit` — now properly outputs JSON error via `jerror`
- Fixed `cmd_drag` cliclick path ignoring `--duration` parameter (now inserts `w:` wait command)
- Added missing `find_running_app` function (2 tests were failing)
- Moved `import time` to module top level (was late-imported in function body)

### Documentation
- Added 8 new example cases (Case 12–19): right-click, drag-and-drop, system settings, form filling, dropdown, toggle/slider, cross-app copy-paste, browser tab management
- Added 8 matching reusable operation patterns
- Updated README.md platform table, SKILL.md backend priority table, platform-macos.md, platform-windows.md

## v1.0.1-urgent (2026-03-24)

### Urgent Fixes
- separated literal line breaks from send actions in `desktop_ops.py`
- added `insert-newline` so multi-line messages no longer depend on send-key behavior
- normalized Enter-like send keys so `press --key return` always maps to a real key press path
- documented that WeChat and similar direct-Enter chat apps should send via `press --key return`, not via `type --text` with `\n`
- documented that Windows WeChat should prefer the visible `发送` button instead of relying on Enter-to-send when the button is available

### Packaging
- prepared an urgent pure-skill ZIP package using the same base version with an `-urgent` suffix

## v1.0.1 (2026-03-24)

### Packaging & Release
- Added `skill/agents/openai.yaml` so the packaged skill carries standard UI metadata
- Added a minimal GitHub Actions unit-test workflow to protect future releases
- Prepared a pure-skill package layout for direct installation from a release ZIP

### Bug Fixes
- Fixed task directory handling by centralizing `task_id` validation and safe path resolution in `task_paths.py`
- Fixed `task_context.py` and `cleanup_task.py` to reuse the same safe task path contract
- Fixed `desktop_ops.py` missing `escape_applescript_string()` and applied escaping to AppleScript interpolation points
- Fixed test imports so the suite resolves modules from `skill/scripts/`

### Documentation
- Unified repository-root command examples in `README.md`, `docs/README_zh.md`, and `docs/README_ja.md`
- Synced `skill/SKILL.md` with the full `references/` set and corrected example command paths

## v1.0.0 (2026-03-23)

### Features
- One-command auto-setup (`first_run_setup.py`) — installs all dependencies, OCR languages, Python venv, and OS permissions
- 17 cross-platform desktop operations via `desktop_ops.py`
- Window-scoped OCR targeting — prevents clicking elements in wrong apps
- OCR-first hybrid targeting pipeline (`target_resolver.py`)
- Auto DPI/HiDPI/Retina detection and coordinate scaling
- Multi-language OCR auto-detection (Chinese, Japanese, Korean, etc.)
- CJK text input via clipboard-paste fallback on all platforms
- Adjacent character merging for CJK OCR fragments
- Window-targeted scrolling with `--x --y` positioning
- AppleScript key/type fallback when cliclick fails on macOS

### Cross-Platform Support
- macOS: cliclick + screencapture + AppleScript + System Settings auto-open
- Windows: pyautogui + pygetwindow + clip.exe paste + locale.getdefaultlocale()
- Linux (X11): pyautogui + xdotool + wmctrl + xclip paste

### Bug Fixes
- Fixed `permission_bootstrap.py` falsely marking permissions as completed (checked return code instead of JSON ok field)
- Fixed `desktop_ops.py` `jerror()` exiting with code 0 on errors
- Fixed `capture-region` missing `--with-cursor` argument
- Fixed `task_context.py` hardcoded `/tmp` path (Windows incompatible)
- Fixed `click_and_verify.py` hardcoded `python3` command (Windows incompatible)
- Fixed `smoke_test.py` strict coordinate match failing on Retina displays
- Fixed System Settings fallback for different macOS versions
