# Coordinate Reconstruction

Use this file when accessibility and OCR are both unavailable and you must reconstruct a click target from other evidence.

## IMPORTANT: accessibility/OCR is always preferred

Before using coordinate reconstruction, try these first:
1. `accessibility_provider.py --app "AppName" --text "target"` → exact pixel coordinates
2. `target_resolver.py --app "AppName" --text "target"` → auto-fallback pipeline
3. `ocr_text.py --app "AppName"` → all text positions in window

**Only use this file’s techniques when all three return no results.**

**NEVER visually estimate click positions from screenshots.** Models confuse left/right and misjudge pixel distances. This is the #1 cause of click errors.

## Goal

Reconstruct a reliable click target from programmatic evidence:

- screen size values
- window bounds (from `front-window-bounds`)
- live mouse coordinates (from `mouse-position`)
- pixel color samples (from `pixel-color`)
- region geometry calculations

## Principle

Do not trust a guessed absolute coordinate until you verify it.

Preferred loop:

1. get window bounds from `front-window-bounds`
2. calculate target region geometrically (e.g., center of window, 90% down for input area)
3. sample the pixel color at the candidate point to check it’s the right UI element
4. move to the target point
5. read back the real mouse position
6. click only if the pointer landed where expected (offset ≤ 5px)
7. capture again and verify UI change

## Why this matters

Absolute coordinates alone are fragile because:

- the frontmost window can change
- window positions can move
- screen scaling can change perceived layout
- a control’s visible center may not be its true hit target
- **models misinterpret screenshot layouts** (left/right confusion, distance misjudgment)

## Practical commands

Use helper commands like:

- `screen-size`
- `screenshot`
- `capture-region`
- `mouse-position`
- `pixel-color --x ... --y ...`
- `move --x ... --y ...`
- `click --x ... --y ...`

## Reconstruction strategy

### 1. Global locate

Use a full screenshot to find the rough area of the app and the target control.

### 2. Region refine

Crop a smaller region around the target and reason there instead of on the full screen.

### 3. Pick an anchor point

Choose a point such as:

- center of a button
- center of a row
- center of an icon
- slightly inward from a visible border

### 4. Validate with move

Move first, then read back `mouse-position`.
If the pointer did not land where expected, stop and reassess.

### 5. Validate with UI change

A successful click must be verified by a fresh screenshot, not assumed from the command return.

## Future upgrades

Later, add OCR, text anchors, or UI detection. For MVP, coordinate reconstruction should still work with screenshot + region crop + move/readback + pixel sampling.

When OCR is available, prefer text anchors for buttons, tabs, and titles:

- run OCR on a cropped region
- match text to a query
- derive the click point from the matched text box

This reduces reliance on layout percentages when labels are visible.
