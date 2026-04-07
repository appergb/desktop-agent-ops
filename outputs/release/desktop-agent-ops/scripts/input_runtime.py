#!/usr/bin/env python3
"""Pure key and text helpers used by desktop input commands."""


def escape_applescript_string(value):
    """Escape backslashes and quotes before embedding text in AppleScript."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def normalize_press_key(key):
    """Normalize user-facing key names so Enter-like actions map to real key presses."""
    normalized = str(key).strip().lower()
    aliases = {
        "enter": "return",
        "return": "return",
        "esc": "escape",
        "backspace": "delete",
    }
    return aliases.get(normalized, normalized)


def pyautogui_key_name(key):
    """Translate normalized key names to the names expected by pyautogui."""
    mapping = {
        "return": "enter",
        "escape": "esc",
        "delete": "backspace",
        "up arrow": "up",
        "down arrow": "down",
        "left arrow": "left",
        "right arrow": "right",
    }
    return mapping.get(key, key)


def macos_keycode(key_name):
    """Return the macOS virtual key code used by AppleScript key code."""
    codes = {
        "return": 36,
        "tab": 48,
        "escape": 53,
        "delete": 51,
        "space": 49,
        "up arrow": 126,
        "down arrow": 125,
        "left arrow": 123,
        "right arrow": 124,
    }
    return codes[key_name]


def has_non_ascii(text):
    return any(ord(char) > 127 for char in text)
