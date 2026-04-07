#!/usr/bin/env python3
"""
target_resolver.py — Hybrid target resolver with four-layer fallback.

Targeting priority:
  1. Accessibility API (macOS AX / Windows UIA / Linux AT-SPI) — fastest, structured, no screenshot
  2. System OCR (Vision on macOS) / Tesseract OCR — cross-platform fallback
  3. Template matching — image-based icon matching
  4. Heuristic region — geometry-based last resort

Auto-degrades: if accessibility returns < 10 elements, falls through to OCR.

Usage:
    $PY target_resolver.py --app "WeChat" --text "发送" --python $PY
    $PY target_resolver.py --app "Finder" --text "Downloads" --python $PY
"""
import argparse
import json
from pathlib import Path

from target_provider_chain import (
    accessibility_provider,
    heuristic_provider,
    ocr_provider,
    run_json,
    run_provider_chain,
    template_provider,
)
from target_runtime import choose_best

ROOT = Path(__file__).resolve().parent


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))




def main():
    ap = argparse.ArgumentParser(
        description="Hybrid target resolver with four-layer fallback: "
                    "Accessibility → OCR → Template → Heuristic."
    )
    ap.add_argument("--app", required=True,
                     help="Target app name. Resolver will focus this app and search within its window.")
    ap.add_argument("--label")
    ap.add_argument("--text")
    ap.add_argument("--template")
    ap.add_argument("--providers",
                     default="accessibility,ocr_text,template_match,heuristic_region",
                     help="Comma-separated provider priority order. "
                          "Accessibility is first by default for best speed and accuracy.")
    ap.add_argument("--python", default="python3")
    ap.add_argument("--ocr-min-conf", type=float, default=40.0)
    ap.add_argument("--text-match", choices=["contains", "exact", "regex"], default="contains")
    ap.add_argument("--template-threshold", type=float, default=0.8)
    ap.add_argument("--template-max-matches", type=int, default=3)
    ap.add_argument("--region-label")
    args = ap.parse_args()

    desktop_ops = ROOT / "desktop_ops.py"

    # Step 1: Focus the target app
    try:
        run_json([args.python, str(desktop_ops), "focus-app", "--name", args.app])
    except Exception:
        pass

    # Step 2: Get window bounds
    window_bounds = None
    try:
        window_bounds = run_json([args.python, str(desktop_ops),
                                  "front-window-bounds", "--app", args.app])
    except Exception:
        pass

    # Step 3: Run providers in priority order with smart fallback
    results = run_provider_chain(args, ROOT)

    # Step 4: Pick best candidate and verify within window
    best = choose_best(results)
    found = best is not None
    if best and window_bounds and window_bounds.get("ok") is True:
        wx = window_bounds.get("x", 0)
        wy = window_bounds.get("y", 0)
        ww = window_bounds.get("width", 0)
        wh = window_bounds.get("height", 0)
        bx, by = best.get("x", 0), best.get("y", 0)
        best["within_window"] = (wx <= bx <= wx + ww) and (wy <= by <= wy + wh)

    jprint({
        "ok": found,
        "app": args.app,
        "window_bounds": window_bounds,
        "providers": results,
        "best_candidate": best,
    })


if __name__ == "__main__":
    main()
