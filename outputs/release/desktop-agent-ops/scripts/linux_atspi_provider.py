#!/usr/bin/env python3
"""Linux AT-SPI accessibility provider."""

import platform
import re


def _error(hint, error):
    return {
        "ok": False,
        "platform": "linux",
        "backend": "atspi",
        "error": error,
        "hint": hint,
        "matches": [],
    }


def _normalize_text(value):
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _match_text(value, query, mode):
    if not query:
        return False
    text = str(value or "")
    if not text:
        return False
    if mode == "regex":
        return re.search(query, text, flags=re.IGNORECASE) is not None
    normalized_text = _normalize_text(text)
    normalized_query = _normalize_text(query)
    if mode == "exact":
        return normalized_text == normalized_query
    return normalized_query in normalized_text


def _normalize_element(raw):
    x = int(raw.get("x", 0))
    y = int(raw.get("y", 0))
    width = int(raw.get("width", 0))
    height = int(raw.get("height", 0))
    element = {
        "role": raw.get("role"),
        "title": raw.get("name"),
        "description": raw.get("description"),
        "value": raw.get("value"),
        "states": raw.get("states", {}),
    }
    if width > 0 and height > 0:
        element["position"] = {"x": x, "y": y}
        element["size"] = {"w": width, "h": height}
    return element


def _normalize_match(raw):
    x = int(raw.get("x", 0))
    y = int(raw.get("y", 0))
    width = int(raw.get("width", 0))
    height = int(raw.get("height", 0))
    return {
        "text": raw.get("name") or raw.get("description") or "",
        "role": raw.get("role"),
        "x": int(x + width / 2),
        "y": int(y + height / 2),
        "width": width,
        "height": height,
        "confidence": 1.0,
        "source": "accessibility",
        "label": f'atspi:{raw.get("role", "")}:{raw.get("name", "")}',
    }


def _walk_pyatspi(node, pyatspi, depth=0, max_depth=6):
    if node is None or depth > max_depth:
        return
    yield depth, node
    try:
        child_count = node.childCount
    except Exception:
        child_count = 0
    for index in range(child_count):
        try:
            child = node[index]
        except Exception:
            continue
        yield from _walk_pyatspi(child, pyatspi, depth + 1, max_depth)


def _states_from_pyatspi(node, pyatspi):
    try:
        state = node.getState()
        return {
            "enabled": state.contains(pyatspi.STATE_ENABLED),
            "focused": state.contains(pyatspi.STATE_FOCUSED),
            "selected": state.contains(pyatspi.STATE_SELECTED),
            "visible": state.contains(pyatspi.STATE_VISIBLE),
            "offscreen": state.contains(pyatspi.STATE_SHOWING) is False,
        }
    except Exception:
        return {}


def _element_from_pyatspi(node, pyatspi):
    name = getattr(node, "name", None)
    description = None
    role = None
    try:
        description = node.description
    except Exception:
        pass
    try:
        role = node.getRoleName()
    except Exception:
        pass
    x = y = width = height = 0
    try:
        component = node.queryComponent()
        extents = component.getExtents(pyatspi.DESKTOP_COORDS)
        x, y, width, height = int(extents.x), int(extents.y), int(extents.width), int(extents.height)
    except Exception:
        pass
    return {
        "name": name,
        "description": description,
        "role": role,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "states": _states_from_pyatspi(node, pyatspi),
    }


def _run_with_pyatspi(app_name, text, text_match, max_depth):
    try:
        import pyatspi  # type: ignore
    except Exception:
        return None

    try:
        desktop = pyatspi.Registry.getDesktop(0)
    except Exception:
        return _error("atspi_bus_not_available", "atspi_desktop_unavailable")

    target_app = None
    for app in desktop:
        try:
            if _match_text(getattr(app, "name", ""), app_name, "contains"):
                target_app = app
                break
        except Exception:
            continue
    if target_app is None:
        return {
            "ok": False,
            "platform": "linux",
            "backend": "atspi",
            "error": "app_not_found",
            "app": app_name,
            "matches": [],
        }

    raw_elements = []
    matches = []
    for _depth, node in _walk_pyatspi(target_app, pyatspi, depth=0, max_depth=max_depth):
        raw = _element_from_pyatspi(node, pyatspi)
        raw_elements.append(raw)
        if raw.get("width", 0) > 0 and raw.get("height", 0) > 0:
            candidates = [raw.get("name"), raw.get("description")]
            if any(_match_text(candidate, text, text_match) for candidate in candidates):
                matches.append(_normalize_match(raw))

    elements = [_normalize_element(raw) for raw in raw_elements]
    return {
        "ok": True,
        "platform": "linux",
        "backend": "atspi",
        "app": getattr(target_app, "name", app_name),
        "element_count": len(elements),
        "elements": elements,
        "matches": matches,
    }


def run_linux_atspi_query(app_name, text=None, text_match="contains", max_depth=6):
    if platform.system().lower() != "linux":
        return {"ok": False, "platform": platform.system().lower(), "error": "linux_only", "matches": []}
    result = _run_with_pyatspi(app_name, text, text_match, max_depth)
    if result is not None:
        return result
    return _error("atspi_unavailable", "pyatspi_unavailable")
