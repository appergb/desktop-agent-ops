import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pointer_runtime import click_pointer, move_cursor  # noqa: E402


class _FakePyAutoGui:
    def __init__(self):
        self.clicked = []
        self.moved = []

    def click(self, **kwargs):
        self.clicked.append(kwargs)

    def moveTo(self, x, y, duration=0.0):
        self.moved.append((x, y, duration))


class PointerRuntimeTests(unittest.TestCase):
    def test_move_cursor_prefers_cliclick_on_macos(self):
        calls = []

        payload = move_cursor(
            "darwin",
            100,
            200,
            0.0,
            run_cmd=lambda cmd: calls.append(cmd) or "",
            find_cliclick=lambda: "/usr/local/bin/cliclick",
            pyautogui_getter=lambda: _FakePyAutoGui(),
        )

        self.assertEqual(calls, [["/usr/local/bin/cliclick", "m:100,200"]])
        self.assertEqual(payload["backend"], "cliclick")
        self.assertEqual(payload["x"], 100)
        self.assertEqual(payload["y"], 200)

    def test_click_pointer_uses_pyautogui_for_middle_click_on_macos(self):
        fake_pg = _FakePyAutoGui()

        payload = click_pointer(
            "darwin",
            10,
            20,
            1,
            "middle",
            run_cmd=lambda cmd: "",
            find_cliclick=lambda: "/usr/local/bin/cliclick",
            pyautogui_getter=lambda: fake_pg,
        )

        self.assertEqual(payload["backend"], "pyautogui")
        self.assertEqual(fake_pg.clicked, [{"x": 10, "y": 20, "clicks": 1, "interval": 0.1, "button": "middle"}])


if __name__ == "__main__":
    unittest.main()
