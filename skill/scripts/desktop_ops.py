#!/usr/bin/env python3
import argparse
import json
import platform
import shutil
import subprocess
import sys
import time

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None

from input_runtime import (
    escape_applescript_string,
    normalize_press_key,
    pyautogui_key_name,
)
from pointer_runtime import click_pointer, drag_pointer, move_cursor, scroll_pointer
from runtime_support import DesktopRuntimeError
from screen_runtime import capture_screenshot, read_mouse_position, read_pixel_color, read_screen_size
from text_runtime import (
    insert_newline,
    paste_text as runtime_paste_text,
    press_key,
    send_hotkey,
    type_text,
)
from window_backends import LinuxWindowBackend, MacOSWindowBackend, WindowsWindowBackend
from window_kernel import WindowKernel


def jprint(data):
    print(json.dumps(data, ensure_ascii=False))


def jerror(action, message, platform_name=None, hint=None, details=None):
    payload = {"ok": False, "action": action, "error": message}
    if platform_name:
        payload["platform"] = platform_name
    if hint:
        payload["hint"] = hint
    if details:
        payload["details"] = details
    jprint(payload)
    sys.exit(1)


def run(cmd, timeout=10):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(p.stderr.strip() or f"command failed: {' '.join(cmd)}")
    return p.stdout.strip()


def run_safe(cmd, timeout=10):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {
        "ok": p.returncode == 0,
        "code": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def osascript(script, action, platform_name):
    result = run_safe(["/usr/bin/osascript", "-e", script])
    if result["ok"]:
        return {"ok": True, "stdout": result["stdout"]}
    stderr = result["stderr"]
    hint = None
    if "Not authorized" in stderr or "-1743" in stderr or "-10827" in stderr:
        hint = "automation_permission_required"
    return {"ok": False, "stderr": stderr, "hint": hint}


def _cg_window_bounds(app_name):
    """Fallback: get window bounds via CGWindowListCopyWindowInfo (Quartz).

    Some apps (WeChat 4.x, Electron/Chromium-based) render windows that are
    invisible to System Events but visible to the Core Graphics window server.
    This function finds the largest on-screen window owned by the given app
    (matching by process name, bundle display name, or localized name).
    Returns a dict like {ok, app, window, x, y, width, height} or None.
    """
    try:
        import Quartz
        import AppKit

        # Build a set of names to match: the original name, plus any localized bundle name
        names_to_match = {app_name}
        try:
            workspace = AppKit.NSWorkspace.sharedWorkspace()
            for running_app in workspace.runningApplications():
                loc_name = running_app.localizedName() or ''
                exec_url = str(running_app.executableURL() or '')
                bundle_id = running_app.bundleIdentifier() or ''
                # Match by: localized name equals input, OR executable path contains input
                if (loc_name.lower() == app_name.lower()
                        or app_name.lower() in exec_url.lower()
                        or app_name.lower() in bundle_id.lower()):
                    if loc_name:
                        names_to_match.add(loc_name)
        except Exception:
            pass

        # Get on-screen windows first, then try all windows
        for opts in [
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGWindowListOptionAll,
        ]:
            windows = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID)
            if not windows:
                continue
            best = None
            best_area = 0
            for w in windows:
                owner = w.get('kCGWindowOwnerName', '')
                layer = w.get('kCGWindowLayer', -1)
                if layer != 0:  # Skip non-standard layers (menus, overlays, etc.)
                    continue
                if owner.lower() not in {n.lower() for n in names_to_match} and owner not in names_to_match:
                    continue
                bounds = w.get('kCGWindowBounds', {})
                bw = int(bounds.get('Width', 0))
                bh = int(bounds.get('Height', 0))
                area = bw * bh
                if area > best_area and bw > 50 and bh > 50:
                    best = {
                        "ok": True,
                        "action": "front-window-bounds",
                        "app": app_name,
                        "window": str(w.get('kCGWindowName', '') or owner),
                        "x": int(bounds.get('X', 0)),
                        "y": int(bounds.get('Y', 0)),
                        "width": bw,
                        "height": bh,
                        "backend": "cgwindow",
                    }
                    best_area = area
            if best:
                return best
    except Exception:
        pass
    return None


def pyautogui_mod():
    try:
        import pyautogui  # type: ignore
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        return pyautogui
    except Exception as e:
        raise SystemExit(f"pyautogui unavailable: {e}")


def pygetwindow_mod():
    try:
        import pygetwindow  # type: ignore
        return pygetwindow
    except Exception as e:
        return None


def find_running_app(query, candidates):
    """Case-insensitive exact match of query against candidate process names."""
    q = query.lower()
    for name in candidates:
        if name.lower() == q:
            return name
    return None


def find_cliclick():
    return shutil.which('cliclick')


