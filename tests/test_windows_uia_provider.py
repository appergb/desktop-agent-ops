import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class WindowsUiaProviderTests(unittest.TestCase):
    def test_normalize_match_shape(self):
        import windows_uia_provider  # noqa: E402

        raw = {
            "name": "Save",
            "control_type": "Button",
            "left": 100,
            "top": 200,
            "width": 80,
            "height": 20,
        }
        out = windows_uia_provider._normalize_match(raw)
        self.assertEqual(out["x"], 140)
        self.assertEqual(out["y"], 210)
        self.assertEqual(out["role"], "Button")
        self.assertEqual(out["source"], "accessibility")

    def test_permission_error_shape(self):
        import windows_uia_provider  # noqa: E402

        out = windows_uia_provider._permission_error("windows_uipi_blocked", "blocked")
        self.assertEqual(out["ok"], False)
        self.assertEqual(out["hint"], "windows_uipi_blocked")


if __name__ == "__main__":
    unittest.main()
