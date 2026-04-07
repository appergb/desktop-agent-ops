import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skill" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from input_runtime import (  # noqa: E402
    escape_applescript_string,
    has_non_ascii,
    macos_keycode,
    normalize_press_key,
    pyautogui_key_name,
)


class InputRuntimeTests(unittest.TestCase):
    def test_escape_applescript_string_handles_quotes_and_backslashes(self):
        escaped = escape_applescript_string('Finder "Preview" \\ Test')
        self.assertEqual(escaped, 'Finder \\\"Preview\\\" \\\\ Test')

    def test_normalize_press_key_maps_enter_aliases_only(self):
        self.assertEqual(normalize_press_key("enter"), "return")
        self.assertEqual(normalize_press_key("return"), "return")
        self.assertEqual(normalize_press_key("newline"), "newline")

    def test_pyautogui_key_name_maps_return_to_enter(self):
        self.assertEqual(pyautogui_key_name("return"), "enter")

    def test_macos_keycode_returns_virtual_key_code(self):
        self.assertEqual(macos_keycode("return"), 36)

    def test_has_non_ascii_detects_cjk_text(self):
        self.assertFalse(has_non_ascii("hello"))
        self.assertTrue(has_non_ascii("你好"))


if __name__ == "__main__":
    unittest.main()
