import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from screen_runtime import capture_screenshot, read_screen_size  # noqa: E402


class _FakePosition:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class _FakePyAutoGui:
    def __init__(self):
        self.saved_path = None

    def screenshot(self, region=None):
        class _FakeImage:
            def __init__(self, parent):
                self.parent = parent

            def save(self, path):
                self.parent.saved_path = path

        return _FakeImage(self)

    def position(self):
        return _FakePosition(33, 44)

    def size(self):
        return (1280, 720)


class ScreenRuntimeTests(unittest.TestCase):
    def test_capture_screenshot_uses_pyautogui_off_macos(self):
        fake_pg = _FakePyAutoGui()
        payload = capture_screenshot(
            "linux",
            "/tmp/example.png",
            {"x": 1, "y": 2, "width": 3, "height": 4},
            True,
            run_cmd=lambda cmd: "",
            run_safe_cmd=lambda cmd: {"ok": True, "stdout": "", "stderr": ""},
            find_cliclick=lambda: None,
            pyautogui_getter=lambda: fake_pg,
        )
        self.assertEqual(payload["output"], "/tmp/example.png")
        self.assertEqual(payload["mouse"], {"x": 33, "y": 44})
        self.assertEqual(payload["region"], {"x": 1, "y": 2, "width": 3, "height": 4})

    def test_read_screen_size_uses_osascript_on_macos(self):
        payload = read_screen_size(
            "darwin",
            osascript_runner=lambda script, action, platform_name: {"ok": True, "stdout": "0, 0, 1440, 900"},
            pyautogui_getter=lambda: _FakePyAutoGui(),
        )
        self.assertEqual(payload["width"], 1440)
        self.assertEqual(payload["height"], 900)


if __name__ == "__main__":
    unittest.main()
