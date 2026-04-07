# Target Providers

This file defines the contract for different targeting strategies.

## Goal

Allow the system to choose among multiple targeting providers and fall back safely.

## Provider order (v1.3.0)

Default order for high confidence. **Accessibility is strongly preferred for token efficiency.**

| # | Provider | Token cost | Speed | Screenshot needed? |
|---|----------|------------|-------|-------------------|
| 1 | **Accessibility API** (`accessibility_provider.py`) | **~200 tokens** (JSON) | ~34ms to ~200ms | **No** |
| 2 | System OCR (macOS Vision Framework) | ~30,000-60,000 tokens | ~147ms | Yes |
| 3 | Tesseract OCR | ~30,000-60,000 tokens | slower | Yes |
| 4 | Template / image match | ~30,000-60,000 tokens | varies | Yes |
| 5 | Heuristic region | ~500 tokens (JSON) | instant | No |

**Key insight**: Accessibility APIs return structured UI element data as pure JSON text. No screenshot is captured, no image is sent to the model. This saves 99%+ of the token cost compared to OCR-based targeting. Always prefer the platform accessibility tree when the app supports it.

## Three-layer auto-degradation

`target_resolver.py` implements smart fallback:

1. Try Accessibility API (macOS AX, Windows UIA, Linux AT-SPI) → if `element_count >= 10` and matches found → return immediately
2. If `element_count < 10` or the platform reports an accessibility blocker (UIPI, missing AT-SPI session, etc.) → fall through to OCR
3. OCR auto-selects backend: Vision (macOS) → Tesseract (Linux/Windows or blocked accessibility)
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
| `accessibility_provider.py` | Unified accessibility entry | macOS / Windows / Linux | fast |
| `ax_provider.py` | Accessibility (AXUIElement) | macOS | ~34ms |
| `windows_uia_provider.py` | Accessibility (UI Automation) | Windows | fast |
| `linux_atspi_provider.py` | Accessibility (AT-SPI) | Linux | fast |
| `vision_ocr.py` | Vision Framework OCR | macOS | ~147ms (fast) / ~686ms (accurate) |
| `ocr_text.py` | Multi-backend OCR | All | auto-selects best backend |
| `template_match.py` | Image matching | All | depends on image size |
| `target_resolver.py` | Orchestrator | All | runs providers in order |

## App compatibility

| App type | Best provider | Notes |
|----------|--------------|-------|
| Native macOS (Finder, Safari, Notes) | Accessibility | Full AX tree, usually high coverage |
| Native Windows / WPF / Win32 | Accessibility | UIA works well when privileges match |
| GNOME GTK apps | Accessibility | AT-SPI works when session bus and `pyatspi` are available |
| Java/Swing (IntelliJ IDEA) | Accessibility | Usually good coverage via accessibility bridge |
| WeChat, QQ | Vision OCR / Tesseract | Accessibility often returns a sparse tree |
| Electron (VS Code, Claude) | OCR | Accessibility tree may be minimal or unstable |
| Non-GNOME Linux or restricted Wayland sessions | OCR | AT-SPI may be unavailable, so resolver falls back |

## When to use accessibility directly vs target_resolver

For **known accessibility-friendly apps**, calling `accessibility_provider.py` directly is faster and cheaper than `target_resolver.py`:

```bash
# Direct accessibility lookup — no screenshot, structured coordinates
$PY scripts/accessibility_provider.py --app "Finder" --text "Downloads"

# Inspect full UI tree — understand app structure with zero image tokens
$PY scripts/accessibility_provider.py --app "Safari" --elements
```

Use `target_resolver.py` when:
- You don't know if the app exposes a usable accessibility tree (it auto-detects and falls back)
- The app is known to be accessibility-degraded (WeChat, QQ, Electron apps)
- You need template matching or heuristic fallback

Use `ax_provider.py` directly only when you are on macOS and specifically need raw AX details.

## Notes

- Accessibility requires macOS Accessibility permission (System Settings > Privacy & Security)
- Windows UI Automation works best when the agent and the target app run at the same privilege level; UIPI can block elevated or system windows
- Linux AT-SPI is first-class for GNOME sessions with `pyatspi`; if the session bus or bindings are unavailable, fall back to OCR
- Vision OCR requires no extra permissions beyond Screen Recording
- Tesseract remains available as `--backend tesseract` override
- The `source` field in results indicates which provider found the target
