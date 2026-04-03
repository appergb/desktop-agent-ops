# Target Providers

This file defines the contract for different targeting strategies.

## Goal

Allow the system to choose among multiple targeting providers and fall back safely.

## Provider order (v1.2.0)

Default order for high confidence:

1. **Accessibility provider** (macOS AXUIElement) — fastest, structured data, no screenshot
2. **System OCR provider** (macOS Vision Framework) — fast, accurate CJK, no external deps
3. **Tesseract OCR provider** — cross-platform fallback
4. **Template / image match provider** — icon matching
5. **Heuristic region provider** — geometry-based last resort

## Three-layer auto-degradation

`target_resolver.py` implements smart fallback:

1. Try Accessibility API → if `element_count >= 10` and matches found → return immediately
2. If `element_count < 10` (app hides UI, e.g. WeChat/QQ) → fall through to OCR
3. OCR auto-selects backend: Vision (macOS) → Tesseract (Linux/Windows)
4. If OCR finds nothing → template match → heuristic

The agent does NOT need to choose providers manually. `target_resolver.py` handles the entire chain.

## Provider contract

Each provider should output:

- target type
- confidence score
- bounding box (absolute)
- one or more candidate click points
- validation hints

## Implemented scripts

| Script | Provider | Platform | Speed |
|--------|----------|----------|-------|
| `ax_provider.py` | Accessibility (AXUIElement) | macOS | ~34ms |
| `vision_ocr.py` | Vision Framework OCR | macOS | ~147ms (fast) / ~686ms (accurate) |
| `ocr_text.py` | Multi-backend OCR | All | auto-selects best backend |
| `template_match.py` | Image matching | All | depends on image size |
| `target_resolver.py` | Orchestrator | All | runs providers in order |

## App compatibility

| App type | Best provider | Notes |
|----------|--------------|-------|
| Native macOS (Finder, Safari, Notes) | Accessibility | Full UI tree, ~122 elements |
| Java/Swing (IntelliJ IDEA) | Accessibility | Good coverage via Java Accessibility |
| WeChat, QQ | Vision OCR | Accessibility returns < 10 elements |
| Electron (VS Code, Claude) | Vision OCR | Minimal Accessibility tree |
| Linux GTK/Qt apps | Tesseract | AT-SPI planned for future |
| Windows native/WPF | Tesseract | UI Automation planned for future |

## Notes

- Accessibility requires macOS Accessibility permission (System Settings > Privacy & Security)
- Vision OCR requires no extra permissions beyond Screen Recording
- Tesseract remains available as `--backend tesseract` override
- The `source` field in results indicates which provider found the target
