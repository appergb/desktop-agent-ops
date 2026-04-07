#!/usr/bin/env python3
import importlib.util
import json
import os
import platform
import shutil

if __name__ == "__main__":
    system = platform.system().lower()
    session = None
    limitations = []
    workarounds = []

    if system == 'linux':
        if os.environ.get('WAYLAND_DISPLAY'):
            session = 'wayland'
            limitations = [
                'pyautogui mouse/keyboard requires X11 — limited under Wayland',
                'xdotool only works via XWayland compatibility layer',
                'screenshot may require gnome-screenshot or spectacle instead of pyautogui',
            ]
            workarounds = [
                'Set DISPLAY=:0 for xdotool commands (uses XWayland)',
                'Use gnome-screenshot or spectacle for native Wayland screenshots',
                'Consider ydotool as a Wayland-native alternative to xdotool',
            ]
            # Check for available tools
            if shutil.which('ydotool'):
                workarounds.append('ydotool is available — prefer it over xdotool for Wayland')
        elif os.environ.get('DISPLAY'):
            session = 'x11'
        atspi_available = importlib.util.find_spec('pyatspi') is not None
        if atspi_available:
            workarounds.append('AT-SPI Python bindings are available — prefer structured accessibility targeting where supported')
        else:
            limitations.append('AT-SPI bindings not detected — Linux structured accessibility targeting may be unavailable')
            workarounds.append('Install python3-pyatspi or equivalent distro packages for GNOME accessibility support')

    result = {'ok': True, 'platform': system, 'linux_session': session}
    if limitations:
        result['limitations'] = limitations
        result['workarounds'] = workarounds

    if system == 'windows':
        result['windows_session'] = 'desktop'
        result['limitations'] = [
            'pygetwindow depends on pywin32 — ensure it is installed: uv pip install pywin32',
            'pyautogui coordinates may not account for Windows DPI scaling (125%-250%)',
            'UAC elevation may block some automation targets',
            'UI Automation may be blocked by UIPI when the target runs at a higher integrity level',
            'Windows Defender or AppLocker may block subprocess spawning',
        ]
        result['workarounds'] = [
            'Run Claude Code as administrator if UAC blocks automation',
            'Run the automation process at the same privilege level as the target app',
            'Disable "Scale for all displays" in Windows Display Settings if coordinates are off',
            'Use desktop_ops.py screenshot to verify window positions before clicking',
            'For WeChat Windows, prefer the visible send button over Enter-to-send',
        ]

    print(json.dumps(result, ensure_ascii=False))
