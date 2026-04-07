#!/usr/bin/env python3
"""Platform-specific window lifecycle helpers."""

import re

from window_kernel import WindowState


def _normalize_title(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def select_window_by_title(windows, query):
    """Pick the best window match using exact, then partial title matching."""
    normalized_query = _normalize_title(query)
    if not normalized_query:
        return None

    exact_matches = []
    partial_matches = []
    for window in windows:
        title = _normalize_title(getattr(window, "title", ""))
        if not title:
            continue
        if title == normalized_query:
            exact_matches.append(window)
        elif normalized_query in title:
            partial_matches.append(window)

    if exact_matches:
        return exact_matches[0]
    if partial_matches:
        return partial_matches[0]
    return None


def _windows_match_title(left, right):
    return _normalize_title(left) == _normalize_title(right)


class MacOSWindowBackend:
    name = "macos"

    def __init__(self, osascript_runner, run_safe_cmd, cg_window_bounds_getter, sleep):
        self.osascript_runner = osascript_runner
        self.run_safe_cmd = run_safe_cmd
        self.cg_window_bounds_getter = cg_window_bounds_getter
        self.sleep = sleep

    def can_open_app(self):
        return True

    def probe(self, app_name):
        escaped_name = _escape_applescript_string(app_name)
        script = f'''tell application "System Events"
    if not (exists process "{escaped_name}") then
        return "false|0|0"
    end if
    tell process "{escaped_name}"
        set isFrontmost to frontmost
        set windowCount to count of windows
        set minimizedCount to 0
        repeat with w in windows
            try
                if value of attribute "AXMinimized" of w is true then
                    set minimizedCount to minimizedCount + 1
                end if
            end try
        end repeat
        return (isFrontmost as text) & "|" & (windowCount as text) & "|" & (minimizedCount as text)
    end tell
end tell'''
        result = self.osascript_runner(script, "window-probe", "darwin")
        if not result.get("ok"):
            return WindowState(frontmost=False, has_usable_window=False, details={"error": result.get("stderr")})

        raw = result.get("stdout", "false|0|0").strip()
        parts = raw.split("|")
        if len(parts) != 3:
            return WindowState(frontmost=False, has_usable_window=False, details={"raw": raw})

        frontmost = parts[0].strip().lower() == "true"
        window_count = int(parts[1].strip() or 0)
        minimized_count = int(parts[2].strip() or 0)
        cg_window = self.cg_window_bounds_getter(app_name)
        has_usable_window = (window_count > minimized_count) or bool(cg_window and cg_window.get("ok"))
        active_name = app_name if frontmost else None
        return WindowState(
            frontmost=frontmost,
            has_usable_window=has_usable_window,
            window_count=window_count,
            minimized_count=minimized_count,
            active_window_name=active_name,
            details={"cg_window_available": bool(cg_window and cg_window.get("ok"))},
        )

    def activate(self, app_name):
        escaped_name = _escape_applescript_string(app_name)
        script = f'''tell application "System Events"
    if exists process "{escaped_name}" then
        set visible of process "{escaped_name}" to true
    end if
end tell
tell application "{escaped_name}" to activate'''
        self.osascript_runner(script, "focus-app", "darwin")
        self.sleep(0.1)

    def restore(self, app_name):
        escaped_name = _escape_applescript_string(app_name)
        script = f'''tell application "System Events"
    if exists process "{escaped_name}" then
        tell process "{escaped_name}"
            repeat with w in windows
                try
                    set value of attribute "AXMinimized" of w to false
                end try
            end repeat
        end tell
    end if
end tell'''
        self.osascript_runner(script, "focus-app", "darwin")

    def raise_window(self, app_name):
        escaped_name = _escape_applescript_string(app_name)
        script = f'''tell application "System Events"
    if exists process "{escaped_name}" then
        tell process "{escaped_name}"
            set frontmost to true
            try
                perform action "AXRaise" of window 1
            end try
        end tell
    end if
end tell'''
        self.osascript_runner(script, "focus-app", "darwin")

    def open_app(self, app_name):
        self.run_safe_cmd(["open", "-a", app_name])
        self.sleep(0.3)

    def frontmost(self):
        result = self.osascript_runner(
            'tell application "System Events" to get name of first application process whose frontmost is true',
            "frontmost",
            "darwin",
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("stderr") or "osascript_failed")
        return result.get("stdout", "").strip()

    def list_apps(self):
        result = self.osascript_runner(
            'tell application "System Events" to get name of every application process',
            "list-apps",
            "darwin",
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("stderr") or "osascript_failed")
        return [item.strip() for item in result.get("stdout", "").split(",") if item.strip()]

    def front_window_bounds(self, app_name):
        escaped_name = _escape_applescript_string(app_name)
        script = f'''tell application "System Events"
  tell process "{escaped_name}"
    set frontmost to true
    set w to front window
    set p to position of w
    set s to size of w
    return (name of w as text) & "|" & (item 1 of p as text) & "," & (item 2 of p as text) & "|" & (item 1 of s as text) & "," & (item 2 of s as text)
  end tell
end tell'''
        result = self.osascript_runner(script, "front-window-bounds", "darwin")
        if result.get("ok"):
            raw = result.get("stdout", "")
            parts = raw.rsplit("|", 2)
            if len(parts) == 3:
                window_name, pos, size = parts
                x, y = [int(value.strip()) for value in pos.split(",")]
                width, height = [int(value.strip()) for value in size.split(",")]
                return {
                    "ok": True,
                    "action": "front-window-bounds",
                    "app": app_name,
                    "window": window_name,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "backend": "applescript",
                }

        cg_window = self.cg_window_bounds_getter(app_name)
        if cg_window:
            return cg_window
        raise RuntimeError(result.get("stderr") or "front_window_bounds_failed")


class WindowsWindowBackend:
    name = "windows"

    def __init__(self, pygetwindow_getter):
        self.pygetwindow_getter = pygetwindow_getter

    def can_open_app(self):
        return False

    def _module(self):
        module = self.pygetwindow_getter()
        if not module:
            raise RuntimeError("pygetwindow_unavailable")
        return module

    def _matching_windows(self, app_name):
        gw = self._module()
        windows = []
        if hasattr(gw, "getAllWindows"):
            windows = [window for window in gw.getAllWindows() if getattr(window, "title", "").strip()]
        elif hasattr(gw, "getWindowsWithTitle"):
            windows = gw.getWindowsWithTitle(app_name)
        best = select_window_by_title(windows, app_name)
        matches = []
        if best is not None:
            matches.append(best)
        return matches

    def _selected_window(self, app_name):
        matches = self._matching_windows(app_name)
        if not matches:
            raise RuntimeError("window_not_found")
        return matches[0], len(matches)

    def probe(self, app_name):
        try:
            window, match_count = self._selected_window(app_name)
        except RuntimeError:
            return WindowState(frontmost=False, has_usable_window=False, details={"error": "window_not_found"})

        gw = self._module()
        active = gw.getActiveWindow() if hasattr(gw, "getActiveWindow") else None
        active_title = getattr(active, "title", None)
        is_frontmost = bool(active_title and _windows_match_title(active_title, window.title))
        is_minimized = bool(getattr(window, "isMinimized", False))
        has_window = bool(getattr(window, "width", 0) > 0 and getattr(window, "height", 0) > 0)
        return WindowState(
            frontmost=is_frontmost,
            has_usable_window=bool(has_window and not is_minimized),
            window_count=match_count,
            minimized_count=1 if is_minimized else 0,
            active_window_name=window.title,
        )

    def activate(self, app_name):
        window, _ = self._selected_window(app_name)
        window.activate()

    def restore(self, app_name):
        window, _ = self._selected_window(app_name)
        if getattr(window, "isMinimized", False):
            window.restore()

    def raise_window(self, app_name):
        window, _ = self._selected_window(app_name)
        window.activate()

    def open_app(self, app_name):
        raise RuntimeError("windows_open_fallback_not_supported")

    def frontmost(self):
        gw = self._module()
        active = gw.getActiveWindow() if hasattr(gw, "getActiveWindow") else None
        if not active:
            raise RuntimeError("active_window_not_found")
        return active.title

    def list_apps(self):
        gw = self._module()
        return [title for title in gw.getAllTitles() if title.strip()]

    def front_window_bounds(self, app_name=None):
        gw = self._module()
        if app_name:
            window, _ = self._selected_window(app_name)
        else:
            window = gw.getActiveWindow()
            if not window:
                raise RuntimeError("active_window_not_found")
        if getattr(window, "isMinimized", False):
            window.restore()
        window.activate()
        return {
            "ok": True,
            "action": "front-window-bounds",
            "app": app_name or window.title,
            "window": window.title,
            "x": int(window.left),
            "y": int(window.top),
            "width": int(window.width),
            "height": int(window.height),
            "backend": "pygetwindow",
        }


class LinuxWindowBackend:
    name = "linux"

    def __init__(self, run_cmd, which):
        self.run_cmd = run_cmd
        self.which = which

    def can_open_app(self):
        return False

    def _require(self, binary):
        if not self.which(binary):
            raise RuntimeError(f"{binary}_missing")

    def _list_titles(self):
        self._require("wmctrl")
        raw = self.run_cmd(["wmctrl", "-l"])
        titles = []
        for line in raw.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[3].strip():
                titles.append(parts[3].strip())
        return titles

    def _selected_title(self, app_name):
        titles = self._list_titles()
        window = select_window_by_title([_TitleWindow(title) for title in titles], app_name)
        if not window:
            raise RuntimeError("window_not_found")
        return window.title, len([title for title in titles if _normalize_title(title) == _normalize_title(window.title)])

    def probe(self, app_name):
        try:
            title, match_count = self._selected_title(app_name)
        except RuntimeError:
            return WindowState(frontmost=False, has_usable_window=False, details={"error": "window_not_found"})

        active_title = None
        is_frontmost = False
        if self.which("xdotool"):
            try:
                wid = self.run_cmd(["xdotool", "getactivewindow"])
                active_title = self.run_cmd(["xdotool", "getwindowname", wid])
                is_frontmost = _windows_match_title(active_title, title)
            except Exception:
                active_title = None
        return WindowState(
            frontmost=is_frontmost,
            has_usable_window=True,
            window_count=match_count,
            minimized_count=0,
            active_window_name=active_title or title,
        )

    def activate(self, app_name):
        self._require("wmctrl")
        self.run_cmd(["wmctrl", "-a", app_name])

    def restore(self, app_name):
        self._require("wmctrl")
        self.run_cmd(["wmctrl", "-R", app_name])

    def raise_window(self, app_name):
        self._require("wmctrl")
        self.run_cmd(["wmctrl", "-a", app_name])

    def open_app(self, app_name):
        raise RuntimeError("linux_open_fallback_not_supported")

    def frontmost(self):
        self._require("xdotool")
        wid = self.run_cmd(["xdotool", "getactivewindow"])
        return self.run_cmd(["xdotool", "getwindowname", wid])

    def list_apps(self):
        return self._list_titles()

    def front_window_bounds(self, app_name=None):
        if app_name:
            try:
                self.restore(app_name)
            except Exception:
                self.activate(app_name)
        self._require("xdotool")
        wid = self.run_cmd(["xdotool", "getactivewindow"])
        geom_raw = self.run_cmd(["xdotool", "getwindowgeometry", "--shell", wid])
        name = self.run_cmd(["xdotool", "getwindowname", wid])
        geom = {}
        for line in geom_raw.splitlines():
            match = re.match(r"^(X|Y|WIDTH|HEIGHT)=(\d+)$", line.strip())
            if match:
                geom[match.group(1)] = int(match.group(2))
        if not all(key in geom for key in ("X", "Y", "WIDTH", "HEIGHT")):
            raise RuntimeError("geometry_parse_failed")
        return {
            "ok": True,
            "action": "front-window-bounds",
            "app": app_name or name,
            "window": name,
            "x": geom["X"],
            "y": geom["Y"],
            "width": geom["WIDTH"],
            "height": geom["HEIGHT"],
            "backend": "xdotool",
        }


class _TitleWindow:
    def __init__(self, title):
        self.title = title


def _escape_applescript_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')
