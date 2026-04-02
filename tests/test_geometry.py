import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skill' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import desktop_ops  # noqa: E402
import target_report  # noqa: E402
import targeting  # noqa: E402
import window_regions  # noqa: E402


class GeometryTests(unittest.TestCase):
    def test_targeting_candidate_points_are_stable(self):
        points = targeting.candidate_points(10, 20, 100, 60)
        self.assertEqual(len(points), 5)
        self.assertEqual(points[0], {'label': 'center', 'x': 60, 'y': 50})

    def test_target_report_candidate_points_match_region_shape(self):
        region = {
            'absolute': {'x': 100, 'y': 200, 'width': 80, 'height': 40},
        }
        points = target_report.candidate_points(region)
        self.assertEqual(points[0]['label'], 'center')
        self.assertEqual(points[0]['x'], 140)
        self.assertEqual(points[0]['y'], 220)

    def test_window_region_preset_offsets(self):
        presets = window_regions.presets(50, 80, 1000, 800)
        bottom_input = presets['bottom_input']['absolute']
        self.assertEqual(bottom_input['x'], 330)
        self.assertEqual(bottom_input['y'], 720)
        self.assertEqual(bottom_input['width'], 660)
        self.assertEqual(bottom_input['height'], 128)

    def test_applescript_escape_handles_quotes_and_backslashes(self):
        escaped = desktop_ops.escape_applescript_string('Finder "Preview" \\ Test')
        self.assertEqual(escaped, 'Finder \\\"Preview\\\" \\\\ Test')

    def test_capture_region_parser_has_with_cursor_flag(self):
        args = desktop_ops.build_parser().parse_args([
            'capture-region',
            '--x', '1',
            '--y', '2',
            '--width', '3',
            '--height', '4',
        ])
        self.assertFalse(args.with_cursor)

    def test_normalize_press_key_treats_enter_like_values_as_return(self):
        self.assertEqual(desktop_ops.normalize_press_key('enter'), 'return')
        self.assertEqual(desktop_ops.normalize_press_key('return'), 'return')
        self.assertEqual(desktop_ops.normalize_press_key('newline'), 'newline')

    def test_pyautogui_key_name_maps_return_to_enter(self):
        self.assertEqual(desktop_ops.pyautogui_key_name('return'), 'enter')

    def test_insert_newline_parser_has_default_count(self):
        args = desktop_ops.build_parser().parse_args(['insert-newline'])
        self.assertEqual(args.count, 1)

    def test_find_running_app_matches_exact_normalized_name(self):
        candidates = ['WeChat', 'Safari']
        self.assertEqual(desktop_ops.find_running_app('wechat', candidates), 'WeChat')

    def test_find_running_app_does_not_alias_unseen_name(self):
        candidates = ['WeChat', 'Safari']
        self.assertIsNone(desktop_ops.find_running_app('微信', candidates))
