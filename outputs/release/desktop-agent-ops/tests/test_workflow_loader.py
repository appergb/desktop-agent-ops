import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skill' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_loader import parse_frontmatter, parse_steps, validate_workflow  # noqa: E402


def _make_wf(meta=None, steps=None):
    return {'meta': meta or {}, 'steps': steps or [], 'path': '/tmp/t.md', 'raw': ''}


# ── parse_frontmatter ───────────────────────────────────────────────────────


class ParseFrontmatterTests(unittest.TestCase):

    def test_basic_key_value(self):
        text = '---\nname: demo\ndescription: A demo workflow\n---\nBody here'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta['name'], 'demo')
        self.assertEqual(meta['description'], 'A demo workflow')
        self.assertIn('Body here', body)

    def test_inline_list(self):
        text = '---\ntags: [ui, click, scroll]\n---\n'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta['tags'], ['ui', 'click', 'scroll'])

    def test_parameters_with_nested_dicts(self):
        text = (
            '---\nname: p\nparameters:\n'
            '  - name: url, default: https://example.com\n'
            '  - name: retries, default: 3\n'
            '---\n'
        )
        meta, _ = parse_frontmatter(text)
        params = meta['parameters']
        self.assertIsInstance(params, list)
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]['name'], 'url')
        self.assertEqual(params[1]['name'], 'retries')
        self.assertEqual(params[1]['default'], 3)

    def test_no_frontmatter(self):
        text = '# Just a heading\nSome text'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_value_casting_bool_int_quoted(self):
        text = '---\nenabled: true\ncount: 42\nlabel: "hello world"\n---\n'
        meta, _ = parse_frontmatter(text)
        self.assertIs(meta['enabled'], True)
        self.assertEqual(meta['count'], 42)
        self.assertEqual(meta['label'], 'hello world')


# ── parse_steps ─────────────────────────────────────────────────────────────


class ParseStepsTests(unittest.TestCase):

    def test_basic_two_steps(self):
        body = (
            '## Step 1: Open app\n'
            '```bash\nopen -a Safari\n```\n'
            '## Step 2: Navigate\n'
            '```bash\ncurl https://example.com\n```\n'
        )
        steps = parse_steps(body)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]['number'], 1)
        self.assertEqual(steps[0]['title'], 'Open app')
        self.assertEqual(steps[0]['commands'], ['open -a Safari'])
        self.assertEqual(steps[1]['number'], 2)

    def test_multiple_commands_per_step(self):
        body = (
            '## Step 1: Setup\n'
            '```bash\ncommand_a\ncommand_b\ncommand_c\n```\n'
        )
        steps = parse_steps(body)
        self.assertEqual(len(steps[0]['commands']), 3)

    def test_step_without_verify(self):
        body = '## Step 1: Solo\n```bash\necho hi\n```\n'
        steps = parse_steps(body)
        self.assertIsNone(steps[0]['verify'])

    def test_step_with_verify(self):
        body = (
            '## Step 1: Do\n'
            '```bash\necho hi\n```\n'
            '### Verify\n'
            'Check that hi was printed.\n'
        )
        steps = parse_steps(body)
        self.assertEqual(steps[0]['verify'], 'Check that hi was printed.')

    def test_empty_body(self):
        steps = parse_steps('')
        self.assertEqual(steps, [])


# ── validate_workflow ───────────────────────────────────────────────────────


class ValidateWorkflowTests(unittest.TestCase):

    def test_missing_name(self):
        wf = _make_wf(meta={'description': 'ok'}, steps=[{'number': 1, 'commands': ['x']}])
        errors = validate_workflow(wf)
        self.assertTrue(any('name' in e for e in errors))

    def test_missing_description(self):
        wf = _make_wf(meta={'name': 'ok'}, steps=[{'number': 1, 'commands': ['x']}])
        errors = validate_workflow(wf)
        self.assertTrue(any('description' in e for e in errors))

    def test_no_steps(self):
        wf = _make_wf(meta={'name': 'n', 'description': 'd'}, steps=[])
        errors = validate_workflow(wf)
        self.assertIn('Workflow has no steps', errors)

    def test_step_with_no_commands(self):
        wf = _make_wf(
            meta={'name': 'n', 'description': 'd'},
            steps=[{'number': 1, 'commands': []}],
        )
        errors = validate_workflow(wf)
        self.assertTrue(any('no commands' in e for e in errors))

    def test_valid_workflow(self):
        wf = _make_wf(
            meta={'name': 'n', 'description': 'd'},
            steps=[{'number': 1, 'commands': ['echo ok']}],
        )
        errors = validate_workflow(wf)
        self.assertEqual(errors, [])

    def test_unused_parameter_warning(self):
        wf = _make_wf(
            meta={
                'name': 'n',
                'description': 'd',
                'parameters': [{'name': 'ghost'}],
            },
            steps=[{'number': 1, 'commands': ['echo ok']}],
        )
        errors = validate_workflow(wf)
        self.assertTrue(any('ghost' in e and 'never referenced' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
