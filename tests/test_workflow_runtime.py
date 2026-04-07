import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_runtime import flatten_result_fields, substitute_vars  # noqa: E402


class WorkflowRuntimeTests(unittest.TestCase):
    def test_flatten_result_fields_handles_nested_dicts(self):
        flattened = flatten_result_fields({
            "best_candidate": {"x": 300, "y": 420},
            "window": {"bounds": {"width": 1024}},
        })
        self.assertEqual(flattened["best_candidate_x"], 300)
        self.assertEqual(flattened["best_candidate_y"], 420)
        self.assertEqual(flattened["window_bounds_width"], 1024)

    def test_substitute_vars_preserves_variable_boundaries(self):
        result = substitute_vars(
            "$PY $SCRIPT_DIR/tool.py $STEP_2_best_candidate_x $RESULT_best_candidate_y $param_name_suffix $param_name",
            {"param_name": "hello"},
            {"best_candidate": {"y": 450}},
            "",
            "python3",
            {2: {"best_candidate": {"x": 120}}},
            scripts_dir=SCRIPTS_DIR,
            skill_dir=SCRIPTS_DIR.parent,
        )
        self.assertIn("python3", result)
        self.assertIn(str((SCRIPTS_DIR / "tool.py").resolve()), result)
        self.assertIn("120", result)
        self.assertIn("450", result)
        self.assertIn("$param_name_suffix", result)
        self.assertTrue(result.endswith(" hello"))


if __name__ == "__main__":
    unittest.main()
