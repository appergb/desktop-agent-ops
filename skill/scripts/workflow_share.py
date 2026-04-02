#!/usr/bin/env python3
"""workflow_share.py — Share workflows to community via GitHub PR."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Sibling imports ─────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_loader import load_workflow, validate_workflow  # noqa: E402
from secret_scanner import scan_file                         # noqa: E402

# ── Constants ───────────────────────────────────────────────────────────────

UPSTREAM_REPO = 'appergb/desktop-agent-ops'
WORKFLOW_DEST = 'skill/workflows'


# ── JSON output helpers (match project convention) ──────────────────────────

def jprint(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def jerror(action, msg):
    jprint({'ok': False, 'action': action, 'error': msg})


# ── GitHub CLI check ────────────────────────────────────────────────────────

def check_gh_cli():
    """Run ``gh auth status`` and extract the authenticated username.

    Returns ``{"ok": bool, "user": str|None, "error": str|None}``.
    """
    try:
        result = subprocess.run(
            ['gh', 'auth', 'status'],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return {'ok': False, 'user': None, 'error': 'gh CLI not found'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'user': None, 'error': 'gh auth status timed out'}

    combined = result.stdout + result.stderr
    if result.returncode != 0:
        return {'ok': False, 'user': None, 'error': combined.strip()}

    # Parse username from output like "Logged in to github.com account USER ..."
    user = None
    for line in combined.splitlines():
        line_lower = line.lower()
        if 'logged in' in line_lower and 'account' in line_lower:
            parts = line.split('account')
            if len(parts) >= 2:
                user = parts[1].strip().split()[0].strip('()')
                break
    if not user:
        # Fallback: try "as USER" pattern
        for line in combined.splitlines():
            if ' as ' in line:
                user = line.split(' as ')[-1].strip().split()[0]
                break

    return {'ok': True, 'user': user, 'error': None}


# ── Preflight check ────────────────────────────────────────────────────────

def preflight_check(workflow_name):
    """Validate workflow and scan for secrets before sharing.

    Returns ``{"ok", "errors", "warnings", "gh_user", "workflow_meta",
    "workflow_path"}``.
    """
    errors = []
    warnings = []

    # Load workflow
    wf = load_workflow(workflow_name)
    if wf is None:
        return {
            'ok': False,
            'errors': [f'Workflow not found: {workflow_name}'],
            'warnings': [],
            'gh_user': None,
            'workflow_meta': None,
            'workflow_path': None,
        }

    # Validate structure
    validation_errors = validate_workflow(wf)
    if validation_errors:
        errors.extend(validation_errors)

    # Scan for secrets
    scan_result = scan_file(wf['path'])
    for finding in scan_result.get('findings', []):
        entry = f"{finding['type']}: line {finding['line']} ({finding['match_preview']})"
        if finding['severity'] == 'error':
            errors.append(entry)
        else:
            warnings.append(entry)

    # Check gh CLI
    gh = check_gh_cli()
    if not gh['ok']:
        errors.append(f"GitHub CLI: {gh['error']}")

    return {
        'ok': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'gh_user': gh.get('user'),
        'workflow_meta': wf['meta'],
        'workflow_path': wf['path'],
    }


# ── PR body generator ──────────────────────────────────────────────────────

def generate_pr_body(meta, scan_summary, gh_user):
    """Build a Markdown PR body with workflow details and check results."""
    name = meta.get('name', 'unknown')
    desc = meta.get('description', '')
    version = meta.get('version', '')
    platform = meta.get('platform', [])
    tags = meta.get('tags', [])

    if isinstance(platform, list):
        platform = ', '.join(str(p) for p in platform)
    if isinstance(tags, list):
        tags = ', '.join(str(t) for t in tags)

    body = (
        f"## Workflow: {name}\n\n"
        f"{desc}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Version** | {version} |\n"
        f"| **Platform** | {platform} |\n"
        f"| **Tags** | {tags} |\n"
        f"| **Submitted by** | @{gh_user} |\n\n"
        f"### Pre-upload checks\n\n"
        f"- Secret scan: {scan_summary}\n\n"
        f"### Usage example\n\n"
        f"```bash\n"
        f"python3 skill/scripts/workflow_loader.py load --workflow \"{name}\"\n"
        f"```\n"
    )
    return body


# ── Create PR ───────────────────────────────────────────────────────────────

def create_pr(workflow_path, meta, gh_user):
    """Fork, commit the workflow, and open a PR against upstream.

    Returns ``{"ok": bool, "pr_url": str|None, "workflow": str,
    "error": str|None}``.
    """
    name = meta.get('name', Path(workflow_path).stem)
    hash_input = f"{name}{gh_user}{workflow_path}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    branch = f"workflow/{name}-{short_hash}"

    tmpdir = tempfile.mkdtemp(prefix='workflow_share_')
    clone_dir = os.path.join(tmpdir, 'repo')

    try:
        # Fork + clone
        result = subprocess.run(
            ['gh', 'repo', 'fork', UPSTREAM_REPO,
             '--clone', '--clone-dir', clone_dir],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return {
                'ok': False, 'pr_url': None, 'workflow': name,
                'error': f'fork failed: {result.stderr.strip()}',
            }

        # Create branch
        result = subprocess.run(
            ['git', 'checkout', '-b', branch],
            capture_output=True, text=True, timeout=120,
            cwd=clone_dir,
        )
        if result.returncode != 0:
            return {
                'ok': False, 'pr_url': None, 'workflow': name,
                'error': f'branch creation failed: {result.stderr.strip()}',
            }

        # Copy workflow file
        dest_dir = os.path.join(clone_dir, WORKFLOW_DEST)
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, f'{name}.md')
        shutil.copy2(workflow_path, dest_file)

        # Stage + commit
        subprocess.run(
            ['git', 'add', os.path.join(WORKFLOW_DEST, f'{name}.md')],
            capture_output=True, text=True, timeout=120,
            cwd=clone_dir,
        )
        result = subprocess.run(
            ['git', 'commit', '-m', f'workflow: add {name}'],
            capture_output=True, text=True, timeout=120,
            cwd=clone_dir,
        )
        if result.returncode != 0:
            return {
                'ok': False, 'pr_url': None, 'workflow': name,
                'error': f'commit failed: {result.stderr.strip()}',
            }

        # Push
        result = subprocess.run(
            ['git', 'push', 'origin', branch],
            capture_output=True, text=True, timeout=120,
            cwd=clone_dir,
        )
        if result.returncode != 0:
            return {
                'ok': False, 'pr_url': None, 'workflow': name,
                'error': f'push failed: {result.stderr.strip()}',
            }

        # Create PR
        scan_result = scan_file(workflow_path)
        pr_body = generate_pr_body(meta, scan_result['summary'], gh_user)

        result = subprocess.run(
            ['gh', 'pr', 'create',
             '--repo', UPSTREAM_REPO,
             '--title', f'workflow: add {name}',
             '--body', pr_body],
            capture_output=True, text=True, timeout=120,
            cwd=clone_dir,
        )
        if result.returncode != 0:
            return {
                'ok': False, 'pr_url': None, 'workflow': name,
                'error': f'pr create failed: {result.stderr.strip()}',
            }

        pr_url = result.stdout.strip().splitlines()[-1]

        return {'ok': True, 'pr_url': pr_url, 'workflow': name, 'error': None}

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Share workflows to community via GitHub PR',
    )
    sub = ap.add_subparsers(dest='command', required=True)

    # check subcommand
    p_check = sub.add_parser('check', help='Preflight check only')
    p_check.add_argument('--workflow', required=True, help='Workflow name or path')

    # share subcommand
    p_share = sub.add_parser('share', help='Upload workflow via PR')
    p_share.add_argument('--workflow', required=True, help='Workflow name or path')
    p_share.add_argument('--force', action='store_true', help='Skip warnings')

    args = ap.parse_args()

    if args.command == 'check':
        result = preflight_check(args.workflow)
        jprint({
            'ok': result['ok'],
            'errors': result['errors'],
            'warnings': result['warnings'],
            'gh_user': result['gh_user'],
            'workflow': result['workflow_meta'].get('name', '') if result['workflow_meta'] else None,
        })
        sys.exit(0 if result['ok'] else 1)

    elif args.command == 'share':
        result = preflight_check(args.workflow)

        # Errors always block
        if result['errors']:
            jerror('share', 'Preflight errors must be resolved before sharing')
            jprint({
                'ok': False,
                'errors': result['errors'],
                'warnings': result['warnings'],
            })
            sys.exit(1)

        # Warnings block unless --force
        if result['warnings'] and not args.force:
            jerror('share', 'Warnings found; use --force to skip')
            jprint({
                'ok': False,
                'errors': [],
                'warnings': result['warnings'],
            })
            sys.exit(1)

        # Create PR
        pr_result = create_pr(
            result['workflow_path'],
            result['workflow_meta'],
            result['gh_user'],
        )
        jprint(pr_result)
        sys.exit(0 if pr_result['ok'] else 1)


if __name__ == '__main__':
    main()
