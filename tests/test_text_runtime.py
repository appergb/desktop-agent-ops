import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from runtime_support import DesktopRuntimeError  # noqa: E402
from text_runtime import press_key, type_text  # noqa: E402


class _FakePyAutoGui:
    def __init__(self):
        self.pressed = []
        self.written = []
        self.hotkeys = []

    def press(self, key):
        self.pressed.append(key)

    def write(self, text, interval=0.0):
        self.written.append((text, interval))

    def hotkey(self, *keys):
        self.hotkeys.append(keys)


class TextRuntimeTests(unittest.TestCase):
    def test_press_key_prefers_applescript_on_macos(self):
        payload = press_key(
            "darwin",
            "enter",
            osascript_runner=lambda script, action, platform_name: {"ok": True, "stdout": ""},
            run_cmd=lambda cmd: "",
            find_cliclick=lambda: "/usr/local/bin/cliclick",
            pyautogui_getter=lambda: _FakePyAutoGui(),
        )
        self.assertEqual(payload["backend"], "applescript")
        self.assertEqual(payload["key"], "return")

    def test_type_text_reports_non_ascii_clipboard_requirement(self):
        with self.assertRaises(DesktopRuntimeError) as ctx:
            type_text(
                "linux",
                "你好",
                paste_text_func=lambda text, action_name="type": (_ for _ in ()).throw(RuntimeError("literal_paste_unavailable")),
                run_cmd=lambda cmd: "",
                find_cliclick=lambda: None,
                pyautogui_getter=lambda: _FakePyAutoGui(),
            )
        self.assertEqual(ctx.exception.message, "non_ascii_text_requires_clipboard_paste")


if __name__ == "__main__":
    unittest.main()
