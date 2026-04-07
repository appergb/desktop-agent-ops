#!/usr/bin/env python3
"""Screen capture and readback helpers separated from the CLI entrypoint."""

import os
import tempfile
from pathlib import Path

from runtime_support import DesktopRuntimeError


def _temp_output_path():
    fd, path = tempfile.mkstemp(prefix="desktop-agent-", suffix=".png")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    return path


def _load_pyautogui(pyautogui_getter, system_name):
    try:
        return pyautogui_getter()
    except SystemExit as exc:
        raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc


def capture_screenshot(system_name, output, region, with_cursor, run_cmd, run_safe_cmd, find_cliclick, pyautogui_getter):
    output_path = output or _temp_output_path()
    if system_name == "darwin":
        cmd = ["/usr/sbin/screencapture", "-x"]
        if region:
            cmd += ["-R", f'{region["x"]},{region["y"]},{region["width"]},{region["height"]}']
        cmd.append(output_path)
        result = run_safe_cmd(cmd)
        if not result["ok"]:
            hint = None
            if "could not create image from display" in result.get("stderr", "").lower():
                hint = "screen_recording_permission_required"
            raise DesktopRuntimeError(
                result["stderr"] or "screencapture_failed",
                platform_name=system_name,
                hint=hint,
            )

        mouse = None
        if with_cursor:
            try:
                cliclick = find_cliclick()
                if cliclick:
                    out = run_cmd([cliclick, "-d", "stdout", "p:."])
                    mx, my = [int(value) for value in out.strip().split(",")]
                    mouse = {"x": mx, "y": my}
            except Exception:
                mouse = None

        return {"ok": True, "action": "screenshot", "output": output_path, "with_cursor": with_cursor, "mouse": mouse, "region": region}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    try:
        if region:
            image = pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
        else:
            image = pyautogui.screenshot()
        image.save(output_path)
        mouse = None
        if with_cursor:
            position = pyautogui.position()
            mouse = {"x": int(position.x), "y": int(position.y)}
        return {"ok": True, "action": "screenshot", "output": output_path, "with_cursor": with_cursor, "mouse": mouse, "region": region}
    except Exception as exc:
        raise DesktopRuntimeError(f"not implemented or failed: {exc}", platform_name=system_name) from exc


def read_mouse_position(system_name, run_cmd, find_cliclick, pyautogui_getter):
    cliclick = find_cliclick()
    if cliclick:
        try:
            out = run_cmd([cliclick, "-d", "stdout", "p:."])
        except SystemExit as exc:
            raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
        x, y = [int(value) for value in out.strip().split(",")]
        return {"ok": True, "backend": "cliclick", "x": x, "y": y}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    position = pyautogui.position()
    return {"ok": True, "backend": "pyautogui", "x": position.x, "y": position.y}


def read_screen_size(system_name, osascript_runner, pyautogui_getter):
    if system_name == "darwin":
        result = osascript_runner('tell application "Finder" to get bounds of window of desktop', "screen-size", system_name)
        if not result["ok"]:
            raise DesktopRuntimeError(
                result.get("stderr") or "osascript_failed",
                platform_name=system_name,
                hint=result.get("hint"),
            )
        parts = [int(value.strip()) for value in result["stdout"].split(",")]
        left, top, right, bottom = parts
        return {"ok": True, "width": right - left, "height": bottom - top, "bounds": [left, top, right, bottom]}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    width, height = pyautogui.size()
    return {"ok": True, "width": width, "height": height}


def read_pixel_color(system_name, x, y, image_module, run_safe_cmd, pyautogui_getter):
    if image_module is None:
        raise DesktopRuntimeError("PIL unavailable: cannot read pixel-color", platform_name=system_name)

    fd, tmp = tempfile.mkstemp(prefix="desktop-pixel-", suffix=".png")
    os.close(fd)
    try:
        try:
            if system_name == "darwin":
                result = run_safe_cmd(["/usr/sbin/screencapture", "-x", "-R", f"{x},{y},1,1", tmp])
                if not result["ok"]:
                    raise DesktopRuntimeError("screenshot_failed", platform_name=system_name)
            else:
                pyautogui = _load_pyautogui(pyautogui_getter, system_name)
                image = pyautogui.screenshot(region=(x, y, 1, 1))
                image.save(tmp)
        except DesktopRuntimeError:
            raise
        except Exception as exc:
            raise DesktopRuntimeError(f"screenshot_failed: {exc}", platform_name=system_name) from exc

        image = image_module.open(tmp)
        pixel = image.getpixel((0, 0))
        if isinstance(pixel, int):
            rgb = [pixel, pixel, pixel]
        else:
            rgb = list(pixel[:3])
        hex_value = "#%02x%02x%02x" % tuple(rgb)
        return {"ok": True, "action": "pixel-color", "x": x, "y": y, "rgb": rgb, "hex": hex_value}
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass
