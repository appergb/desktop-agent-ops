#!/usr/bin/env python3
"""
ax_provider.py — macOS Accessibility API provider.

Queries the UI element tree of a running app via AXUIElement (PyObjC).
Returns structured elements with role, title, position, and size —
no screenshot or OCR needed.

Usage:
    python3 ax_provider.py --app "Finder" [--text "搜索"] [--max-depth 6]

Output (JSON):
    {
      "ok": true,
      "app": "Finder",
      "pid": 1234,
      "element_count": 122,
      "elements": [ { "role", "title", "description", "value", "position", "size" } ],
      "matches": [ { "text", "role", "x", "y", "width", "height", "confidence": 1.0 } ]
    }

Falls back gracefully:
  - If pyobjc not installed → ok:false, error:"pyobjc_unavailable"
  - If AX permission denied → ok:false, error:"accessibility_not_trusted"
  - If app not found / too few elements → ok:true but element_count is low
"""
import argparse
import json
import platform
import re
import sys

def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def _check_platform():
    if platform.system().lower() != "darwin":
        return "macos_only"
    return None


def _import_ax():
    """Import pyobjc AX modules. Returns (modules_dict, error_string)."""
    try:
        import AppKit
        from ApplicationServices import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
            AXIsProcessTrusted,
        )
        return {
            "AppKit": AppKit,
            "AXUIElementCreateApplication": AXUIElementCreateApplication,
            "AXUIElementCopyAttributeValue": AXUIElementCopyAttributeValue,
            "AXIsProcessTrusted": AXIsProcessTrusted,
        }, None
    except ImportError:
        return None, "pyobjc_unavailable"


def _ax_get(element, attr, copy_fn):
    err, val = copy_fn(element, attr, None)
    if err != 0:
        return None
    return val


_POINT_RE = re.compile(r'x:([\d.]+)\s+y:([\d.]+)')
_SIZE_RE = re.compile(r'w:([\d.]+)\s+h:([\d.]+)')


def _parse_point(ax_value):
    if ax_value is None:
        return None
    m = _POINT_RE.search(str(ax_value))
    return (float(m.group(1)), float(m.group(2))) if m else None


def _parse_size(ax_value):
    if ax_value is None:
        return None
    m = _SIZE_RE.search(str(ax_value))
    return (float(m.group(1)), float(m.group(2))) if m else None


def walk_ax_tree(element, copy_fn, depth=0, max_depth=6):
    """Recursively walk AX tree, yielding element info dicts."""
    if depth > max_depth:
        return

    role = _ax_get(element, "AXRole", copy_fn)
    title = _ax_get(element, "AXTitle", copy_fn)
    desc = _ax_get(element, "AXDescription", copy_fn)
    value = _ax_get(element, "AXValue", copy_fn)
    pos_raw = _ax_get(element, "AXPosition", copy_fn)
    size_raw = _ax_get(element, "AXSize", copy_fn)

    position = _parse_point(pos_raw)
    size = _parse_size(size_raw)

    info = {
        "depth": depth,
        "role": str(role) if role else None,
        "title": str(title) if title else None,
        "description": str(desc) if desc else None,
        "value": str(value) if value and len(str(value)) < 500 else None,
    }
    if position:
        info["position"] = {"x": position[0], "y": position[1]}
    if size:
        info["size"] = {"w": size[0], "h": size[1]}

    yield info

    children = _ax_get(element, "AXChildren", copy_fn)
    if children:
        for child in children:
            yield from walk_ax_tree(child, copy_fn, depth + 1, max_depth)


def find_pid_by_name(app_name, AppKit):
    """Find a running app's PID by name (case-insensitive)."""
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        localized = app.localizedName()
        if localized and localized.lower() == app_name.lower():
            return app.processIdentifier(), localized
    # Also try bundle ID suffix match
    for app in workspace.runningApplications():
        bid = app.bundleIdentifier() or ""
        if bid.lower().endswith("." + app_name.lower()):
            return app.processIdentifier(), app.localizedName()
    return None, None


def match_elements(elements, query, match_mode="contains"):
    """Find elements whose text matches the query."""
    if not query:
        return []
    q = query.strip().lower()
    matches = []
    for el in elements:
        texts = [el.get("title"), el.get("description"), el.get("value")]
        for t in texts:
            if not t:
                continue
            t_lower = t.strip().lower()
            hit = False
            if match_mode == "exact":
                hit = t_lower == q
            elif match_mode == "regex":
                hit = bool(re.search(query, t, re.IGNORECASE))
            else:  # contains
                hit = q in t_lower
            if hit and el.get("position") and el.get("size"):
                pos = el["position"]
                sz = el["size"]
                matches.append({
                    "text": t,
                    "role": el.get("role"),
                    "x": int(pos["x"] + sz["w"] / 2),
                    "y": int(pos["y"] + sz["h"] / 2),
                    "width": int(sz["w"]),
                    "height": int(sz["h"]),
                    "confidence": 1.0,
                    "source": "accessibility",
                    "label": f"ax:{el.get('role', '')}:{t}",
                })
                break
    return matches


def run_ax_query(app_name, text=None, text_match="contains", max_depth=6):
    """Main entry point. Returns result dict."""
    platform_err = _check_platform()
    if platform_err:
        return {"ok": False, "error": platform_err}

    mods, import_err = _import_ax()
    if import_err:
        return {"ok": False, "error": import_err}

    if not mods["AXIsProcessTrusted"]():
        return {"ok": False, "error": "accessibility_not_trusted",
                "hint": "Enable in System Settings > Privacy & Security > Accessibility"}

    pid, resolved_name = find_pid_by_name(app_name, mods["AppKit"])
    if pid is None:
        return {"ok": False, "error": "app_not_found", "app": app_name}

    app_ref = mods["AXUIElementCreateApplication"](pid)
    copy_fn = mods["AXUIElementCopyAttributeValue"]

    elements = list(walk_ax_tree(app_ref, copy_fn, max_depth=max_depth))

    matches = []
    if text:
        matches = match_elements(elements, text, text_match)

    # Strip depth/internal fields for output
    clean_elements = []
    for el in elements:
        out = {}
        for k in ("role", "title", "description", "value", "position", "size"):
            if el.get(k) is not None:
                out[k] = el[k]
        if out:
            clean_elements.append(out)

    return {
        "ok": True,
        "app": resolved_name or app_name,
        "pid": pid,
        "element_count": len(clean_elements),
        "elements": clean_elements,
        "matches": matches,
    }


def main():
    ap = argparse.ArgumentParser(description="macOS Accessibility API provider")
    ap.add_argument("--app", required=True, help="Target app name")
    ap.add_argument("--text", help="Text to search for in UI elements")
    ap.add_argument("--text-match", choices=["contains", "exact", "regex"],
                     default="contains")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--elements", action="store_true",
                     help="Include full element list in output (verbose)")
    args = ap.parse_args()

    result = run_ax_query(args.app, args.text, args.text_match, args.max_depth)

    if not args.elements and result.get("ok"):
        result.pop("elements", None)

    jprint(result)


if __name__ == "__main__":
    main()
