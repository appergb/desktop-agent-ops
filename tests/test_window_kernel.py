import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from window_backends import select_window_by_title  # noqa: E402
from window_kernel import WindowKernel, WindowState  # noqa: E402


class FakeBackend:
    def __init__(self, states, supports_open=True):
        self.states = list(states)
        self.calls = []
        self.supports_open = supports_open
        self.name = "fake"

    def probe(self, app_name):
        self.calls.append(("probe", app_name))
        if not self.states:
            raise AssertionError("probe called too many times")
        return self.states.pop(0)

    def activate(self, app_name):
        self.calls.append(("activate", app_name))

    def restore(self, app_name):
        self.calls.append(("restore", app_name))

    def raise_window(self, app_name):
        self.calls.append(("raise", app_name))

    def can_open_app(self):
        return self.supports_open

    def open_app(self, app_name):
        self.calls.append(("open_app", app_name))


class FakeWindow:
    def __init__(self, title):
        self.title = title


class WindowKernelTests(unittest.TestCase):
    def test_focus_app_uses_open_fallback_when_restore_does_not_reveal_window(self):
        backend = FakeBackend([
            WindowState(frontmost=False, has_usable_window=False, window_count=0),
            WindowState(frontmost=True, has_usable_window=False, window_count=1, minimized_count=1),
            WindowState(frontmost=True, has_usable_window=True, window_count=1, minimized_count=0),
        ])

        result = WindowKernel(backend).focus_app("WeChat")

        self.assertTrue(result["ok"])
        self.assertTrue(result["verified_frontmost"])
        self.assertTrue(result["window_restored"])
        self.assertTrue(result["used_open_fallback"])
        self.assertEqual(
            backend.calls,
            [
                ("probe", "WeChat"),
                ("activate", "WeChat"),
                ("restore", "WeChat"),
                ("raise", "WeChat"),
                ("probe", "WeChat"),
                ("open_app", "WeChat"),
                ("activate", "WeChat"),
                ("restore", "WeChat"),
                ("raise", "WeChat"),
                ("probe", "WeChat"),
            ],
        )

    def test_focus_app_short_circuits_when_window_is_already_usable(self):
        backend = FakeBackend([
            WindowState(frontmost=True, has_usable_window=True, window_count=1, minimized_count=0),
        ])

        result = WindowKernel(backend).focus_app("WeChat")

        self.assertTrue(result["ok"])
        self.assertTrue(result["verified_frontmost"])
        self.assertFalse(result["used_open_fallback"])
        self.assertEqual(
            backend.calls,
            [
                ("probe", "WeChat"),
                ("raise", "WeChat"),
            ],
        )


class WindowSelectionTests(unittest.TestCase):
    def test_select_window_by_title_prefers_exact_case_insensitive_match(self):
        windows = [FakeWindow("微信"), FakeWindow("WeChat"), FakeWindow("WeChat - Chat")]
        best = select_window_by_title(windows, "wechat")
        self.assertIsNotNone(best)
        self.assertEqual(best.title, "WeChat")

    def test_select_window_by_title_falls_back_to_partial_match(self):
        windows = [FakeWindow("WeChat - File Transfer"), FakeWindow("Safari")]
        best = select_window_by_title(windows, "wechat")
        self.assertIsNotNone(best)
        self.assertEqual(best.title, "WeChat - File Transfer")


if __name__ == "__main__":
    unittest.main()