def _emit_runtime_result(action, callback, *args, **kwargs):
    try:
        payload = callback(*args, **kwargs)
    except DesktopRuntimeError as exc:
        jerror(
            action,
            exc.message,
            exc.platform_name or platform.system().lower(),
            hint=exc.hint,
            details=exc.details,
        )
        return
    jprint(payload)


def cmd_screenshot(output=None, x=None, y=None, width=None, height=None, with_cursor=False):
    system = platform.system().lower()
    region = None if None in (x, y, width, height) else {"x": x, "y": y, "width": width, "height": height}
    _emit_runtime_result(
        "screenshot",
        capture_screenshot,
        system,
        output,
        region,
        with_cursor,
        run,
        run_safe,
        find_cliclick,
        pyautogui_mod,
    )


def cmd_frontmost():
    system = platform.system().lower()
    try:
        name = _window_backend(system).frontmost()
    except RuntimeError as exc:
        jerror("frontmost", str(exc), system)
        return
    jprint({"ok": True, "frontmost_app": name})


def cmd_list_apps():
    system = platform.system().lower()
    try:
        apps = _window_backend(system).list_apps()
    except RuntimeError as exc:
        jerror("list-apps", str(exc), system)
        return
    jprint({"ok": True, "apps": apps})


def cmd_focus_app(name):
    system = platform.system().lower()
    try:
        result = WindowKernel(_window_backend(system)).focus_app(name)
    except RuntimeError as exc:
        jerror("focus-app", str(exc), system)
        return
    if not result.get("ok"):
        jerror("focus-app", "window_restore_failed", system, details=result)
        return
    jprint(result)


def cmd_front_window_bounds(app=None):
    system = platform.system().lower()
    try:
        backend = _window_backend(system)
        process_name = app or backend.frontmost()
        if app:
            focus_result = WindowKernel(backend).focus_app(process_name)
            if not focus_result.get("ok"):
                raise RuntimeError("window_restore_failed")
        bounds = backend.front_window_bounds(process_name)
    except RuntimeError as exc:
        jerror("front-window-bounds", str(exc), system)
        return
    jprint(bounds)


def _window_backend(system_name):
    if system_name == "darwin":
        return MacOSWindowBackend(
            osascript_runner=osascript,
            run_safe_cmd=run_safe,
            cg_window_bounds_getter=_cg_window_bounds,
            sleep=time.sleep,
        )
    if system_name == "windows":
        return WindowsWindowBackend(pygetwindow_getter=pygetwindow_mod)
    if system_name == "linux":
        return LinuxWindowBackend(run_cmd=run, which=shutil.which)
    raise RuntimeError("not_implemented")


def cmd_move(x, y, duration=0.0):
    _emit_runtime_result("move", move_cursor, platform.system().lower(), x, y, duration, run, find_cliclick, pyautogui_mod)


def cmd_click(x=None, y=None, clicks=1, button="left"):
    _emit_runtime_result("click", click_pointer, platform.system().lower(), x, y, clicks, button, run, find_cliclick, pyautogui_mod)


def cmd_drag(x1, y1, x2, y2, duration=0.2, button="left"):
    _emit_runtime_result(
        "drag",
        drag_pointer,
        platform.system().lower(),
        x1,
        y1,
        x2,
        y2,
        duration,
        button,
        run,
        find_cliclick,
        pyautogui_mod,
    )


def cmd_scroll(amount, x=None, y=None, direction="vertical"):
    _emit_runtime_result(
        "scroll",
        scroll_pointer,
        platform.system().lower(),
        amount,
        x,
        y,
        direction,
        run,
        find_cliclick,
        pyautogui_mod,
    )


def cmd_press(key):
    _emit_runtime_result("press", press_key, platform.system().lower(), key, osascript, run, find_cliclick, pyautogui_mod)


def paste_text(text, action_name='type'):
    return runtime_paste_text(
        platform.system().lower(),
        text,
        action_name,
        osascript,
        subprocess.run,
        pyautogui_mod,
        shutil.which,
    )


def cmd_type(text):
    _emit_runtime_result(
        "type",
        type_text,
        platform.system().lower(),
        text,
        paste_text,
        run,
        find_cliclick,
        pyautogui_mod,
    )


def cmd_insert_newline(count=1):
    _emit_runtime_result("insert-newline", insert_newline, platform.system().lower(), count, paste_text)


def cmd_hotkey(keys):
    _emit_runtime_result("hotkey", send_hotkey, platform.system().lower(), keys, run, find_cliclick, pyautogui_mod)


def cmd_mouse_position():
    _emit_runtime_result("mouse-position", read_mouse_position, platform.system().lower(), run, find_cliclick, pyautogui_mod)


def cmd_screen_size():
    _emit_runtime_result("screen-size", read_screen_size, platform.system().lower(), osascript, pyautogui_mod)


