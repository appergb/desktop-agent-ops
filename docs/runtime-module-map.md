# Runtime Module Map

This file records the current runtime structure after the window kernel refactor.

## Primary entrypoints

- `skill/scripts/desktop_ops.py`
  Purpose: CLI entrypoint for screenshots, window focus, bounds, mouse, keyboard, and clipboard actions.
- `skill/scripts/target_resolver.py`
  Purpose: Orchestrates accessibility, OCR, template, and heuristic targeting.
- `skill/scripts/workflow_runner.py`
  Purpose: Executes bundled or user workflows against the runtime CLI.
- `skill/scripts/first_run_setup.py`
  Purpose: Host setup, dependency install, permissions, and readiness checks.
- `skill/scripts/local_agent.py`
  Purpose: Local LLM executor that calls the desktop runtime tools.

## Window runtime

- `skill/scripts/window_kernel.py`
  Purpose: Shared restore lifecycle: probe -> activate -> restore -> raise -> verify -> optional reopen.
- `skill/scripts/window_backends.py`
  Purpose: Platform backends for macOS, Windows, and Linux window control.
- `skill/scripts/desktop_ops.py`
  Purpose: Keeps the public CLI stable while delegating domain logic into focused runtime modules.
- `skill/scripts/input_runtime.py`
  Purpose: Pure key normalization, AppleScript escaping, and text classification helpers for keyboard and typing commands.
- `skill/scripts/pointer_runtime.py`
  Purpose: Pointer movement, clicking, dragging, and scrolling with platform-aware backend selection.
- `skill/scripts/screen_runtime.py`
  Purpose: Screenshot capture, cursor readback, screen size, and pixel-color sampling.
- `skill/scripts/text_runtime.py`
  Purpose: Key press, clipboard paste, typing, newline insertion, and hotkey dispatch.
- `skill/scripts/runtime_support.py`
  Purpose: Shared structured runtime error type used by the domain runtime modules.

## Targeting runtime

- `skill/scripts/accessibility_provider.py`
  Purpose: Unified accessibility entrypoint for AX, UIA, and AT-SPI.
- `skill/scripts/ax_provider.py`
  Purpose: macOS AX backend.
- `skill/scripts/windows_uia_provider.py`
  Purpose: Windows UI Automation backend.
- `skill/scripts/linux_atspi_provider.py`
  Purpose: Linux AT-SPI backend.
- `skill/scripts/ocr_text.py`
  Purpose: OCR runtime and backend selection.
- `skill/scripts/vision_ocr.py`
  Purpose: Vision OCR backend for macOS.
- `skill/scripts/template_match.py`
  Purpose: Template matching fallback.
- `skill/scripts/window_regions.py`
  Purpose: Semantic regions relative to the current window.
- `skill/scripts/target_report.py`
  Purpose: Region + candidate reporting around resolved targets.
- `skill/scripts/target_runtime.py`
  Purpose: Pure text matching, OCR box merging, and candidate ranking helpers shared by the provider chain and resolver.
- `skill/scripts/targeting.py`
  Purpose: Geometry helper CLI kept for tests and documentation compatibility.

## Workflow runtime

- `skill/scripts/workflow_loader.py`
  Purpose: Parse workflow markdown, metadata, and step definitions.
- `skill/scripts/workflow_runner.py`
  Purpose: CLI entrypoint for listing, validating, previewing, and running workflows.
- `skill/scripts/workflow_runtime.py`
  Purpose: Pure parameter parsing, default application, result flattening, and variable substitution.
- `skill/scripts/workflow_executor.py`
  Purpose: Step execution, retry, subprocess wiring, and task directory lifecycle integration.
- `skill/scripts/task_context.py`
  Purpose: Task directory lifecycle and state capture.
- `skill/scripts/cleanup_task.py`
  Purpose: Cleanup for task artifacts after completion or failure.

## Diagnostics and setup

- `skill/scripts/platform_probe.py`
  Purpose: Platform capability and dependency probe.
- `skill/scripts/permission_bootstrap.py`
  Purpose: Initial permission prompting and smoke actions.
- `skill/scripts/doctor.py`
  Purpose: Health check and dependency diagnosis.
- `skill/scripts/smoke_test.py`
  Purpose: Runtime smoke verification.
- `skill/scripts/resolve_python.py`
  Purpose: Resolve interpreter path for packaged/runtime environments.

## Agent and orchestration helpers

- `skill/scripts/local_agent.py`
  Purpose: Tool-driven local agent loop.
- `skill/scripts/dispatch_agent.py`
  Purpose: Higher-level orchestration over the local agent.

## Removed as dead weight

- `skill/scripts/bootstrap_env.py`
  Reason: Legacy venv bootstrap path superseded by `first_run_setup.py`.
- `outputs/`
  Reason: Release artifacts removed so the repository has a single runtime source of truth during refactor work.
