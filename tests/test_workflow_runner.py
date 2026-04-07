import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import workflow_runner  # noqa: E402


class WorkflowRunnerSubstitutionTests(unittest.TestCase):
    def test_flatten_step_result_flattens_nested_dict_fields(self):
        flattened = workflow_runner._flatten_step_result({
            "best_candidate": {"x": 120, "y": 240},
            "window_bounds": {"width": 800},
        })
        self.assertEqual(flattened["best_candidate_x"], 120)
        self.assertEqual(flattened["best_candidate_y"], 240)
        self.assertEqual(flattened["window_bounds_width"], 800)

    def test_substitute_vars_resolves_nested_step_tokens(self):
        resolved = workflow_runner.substitute_vars(
            "$STEP_3_best_candidate_x,$STEP_3_best_candidate_y",
            {},
            {},
            "",
            "python3",
            {3: {"best_candidate": {"x": 120, "y": 240}}},
        )
        self.assertEqual(resolved, "120,240")

    def test_substitute_vars_exposes_script_dir(self):
        resolved = workflow_runner.substitute_vars(
            "$SCRIPT_DIR/desktop_ops.py",
            {},
            {},
            "",
            "python3",
            {},
        )
        self.assertEqual(
            resolved,
            str((SCRIPTS_DIR / "desktop_ops.py").resolve()),
        )

    def test_substitute_vars_exposes_skill_dir(self):
        resolved = workflow_runner.substitute_vars(
            "$SKILL_DIR/workflows/examples/open-app-and-click.md",
            {},
            {},
            "",
            "python3",
            {},
        )
        self.assertEqual(
            resolved,
            str((SCRIPTS_DIR.parent / "workflows" / "examples" / "open-app-and-click.md").resolve()),
        )


if __name__ == "__main__":
    unittest.main()
