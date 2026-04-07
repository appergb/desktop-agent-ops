import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from target_runtime import choose_best, merge_adjacent_boxes, normalize_text  # noqa: E402


class TargetRuntimeTests(unittest.TestCase):
    def test_normalize_text_compacts_whitespace_and_case(self):
        self.assertEqual(normalize_text("  Send   Button "), "sendbutton")

    def test_merge_adjacent_boxes_merges_split_cjk_text(self):
        boxes = [
            {"text": "发", "confidence": 90, "abs_box": {"x": 10, "y": 20, "width": 12, "height": 20}},
            {"text": "送", "confidence": 92, "abs_box": {"x": 23, "y": 20, "width": 12, "height": 20}},
        ]
        merged = merge_adjacent_boxes(boxes, "发送")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "发送")
        self.assertEqual(merged[0]["abs_box"]["x"], 10)
        self.assertEqual(merged[0]["abs_box"]["width"], 25)

    def test_choose_best_prefers_highest_confidence_match(self):
        best = choose_best([
            {"ok": True, "matches": [{"x": 10, "y": 10, "confidence": 0.4, "source": "ocr"}]},
            {"ok": True, "matches": [{"x": 20, "y": 20, "confidence": 0.9, "source": "accessibility"}]},
        ])
        self.assertEqual(best["source"], "accessibility")
        self.assertEqual(best["x"], 20)


if __name__ == "__main__":
    unittest.main()
