#!/usr/bin/env python3
"""Shared window activation and restore lifecycle."""

from dataclasses import dataclass


@dataclass
class WindowState:
    frontmost: bool
    has_usable_window: bool
    window_count: int = 0
    minimized_count: int = 0
    active_window_name: str | None = None
    details: dict | None = None


class WindowKernel:
    """Apply a consistent restore lifecycle across platform backends."""

    def __init__(self, backend):
        self.backend = backend

    def focus_app(self, app_name):
        initial = self.backend.probe(app_name)
        if initial.frontmost and initial.has_usable_window:
            self.backend.raise_window(app_name)
            return self._result(app_name, initial, used_open_fallback=False)

        self.backend.activate(app_name)
        self.backend.restore(app_name)
        self.backend.raise_window(app_name)
        current = self.backend.probe(app_name)
        used_open_fallback = False

        if not (current.frontmost and current.has_usable_window) and self.backend.can_open_app():
            self.backend.open_app(app_name)
            used_open_fallback = True
            self.backend.activate(app_name)
            self.backend.restore(app_name)
            self.backend.raise_window(app_name)
            current = self.backend.probe(app_name)

        return self._result(app_name, current, used_open_fallback)

    def _result(self, app_name, state, used_open_fallback):
        return {
            "ok": bool(state.frontmost and state.has_usable_window),
            "action": "focus-app",
            "app": app_name,
            "verified_frontmost": bool(state.frontmost),
            "window_restored": bool(state.has_usable_window),
            "used_open_fallback": bool(used_open_fallback),
            "window_count": int(state.window_count),
            "minimized_count": int(state.minimized_count),
            "backend": getattr(self.backend, "name", "unknown"),
            "active_window": state.active_window_name,
            "details": state.details or {},
        }
