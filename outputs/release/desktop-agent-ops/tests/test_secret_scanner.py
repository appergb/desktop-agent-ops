import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skill' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from secret_scanner import scan_text, shannon_entropy  # noqa: E402


class ScanTextErrorSeverityTests(unittest.TestCase):
    """Patterns that should produce severity='error' findings."""

    def test_aws_access_key_detected(self):
        findings = scan_text('AKIA1234567890ABCDEF')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('AWS Access Key', names)

    def test_github_token_detected(self):
        token = 'ghp_abcdefghijklmnopqrstuvwxyz1234567890'
        findings = scan_text(token)
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('GitHub Token', names)

    def test_generic_api_key_detected(self):
        findings = scan_text('api_key = "mysecretvalue123"')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('Generic API Key', names)

    def test_generic_password_detected(self):
        findings = scan_text('password: supersecret123')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('Generic Secret', names)

    def test_private_key_block_detected(self):
        findings = scan_text('-----BEGIN RSA PRIVATE KEY-----')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('Private Key', names)

    def test_connection_string_detected(self):
        findings = scan_text('postgres://user:pass@host/db')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('Connection String', names)

    def test_bearer_token_detected(self):
        findings = scan_text('Bearer eyJhbGciOiJIUzI1NiJ9.xxx')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertTrue(len(errors) >= 1)
        names = [f['type'] for f in errors]
        self.assertIn('Bearer Token', names)


class ScanTextWarningSeverityTests(unittest.TestCase):
    """Patterns that should produce severity='warning' findings."""

    def test_unix_absolute_path_warning(self):
        findings = scan_text('/Users/john/Documents/')
        warnings = [f for f in findings if f['severity'] == 'warning']
        self.assertTrue(len(warnings) >= 1)
        names = [f['type'] for f in warnings]
        self.assertIn('Absolute Path (Unix)', names)

    def test_windows_path_warning(self):
        findings = scan_text('C:\\Users\\john\\Desktop\\')
        warnings = [f for f in findings if f['severity'] == 'warning']
        self.assertTrue(len(warnings) >= 1)
        names = [f['type'] for f in warnings]
        self.assertIn('Absolute Path (Win)', names)

    def test_email_warning(self):
        findings = scan_text('user@example.com')
        warnings = [f for f in findings if f['severity'] == 'warning']
        self.assertTrue(len(warnings) >= 1)
        names = [f['type'] for f in warnings]
        self.assertIn('Email', names)

    def test_internal_ip_warning(self):
        findings = scan_text('192.168.1.100')
        warnings = [f for f in findings if f['severity'] == 'warning']
        self.assertTrue(len(warnings) >= 1)
        names = [f['type'] for f in warnings]
        self.assertIn('Internal IP', names)

    def test_loopback_not_flagged_as_internal_ip(self):
        findings = scan_text('127.0.0.1')
        ip_findings = [f for f in findings if f['type'] == 'Internal IP']
        self.assertEqual(len(ip_findings), 0)

    def test_internal_hostname_warning(self):
        findings = scan_text('server.internal')
        warnings = [f for f in findings if f['severity'] == 'warning']
        self.assertTrue(len(warnings) >= 1)
        names = [f['type'] for f in warnings]
        self.assertIn('Internal Hostname', names)


class ScanTextCleanInputTests(unittest.TestCase):
    """Benign text should produce no findings."""

    def test_clean_text_no_findings(self):
        findings = scan_text('This is a normal workflow')
        self.assertEqual(len(findings), 0)


class UploadDecisionTests(unittest.TestCase):
    """Simulate can_upload logic: errors block, warnings allow."""

    @staticmethod
    def _can_upload(findings):
        return sum(1 for f in findings if f['severity'] == 'error') == 0

    def test_error_blocks_upload(self):
        findings = scan_text('AKIA1234567890ABCDEF')
        self.assertFalse(self._can_upload(findings))

    def test_warning_only_allows_upload(self):
        findings = scan_text('/Users/john/Documents/')
        errors = [f for f in findings if f['severity'] == 'error']
        self.assertEqual(len(errors), 0)
        self.assertTrue(self._can_upload(findings))


class ShannonEntropyTests(unittest.TestCase):
    """Shannon entropy utility checks."""

    def test_low_entropy_repeated_chars(self):
        self.assertLess(shannon_entropy('aaaa'), 1.0)

    def test_high_entropy_mixed_chars(self):
        self.assertGreater(shannon_entropy('aB3$xY9!kL2@'), 3.0)

    def test_empty_string_zero_entropy(self):
        self.assertEqual(shannon_entropy(''), 0.0)


class MaskingTests(unittest.TestCase):
    """Ensure match_preview does not leak the full secret."""

    def test_aws_key_masked(self):
        findings = scan_text('AKIA1234567890ABCDEF')
        aws = [f for f in findings if f['type'] == 'AWS Access Key'][0]
        preview = aws['match_preview']
        self.assertNotEqual(preview, 'AKIA1234567890ABCDEF')
        self.assertTrue(preview.startswith('AKIA'))
        self.assertIn('***', preview)

    def test_github_token_masked(self):
        token = 'ghp_abcdefghijklmnopqrstuvwxyz1234567890'
        findings = scan_text(token)
        gh = [f for f in findings if f['type'] == 'GitHub Token'][0]
        self.assertNotEqual(gh['match_preview'], token)
        self.assertIn('***', gh['match_preview'])


if __name__ == '__main__':
    unittest.main()
