import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import target_resolver  # noqa: E402


class AccessibilityProviderDispatchTests(unittest.TestCase):
    def test_accessibility_provider_dispatches_windows(self):
        import accessibility_provider  # noqa: E402

        with mock.patch.object(accessibility_provider.platform, "system", return_value="Windows"):
            with mock.patch.object(
                accessibility_provider,
                "_run_windows",
                return_value={"ok": True, "backend": "uia", "platform": "windows", "element_count": 1, "matches": []},
            ) as patched:
                out = accessibility_provider.run_accessibility_query("Notepad", "Save")
        self.assertEqual(out["backend"], "uia")
        self.assertEqual(out["platform"], "windows")
        patched.assert_called_once_with("Notepad", "Save", "contains", 6)

    def test_accessibility_provider_dispatches_linux(self):
        import accessibility_provider  # noqa: E402

        with mock.patch.object(accessibility_provider.platform, "system", return_value="Linux"):
            with mock.patch.object(
                accessibility_provider,
                "_run_linux",
                return_value={"ok": True, "backend": "atspi", "platform": "linux", "element_count": 1, "matches": []},
            ) as patched:
                out = accessibility_provider.run_accessibility_query("Firefox", "Open")
        self.assertEqual(out["backend"], "atspi")
        self.assertEqual(out["platform"], "linux")
        patched.assert_called_once_with("Firefox", "Open", "contains", 6)

    def test_target_resolver_choose_best_keeps_accessibility_source(self):
        best = target_resolver.choose_best([
            {
                "ok": True,
                "matches": [{"x": 1, "y": 2, "confidence": 1.0, "source": "accessibility"}],
            }
        ])
        self.assertEqual(best["source"], "accessibility")


if __name__ == "__main__":
    unittest.main()
