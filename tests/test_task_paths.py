import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skill' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import task_paths  # noqa: E402


class TaskPathsTests(unittest.TestCase):
    def test_resolve_task_dir_accepts_safe_identifier(self):
        task_dir = task_paths.resolve_task_dir('chat-window-01')
        self.assertEqual(task_dir.name, 'chat-window-01')
        self.assertEqual(task_dir.parent, task_paths.BASE.resolve())

    def test_resolve_task_dir_rejects_traversal(self):
        with self.assertRaisesRegex(ValueError, 'invalid_task_id'):
            task_paths.resolve_task_dir('../escape')

    def test_resolve_task_dir_rejects_path_separator(self):
        with self.assertRaisesRegex(ValueError, 'invalid_task_id'):
            task_paths.resolve_task_dir('nested/task')
