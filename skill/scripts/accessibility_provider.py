#!/usr/bin/env python3
"""Unified cross-platform accessibility provider entry point."""

import argparse
import json
import platform


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def _normalize_payload(result, platform_name, backend):
    payload = dict(result or {})
    payload.setdefault("platform", platform_name)
    payload.setdefault("backend", backend)
    payload.setdefault("matches", [])
    if payload.get("ok") and payload.get("elements") is None:
        payload["elements"] = []
    for match in payload.get("matches", []):
        match.setdefault("source", "accessibility")
        match.setdefault("confidence", 1.0)
    return payload


def _run_macos(app_name, text, text_match, max_depth):
    from ax_provider import run_ax_query
    return _normalize_payload(
        run_ax_query(app_name, text, text_match, max_depth),
        "macos",
        "ax",
    )


def _run_windows(app_name, text, text_match, max_depth):
    from windows_uia_provider import run_windows_uia_query
    return _normalize_payload(
        run_windows_uia_query(app_name, text, text_match, max_depth),
        "windows",
        "uia",
    )


def _run_linux(app_name, text, text_match, max_depth):
    from linux_atspi_provider import run_linux_atspi_query
    return _normalize_payload(
        run_linux_atspi_query(app_name, text, text_match, max_depth),
        "linux",
        "atspi",
    )


def run_accessibility_query(app_name, text=None, text_match="contains", max_depth=6):
    system = platform.system().lower()
    try:
        if system == "darwin":
            return _run_macos(app_name, text, text_match, max_depth)
        if system == "windows":
            return _run_windows(app_name, text, text_match, max_depth)
        if system == "linux":
            return _run_linux(app_name, text, text_match, max_depth)
    except Exception as e:
        return {
            "ok": False,
            "platform": system,
            "error": f"provider_error: {e}",
            "matches": [],
        }
    return {
        "ok": False,
        "platform": system,
        "error": f"unsupported_platform:{system}",
        "matches": [],
    }


def main():
    ap = argparse.ArgumentParser(description="Cross-platform accessibility provider")
    ap.add_argument("--app", required=True, help="Target app name")
    ap.add_argument("--text", help="Text to search for in UI elements")
    ap.add_argument("--text-match", choices=["contains", "exact", "regex"], default="contains")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--elements", action="store_true", help="Include verbose elements payload")
    args = ap.parse_args()

    try:
        result = run_accessibility_query(args.app, args.text, args.text_match, args.max_depth)
    except Exception as e:
        jprint({"ok": False, "error": f"unhandled_error: {e}", "matches": []})
        return
    if not args.elements and result.get("ok"):
        result.pop("elements", None)
    jprint(result)


if __name__ == "__main__":
    main()
