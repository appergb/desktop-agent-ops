#!/usr/bin/env python3
"""Keyboard and text input helpers separated from the CLI entrypoint."""

import base64

from input_runtime import (
    escape_applescript_string,
    has_non_ascii,
    macos_keycode,
    normalize_press_key,
    pyautogui_key_name,
)
from runtime_support import DesktopRuntimeError


_APPLESCRIPT_KEYS = {
    "return": "return",
    "tab": "tab",
    "escape": "escape",
    "delete": "delete",
    "backspace": "delete",
    "space": "space",
    "up": "up arrow",
    "down": "down arrow",
    "left": "left arrow",
    "right": "right arrow",
}

_CLICLICK_SPECIAL_KEYS = {
    "return", "enter", "tab", "escape", "esc", "delete", "backspace",
    "space", "arrow-up", "arrow-down", "arrow-left", "arrow-right",
    "home", "end", "page-up", "page-down", "fwd-delete",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "f9", "f10", "f11", "f12", "f13", "f14", "f15", "f16",
}


def _load_pyautogui(pyautogui_getter, system_name):
    try:
        return pyautogui_getter()
    except SystemExit as exc:
        raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc


def _apple_keycode(key_name, system_name):
    try:
        return macos_keycode(key_name)
    except KeyError as exc:
        raise DesktopRuntimeError(
            f"unknown_key: {key_name}",
            platform_name=system_name,
            hint="supported keys: return, tab, escape, delete, space, up arrow, down arrow, left arrow, right arrow",
        ) from exc


def press_key(system_name, key, osascript_runner, run_cmd, find_cliclick, pyautogui_getter):
    normalized_key = normalize_press_key(key)

    if system_name == "darwin":
        applescript_key = _APPLESCRIPT_KEYS.get(normalized_key, normalized_key)
        if applescript_key in ("return", "tab", "escape", "delete", "space", "up arrow", "down arrow", "left arrow", "right arrow"):
            script = f'tell application "System Events" to key code {_apple_keycode(applescript_key, system_name)}'
        else:
            escaped_key = escape_applescript_string(applescript_key)
            script = f'tell application "System Events" to keystroke "{escaped_key}"'

        result = osascript_runner(script, "press", system_name)
        if result["ok"]:
            return {"ok": True, "action": "press", "backend": "applescript", "key": normalized_key}

        cliclick = find_cliclick()
        if cliclick:
            try:
                run_cmd([cliclick, f"kp:{normalized_key}"])
                return {"ok": True, "action": "press", "backend": "cliclick", "key": normalized_key}
            except SystemExit:
                pass

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    pyautogui.press(pyautogui_key_name(normalized_key))
    return {"ok": True, "action": "press", "backend": "pyautogui", "key": normalized_key}


def paste_text(system_name, text, action_name, osascript_runner, subprocess_run, pyautogui_getter, which):
    if system_name == "darwin":
        if "\n" in text or "\r" in text:
            subprocess_run(["pbcopy"], input=text.encode("utf-8"), check=True)
            result = osascript_runner('tell application "System Events" to keystroke "v" using command down', action_name, system_name)
            if result["ok"]:
                return "pbcopy_paste"
            raise DesktopRuntimeError(result.get("stderr") or "paste_failed", platform_name=system_name)

        escaped = escape_applescript_string(text)
        script = f'''set the clipboard to "{escaped}"
delay 0.05
tell application "System Events" to keystroke "v" using command down'''
        result = osascript_runner(script, action_name, system_name)
        if result["ok"]:
            return "clipboard_paste"

        subprocess_run(["pbcopy"], input=text.encode("utf-8"), check=True)
        result = osascript_runner('tell application "System Events" to keystroke "v" using command down', action_name, system_name)
        if result["ok"]:
            return "pbcopy_paste"
        raise DesktopRuntimeError(result.get("stderr") or "paste_failed", platform_name=system_name)

    if system_name == "windows":
        script = f'Set-Clipboard -Value "{text}"'
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            subprocess_run(["powershell", "-NoProfile", "-EncodedCommand", encoded], check=True, capture_output=True, timeout=5)
        except Exception:
            subprocess_run(["clip"], input=text.encode("utf-16le"), check=True)
        pyautogui = _load_pyautogui(pyautogui_getter, system_name)
        pyautogui.hotkey("ctrl", "v")
        return "clipboard_paste"

    if system_name == "linux" and which("xclip"):
        subprocess_run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
        pyautogui = _load_pyautogui(pyautogui_getter, system_name)
        pyautogui.hotkey("ctrl", "v")
        return "xclip_paste"

    raise DesktopRuntimeError("literal_paste_unavailable", platform_name=system_name)


def type_text(system_name, text, paste_text_func, run_cmd, find_cliclick, pyautogui_getter):
    contains_non_ascii = has_non_ascii(text)
    try:
        backend = paste_text_func(text, action_name="type")
        return {"ok": True, "action": "type", "backend": backend, "text_length": len(text)}
    except Exception:
        pass

    if contains_non_ascii:
        raise DesktopRuntimeError(
            "non_ascii_text_requires_clipboard_paste",
            platform_name=system_name,
            hint="check_pbcopy_or_xclip_availability",
        )

    cliclick = find_cliclick()
    if cliclick and system_name == "darwin":
        try:
            run_cmd([cliclick, f"t:{text}"])
            return {"ok": True, "action": "type", "backend": "cliclick", "text_length": len(text)}
        except SystemExit:
            pass

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    pyautogui.write(text, interval=0.0)
    return {"ok": True, "action": "type", "backend": "pyautogui", "text_length": len(text)}


def insert_newline(system_name, count, paste_text_func):
    if count < 1:
        raise DesktopRuntimeError("count_must_be_positive", platform_name=system_name)
    try:
        backend = paste_text_func("\n" * count, action_name="insert-newline")
    except DesktopRuntimeError:
        raise
    except Exception as exc:
        raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
    return {"ok": True, "action": "insert-newline", "backend": backend, "count": count}


def send_hotkey(system_name, keys, run_cmd, find_cliclick, pyautogui_getter):
    cliclick = find_cliclick()
    if cliclick and system_name == "darwin":
        try:
            if len(keys) == 1:
                run_cmd([cliclick, f"kp:{keys[0]}"])
            else:
                modifiers = ",".join(keys[:-1])
                last_key = keys[-1]
                if last_key.lower() in _CLICLICK_SPECIAL_KEYS:
                    key_cmd = f"kp:{last_key}"
                else:
                    key_cmd = f"t:{last_key}"
                run_cmd([cliclick, f"kd:{modifiers}", key_cmd, f"ku:{modifiers}"])
        except SystemExit as exc:
            raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
        return {"ok": True, "action": "hotkey", "backend": "cliclick", "keys": keys}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    pyautogui.hotkey(*keys)
    return {"ok": True, "action": "hotkey", "backend": "pyautogui", "keys": keys}
