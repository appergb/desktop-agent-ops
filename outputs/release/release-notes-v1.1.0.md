# Release Notes — v1.1.0 (2026-04-02)

## New Features

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

## Fixes

- **OCR ambiguity guard** — Example 3 send-button lookup now uses `--region-label primary_action` to prevent false-positive when message text contains "发送"
- **Removed vague "OR" fallback** — Input field targeting no longer offers "click at bottom center" as alternative; `window_regions.py --label bottom_input` is now mandatory
- **Reference doc trigger rules** — Changed from "Load as needed" to explicit **MUST-read** conditions for platform, chat-app, WeChat, validation, and targeting docs
- Added post-type screenshot verification step in Example 3

## Documentation

- Added `skill/references/custom-workflows.md` workflow authoring guide
- Updated `SKILL.md` with Custom Workflows section and Agent Safety Review Protocol
- Updated README with workflow system documentation

## Install

Download `desktop-agent-ops-v1.1.0.zip` and follow the setup instructions in SKILL.md.

SHA-256 checksum available in `desktop-agent-ops-v1.1.0.sha256`.
