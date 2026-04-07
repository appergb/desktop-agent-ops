# Workflow

## Goal

Provide a stable closed loop for desktop GUI work:

1. create or load task context
2. observe current screen state
3. decide the next smallest useful action
4. execute through helper script
5. verify with a fresh capture
6. continue or recover
7. cleanup when finished

## Standard loop

### 0. Bootstrap permissions (first run only)

Before the first real desktop action on a new host, run:

- `scripts/permission_bootstrap.py` (use `--open-settings` on macOS if prompts do not appear)

This will trigger OS permission prompts for Screen Recording, Accessibility, and Automation
where applicable. The user must approve those prompts manually.

### 1. Initialize task context

Use `scripts/task_context.py` to:

- create a task directory
- record start time
- store recent screenshot paths
- keep lightweight state only

If the previous task is finished and the new request is unrelated, start a new task context.

### 2. Probe platform

Run `scripts/platform_probe.py` and then follow the correct platform reference.

### 3. Observe before acting

Use `scripts/desktop_ops.py` to capture state before touching the UI.

Default order:

- first: full screenshot or frontmost app/window check
- second: app focus if needed
- third: obtain front-window bounds for the target app
- fourth: derive the target region relative to that window
- fifth: recapture target area

If the target has visible text or an icon, consider running `scripts/target_resolver.py`
before clicking so OCR or template matching can return a higher-confidence target.

### 4. Choose one small action

Examples:

- focus app
- move to a target before clicking when hit accuracy matters
- read screen size or pixel color to refine a target
- click one target
- type into one field
- press one hotkey
- capture a smaller region
- resolve a target using AX, OCR, or templates when labels are visible

**CRITICAL: Get click coordinates from accessibility/OCR, not from visual estimation.**

Models often confuse left/right or misjudge pixel distances when looking at screenshots.
ALWAYS use `accessibility_provider.py` or `target_resolver.py` to get exact pixel coordinates.
NEVER guess or estimate a click position by looking at a screenshot.

Avoid long preplanned action chains.

### 5. Execute through helper script — MANDATORY move→readback→click

**Before every click, follow this exact sequence:**

```
1. accessibility/OCR → get target {x, y} (NEVER estimate from screenshot)
2. front-window-bounds → get {wx, wy, ww, wh}
3. bounds-check: assert wx ≤ x ≤ wx+ww AND wy ≤ y ≤ wy+wh
4. move --x X --y Y (DO NOT CLICK)
5. mouse-position → read back {mx, my}
6. verify: |mx - x| ≤ 5 AND |my - y| ≤ 5  (if not → STOP)
7. click --x X --y Y
```

For destructive actions (send, delete, close, confirm), add between step 4 and 7:
```
screenshot --with-cursor → visually confirm cursor is over correct element
```

Actions should return JSON that the main agent can read back into context.

### 6. Verify immediately

After every meaningful action, capture again and check whether expected state changed.

**In multi-step tasks: re-locate targets before EVERY click.** Coordinates from step N are stale by step N+1. Windows move, dialogs appear, UI shifts after typing.

Examples:

- app became frontmost
- search results appeared
- text field now contains typed content
- chat window opened
- button click changed the screen

When the target region should change, compute a region diff to confirm the change.

### 7. Recover if needed

Use fallback in this order:

1. recapture current state
2. refocus app/window
3. search instead of browsing manually
4. reduce scope to a region capture
5. retry one step only
6. escalate only if clearly necessary

### 8. Cleanup at end

When task finishes, fails, or is cancelled, apply `references/cleanup-rules.md` and run `scripts/cleanup_task.py`.

## Operating principles

- Single-agent first
- Explicit platform branch
- Small steps, frequent verification
- Search before random scrolling when the UI supports search
- Cleanup is part of the task, not optional postwork
