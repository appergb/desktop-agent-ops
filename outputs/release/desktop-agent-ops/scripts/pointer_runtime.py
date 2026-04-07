#!/usr/bin/env python3
"""Pointer and scroll operations separated from the CLI entrypoint."""

from runtime_support import DesktopRuntimeError


def _load_pyautogui(pyautogui_getter, system_name):
    try:
        return pyautogui_getter()
    except SystemExit as exc:
        raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc


def move_cursor(system_name, x, y, duration, run_cmd, find_cliclick, pyautogui_getter):
    cliclick = find_cliclick()
    if cliclick and system_name == "darwin":
        try:
            run_cmd([cliclick, f"m:{x},{y}"])
        except SystemExit as exc:
            raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
        return {"ok": True, "action": "move", "backend": "cliclick", "x": x, "y": y, "duration": duration}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    pyautogui.moveTo(x, y, duration=duration)
    return {"ok": True, "action": "move", "backend": "pyautogui", "x": x, "y": y, "duration": duration}


def _pyautogui_click(pyautogui, x, y, clicks, button):
    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, clicks=clicks, interval=0.1, button=button)
    else:
        pyautogui.click(clicks=clicks, interval=0.1, button=button)


def click_pointer(system_name, x, y, clicks, button, run_cmd, find_cliclick, pyautogui_getter):
    cliclick = find_cliclick()
    if cliclick and system_name == "darwin":
        prefix = {"left": "c", "right": "rc", "middle": None}[button]
        if prefix is None:
            pyautogui = _load_pyautogui(pyautogui_getter, system_name)
            _pyautogui_click(pyautogui, x, y, clicks, button)
            return {"ok": True, "action": "click", "backend": "pyautogui", "clicks": clicks, "button": button, "x": x, "y": y}

        target = "." if x is None or y is None else f"{x},{y}"
        command = f"{prefix}:{target}"
        if clicks == 2 and button == "left":
            command = f"dc:{target}"
        elif clicks != 1:
            pyautogui = _load_pyautogui(pyautogui_getter, system_name)
            _pyautogui_click(pyautogui, x, y, clicks, button)
            return {"ok": True, "action": "click", "backend": "pyautogui", "clicks": clicks, "button": button, "x": x, "y": y}

        try:
            run_cmd([cliclick, command])
        except SystemExit as exc:
            raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
        return {"ok": True, "action": "click", "backend": "cliclick", "clicks": clicks, "button": button, "x": x, "y": y}

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    _pyautogui_click(pyautogui, x, y, clicks, button)
    return {"ok": True, "action": "click", "backend": "pyautogui", "clicks": clicks, "button": button, "x": x, "y": y}


def drag_pointer(system_name, x1, y1, x2, y2, duration, button, run_cmd, find_cliclick, pyautogui_getter):
    cliclick = find_cliclick()
    if cliclick and system_name == "darwin":
        if button != "left":
            raise DesktopRuntimeError(
                "cliclick drag currently supports left button only; use pyautogui",
                platform_name=system_name,
            )
        wait_ms = max(int(duration * 1000), 50)
        try:
            run_cmd([cliclick, f"dd:{x1},{y1}", f"w:{wait_ms}", f"dm:{x2},{y2}", f"du:{x2},{y2}"])
        except SystemExit as exc:
            raise DesktopRuntimeError(str(exc), platform_name=system_name) from exc
        return {
            "ok": True,
            "action": "drag",
            "backend": "cliclick",
            "from": [x1, y1],
            "to": [x2, y2],
            "button": button,
            "duration": duration,
        }

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    pyautogui.moveTo(x1, y1, duration=0)
    pyautogui.dragTo(x2, y2, duration=duration, button=button)
    return {
        "ok": True,
        "action": "drag",
        "backend": "pyautogui",
        "from": [x1, y1],
        "to": [x2, y2],
        "button": button,
        "duration": duration,
    }


def scroll_pointer(system_name, amount, x, y, direction, run_cmd, find_cliclick, pyautogui_getter):
    if x is not None and y is not None:
        cliclick = find_cliclick()
        if cliclick and system_name == "darwin":
            try:
                run_cmd([cliclick, f"m:{x},{y}"])
            except SystemExit:
                pyautogui = _load_pyautogui(pyautogui_getter, system_name)
                pyautogui.moveTo(x, y, duration=0)
        else:
            pyautogui = _load_pyautogui(pyautogui_getter, system_name)
            pyautogui.moveTo(x, y, duration=0)

    pyautogui = _load_pyautogui(pyautogui_getter, system_name)
    if direction == "horizontal":
        pyautogui.hscroll(amount)
        return {"ok": True, "action": "scroll", "backend": "pyautogui", "direction": "horizontal", "amount": amount, "x": x, "y": y}

    pyautogui.scroll(amount)
    return {"ok": True, "action": "scroll", "backend": "pyautogui", "direction": "vertical", "amount": amount, "x": x, "y": y}