def cmd_pixel_color(x, y):
    _emit_runtime_result("pixel-color", read_pixel_color, platform.system().lower(), x, y, Image, run_safe, pyautogui_mod)


def build_parser():
    p = argparse.ArgumentParser(description="desktop helper ops")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("screenshot")
    s.add_argument("--output")
    s.add_argument("--x", type=int)
    s.add_argument("--y", type=int)
    s.add_argument("--width", type=int)
    s.add_argument("--height", type=int)
    s.add_argument("--with-cursor", action="store_true")

    cr = sub.add_parser("capture-region")
    cr.add_argument("--x", type=int, required=True)
    cr.add_argument("--y", type=int, required=True)
    cr.add_argument("--width", type=int, required=True)
    cr.add_argument("--height", type=int, required=True)
    cr.add_argument("--output")
    cr.add_argument("--with-cursor", action="store_true")

    sub.add_parser("frontmost")
    sub.add_parser("list-apps")

    fwb = sub.add_parser("front-window-bounds")
    fwb.add_argument("--app")

    fa = sub.add_parser("focus-app")
    fa.add_argument("--name", required=True)

    mv = sub.add_parser("move")
    mv.add_argument("--x", type=int, required=True)
    mv.add_argument("--y", type=int, required=True)
    mv.add_argument("--duration", type=float, default=0.0)

    c = sub.add_parser("click")
    c.add_argument("--x", type=int)
    c.add_argument("--y", type=int)
    c.add_argument("--button", choices=["left", "right", "middle"], default="left")

    dc = sub.add_parser("double-click")
    dc.add_argument("--x", type=int)
    dc.add_argument("--y", type=int)
    dc.add_argument("--button", choices=["left", "right", "middle"], default="left")

    d = sub.add_parser("drag")
    d.add_argument("--x1", type=int, required=True)
    d.add_argument("--y1", type=int, required=True)
    d.add_argument("--x2", type=int, required=True)
    d.add_argument("--y2", type=int, required=True)
    d.add_argument("--duration", type=float, default=0.2)
    d.add_argument("--button", choices=["left", "right", "middle"], default="left")

    sc = sub.add_parser("scroll")
    sc.add_argument("--amount", type=int, required=True, help="Scroll amount: positive=up, negative=down")
    sc.add_argument("--x", type=int, help="Move cursor to X before scrolling (ensures correct window)")
    sc.add_argument("--y", type=int, help="Move cursor to Y before scrolling (ensures correct window)")
    sc.add_argument("--direction", choices=["vertical", "horizontal"], default="vertical")

    pr = sub.add_parser("press")
    pr.add_argument("--key", required=True)

    t = sub.add_parser("type")
    t.add_argument("--text", required=True)

    nl = sub.add_parser("insert-newline")
    nl.add_argument("--count", type=int, default=1)

    hk = sub.add_parser("hotkey")
    hk.add_argument("--keys", nargs='+', required=True)

    sub.add_parser("mouse-position")
    sub.add_parser("screen-size")

    pc = sub.add_parser("pixel-color")
    pc.add_argument("--x", type=int, required=True)
    pc.add_argument("--y", type=int, required=True)
    return p


def main():
    args = build_parser().parse_args()
    if args.cmd == "screenshot":
        cmd_screenshot(args.output, args.x, args.y, args.width, args.height, args.with_cursor)
    elif args.cmd == "capture-region":
        cmd_screenshot(args.output, args.x, args.y, args.width, args.height, args.with_cursor)
    elif args.cmd == "frontmost":
        cmd_frontmost()
    elif args.cmd == "list-apps":
        cmd_list_apps()
    elif args.cmd == "front-window-bounds":
        cmd_front_window_bounds(args.app)
    elif args.cmd == "focus-app":
        cmd_focus_app(args.name)
    elif args.cmd == "move":
        cmd_move(args.x, args.y, args.duration)
    elif args.cmd == "click":
        cmd_click(args.x, args.y, 1, args.button)
    elif args.cmd == "double-click":
        cmd_click(args.x, args.y, 2, args.button)
    elif args.cmd == "drag":
        cmd_drag(args.x1, args.y1, args.x2, args.y2, args.duration, args.button)
    elif args.cmd == "scroll":
        cmd_scroll(args.amount, args.x, args.y, args.direction)
    elif args.cmd == "press":
        cmd_press(args.key)
    elif args.cmd == "type":
        cmd_type(args.text)
    elif args.cmd == "insert-newline":
        cmd_insert_newline(args.count)
    elif args.cmd == "hotkey":
        cmd_hotkey(args.keys)
    elif args.cmd == "mouse-position":
        cmd_mouse_position()
    elif args.cmd == "screen-size":
        cmd_screen_size()
    elif args.cmd == "pixel-color":
        cmd_pixel_color(args.x, args.y)
    else:
        raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
