#!/usr/bin/env python3
"""
secret_scanner.py — Pre-upload sensitive information scanner.

Scans workflow files for hardcoded secrets, personal paths, and other
sensitive content before uploading to cloud.

Usage:
    python3 secret_scanner.py scan --file /path/to/workflow.md
    python3 secret_scanner.py scan --text "inline content"
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path


# ── JSON output helpers (match project convention) ───────────────────────────

def jprint(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def jerror(action, msg):
    jprint({'ok': False, 'action': action, 'error': msg})


# ── Detection patterns ───────────────────────────────────────────────────────
#
# Each entry: (name, compiled_regex, severity)
# severity is "error" for secrets, "warning" for PII / paths.

PATTERNS = [
    (
        'AWS Access Key',
        re.compile(r'AKIA[0-9A-Z]{16}'),
        'error',
    ),
    (
        'AWS Secret',
        re.compile(r'(?i)aws.?secret.?access.?key\s*[=:]\s*\S+'),
        'error',
    ),
    (
        'GitHub Token',
        re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}'),
        'error',
    ),
    (
        'Generic API Key',
        re.compile(r'(?i)(api.?key|apikey|api.?secret)\s*[=:]\s*["\']?\S{8,}'),
        'error',
    ),
    (
        'Bearer Token',
        re.compile(r'(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*'),
        'error',
    ),
    (
        'Generic Secret',
        re.compile(
            r'(?i)(token|secret|password|passwd|pwd)\s*[=:]\s*["\']?\S{8,}'
        ),
        'error',
    ),
    (
        'Private Key',
        re.compile(
            r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----'
        ),
        'error',
    ),
    (
        'Connection String',
        re.compile(r'(?i)(mongodb|postgres|mysql|redis)://\S+'),
        'error',
    ),
    (
        'Absolute Path (Unix)',
        re.compile(r'/(?:Users|home)/[A-Za-z0-9._-]+/'),
        'warning',
    ),
    (
        'Absolute Path (Win)',
        re.compile(r'[A-Z]:\\Users\\[A-Za-z0-9._-]+\\'),
        'warning',
    ),
    (
        'Email',
        re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
        'warning',
    ),
    (
        'Internal IP',
        re.compile(
            r'\b(?:'
            r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            r'|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'
            r'|192\.168\.\d{1,3}\.\d{1,3}'
            r')\b'
        ),
        'warning',
    ),
    (
        'Internal Hostname',
        re.compile(r'(?i)\b[a-z0-9-]+\.(internal|local|corp|intranet)\b'),
        'warning',
    ),
]


# ── Entropy detection ────────────────────────────────────────────────────────

def shannon_entropy(s):
    """Calculate Shannon entropy of a string in bits."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


_HIGH_ENTROPY_RE = re.compile(r'[A-Za-z0-9+/=_\-]{20,}')


def find_high_entropy_strings(text, min_length=20, min_entropy=4.0):
    """Return list of (match_str, entropy, start, end) for suspicious tokens."""
    results = []
    for m in _HIGH_ENTROPY_RE.finditer(text):
        token = m.group()
        if len(token) < min_length:
            continue
        ent = shannon_entropy(token)
        if ent >= min_entropy:
            results.append((token, ent, m.start(), m.end()))
    return results


# ── Masking helper ───────────────────────────────────────────────────────────

def _mask(value):
    """Show first 4 chars then mask the rest."""
    if len(value) <= 4:
        return value[:2] + '***'
    return value[:4] + '***'


# ── Core scanning ────────────────────────────────────────────────────────────

def scan_text(text):
    """Scan text for sensitive patterns and high-entropy strings.

    Returns a list of finding dicts, each with keys:
        type, pattern, line, column, match_preview, severity
    """
    findings = []
    lines = text.split('\n')

    for line_num, line in enumerate(lines, start=1):
        for name, regex, severity in PATTERNS:
            for m in regex.finditer(line):
                findings.append({
                    'type': name,
                    'pattern': regex.pattern,
                    'line': line_num,
                    'column': m.start() + 1,
                    'match_preview': _mask(m.group()),
                    'severity': severity,
                })

        for token, ent, start, _end in find_high_entropy_strings(line):
            findings.append({
                'type': 'High Entropy String',
                'pattern': f'entropy={ent:.2f}',
                'line': line_num,
                'column': start + 1,
                'match_preview': _mask(token),
                'severity': 'warning',
            })

    return findings


def scan_file(path):
    """Scan a file and return a structured result dict.

    Keys: ok, findings, summary, can_upload
    """
    file_path = Path(path)
    if not file_path.is_file():
        return {
            'ok': False,
            'findings': [],
            'summary': f'file not found: {path}',
            'can_upload': False,
        }

    try:
        text = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        return {
            'ok': False,
            'findings': [],
            'summary': f'read error: {exc}',
            'can_upload': False,
        }

    findings = scan_text(text)
    errors = sum(1 for f in findings if f['severity'] == 'error')
    warnings = sum(1 for f in findings if f['severity'] == 'warning')
    can_upload = errors == 0

    return {
        'ok': True,
        'findings': findings,
        'summary': f'{errors} errors, {warnings} warnings',
        'can_upload': can_upload,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pre-upload sensitive information scanner',
    )
    sub = parser.add_subparsers(dest='command')

    scan_parser = sub.add_parser('scan', help='Scan for sensitive content')
    group = scan_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', type=str, help='Path to file to scan')
    group.add_argument('--text', type=str, help='Inline text to scan')

    args = parser.parse_args()

    if args.command != 'scan':
        jerror('scan', 'usage: secret_scanner.py scan --file PATH | --text TEXT')
        sys.exit(1)

    if args.file:
        result = scan_file(args.file)
    else:
        findings = scan_text(args.text)
        errors = sum(1 for f in findings if f['severity'] == 'error')
        warnings = sum(1 for f in findings if f['severity'] == 'warning')
        result = {
            'ok': True,
            'findings': findings,
            'summary': f'{errors} errors, {warnings} warnings',
            'can_upload': errors == 0,
        }

    jprint(result)
    sys.exit(0 if result.get('can_upload', False) else 1)


if __name__ == '__main__':
    main()
