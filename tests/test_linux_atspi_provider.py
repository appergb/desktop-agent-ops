import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class LinuxAtspiProviderTests(unittest.TestCase):
    def test_normalize_match_shape(self):
        import linux_atspi_provider  # noqa: E402

        raw = {
            "name": "Send",
            "role": "push button",
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 40,
        }
        out = linux_atspi_provider._normalize_match(raw)
        self.assertEqual(out["x"], 60)
        self.assertEqual(out["y"], 40)
        self.assertEqual(out["role"], "push button")
        self.assertEqual(out["source"], "accessibility")

    def test_error_shape(self):
        import linux_atspi_provider  # noqa: E402

        out = linux_atspi_provider._error("atspi_unavailable", "missing")
        self.assertEqual(out["ok"], False)
        self.assertEqual(out["hint"], "atspi_unavailable")


if __name__ == "__main__":
    unittest.main()
