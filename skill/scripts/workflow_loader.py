#!/usr/bin/env python3
"""
workflow_loader.py — Workflow discovery, parsing, and validation.

Discovers workflow files from:
  1. skill/workflows/          (bundled/community)
  2. ~/.claude/desktop-agent-ops/workflows/  (user local, takes precedence)

Workflow format: Markdown with YAML frontmatter (--- delimited).
"""
import json
import re
import sys
from pathlib import Path

from resolve_python import resolve_ops_home

# ── Directories ──────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
COMMUNITY_DIR = SKILL_DIR / 'workflows'

USER_DIR = resolve_ops_home() / 'workflows'

# ── JSON output helpers (match project convention) ───────────────────────────

def jprint(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def jerror(action, msg):
    jprint({'ok': False, 'action': action, 'error': msg})


# ── Minimal YAML-subset frontmatter parser (no PyYAML dependency) ────────────

def parse_frontmatter(text):
    """Split YAML frontmatter from Markdown body.

    Returns (meta_dict, body_str).
    Handles: scalars, simple lists ([a, b]), and nested key-value for parameters.
    """
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, text

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    if end_idx is None:
        return {}, text

    yaml_lines = lines[1:end_idx]
    body = '\n'.join(lines[end_idx + 1:])
    meta = _parse_yaml_subset(yaml_lines)
    return meta, body


def _parse_yaml_subset(lines):
    """Parse a flat/shallow YAML subset into a dict."""
    result = {}
    current_key = None
    current_list = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Detect indent level
        indent = len(line) - len(line.lstrip())

        # List item under a key (indented "- value" or "- name: value")
        if stripped.startswith('- ') and current_key is not None and indent >= 2:
            item_text = stripped[2:].strip()
            if ':' in item_text and not item_text.startswith('"'):
                # Nested dict item: "- name: foo"
                item_dict = {}
                parts = [item_text]
                # Peek ahead handled by collecting into current_list
                for kv in item_text.split(','):
                    kv = kv.strip()
                    if ':' in kv:
                        k, v = kv.split(':', 1)
                        item_dict[k.strip()] = _cast_value(v.strip())
                if current_list is None:
                    current_list = []
                current_list.append(item_dict)
                result[current_key] = current_list
            else:
                if current_list is None:
                    current_list = []
                current_list.append(_cast_value(item_text))
                result[current_key] = current_list
            continue

        # Top-level key: value
        if ':' in stripped:
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()
            current_key = key
            current_list = None

            if value:
                # Inline list: [a, b, c]
                if value.startswith('[') and value.endswith(']'):
                    items = [_cast_value(v.strip()) for v in value[1:-1].split(',') if v.strip()]
                    result[key] = items
                else:
                    result[key] = _cast_value(value)
            else:
                # Value may come as indented list items below
                result[key] = None

    return result


def _cast_value(v):
    """Cast a YAML scalar string to Python type."""
    if v in ('true', 'True', 'yes'):
        return True
    if v in ('false', 'False', 'no'):
        return False
    if v in ('null', 'None', '~', ''):
        return None
    # Strip quotes
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    # Try int/float
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


# ── Step parser ──────────────────────────────────────────────────────────────

_STEP_HEADING = re.compile(r'^##\s+Step\s+(\d+)\s*[:\uff1a]?\s*(.*)', re.IGNORECASE)
_VERIFY_HEADING = re.compile(r'^###\s+Verify', re.IGNORECASE)


def parse_steps(body):
    """Parse Markdown body into ordered steps.

    Returns list of:
      {number: int, title: str, commands: [str], verify: str|None}
    """
    lines = body.split('\n')
    steps = []
    current_step = None
    in_code_block = False
    in_verify = False
    code_lines = []
    verify_lines = []

    for line in lines:
        stripped = line.strip()

        # Step heading
        m = _STEP_HEADING.match(stripped)
        if m and not in_code_block:
            # Save previous step
            if current_step is not None:
                current_step['commands'] = _extract_commands(code_lines)
                current_step['verify'] = '\n'.join(verify_lines).strip() or None
                steps.append(current_step)
            current_step = {
                'number': int(m.group(1)),
                'title': m.group(2).strip(),
            }
            code_lines = []
            verify_lines = []
            in_verify = False
            continue

        if current_step is None:
            continue

        # Verify heading
        if _VERIFY_HEADING.match(stripped) and not in_code_block:
            in_verify = True
            continue

        # Code block boundaries
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
            else:
                in_code_block = True
            continue

        # Collect content
        if in_code_block and not in_verify:
            code_lines.append(line)
        elif in_verify and not in_code_block:
            verify_lines.append(line)

    # Save last step
    if current_step is not None:
        current_step['commands'] = _extract_commands(code_lines)
        current_step['verify'] = '\n'.join(verify_lines).strip() or None
        steps.append(current_step)

    return steps


def _extract_commands(code_lines):
    """Extract non-empty, non-comment command lines."""
    cmds = []
    for line in code_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            cmds.append(stripped)
    return cmds


# ── Workflow discovery ───────────────────────────────────────────────────────

def discover_workflows():
    """Scan community and user directories. Return list of workflow metadata.

    User workflows take precedence over community ones on name collision.
    """
    seen = {}

    # Community first (lower priority)
    if COMMUNITY_DIR.exists():
        for f in sorted(COMMUNITY_DIR.rglob('*.md')):
            _index_workflow(f, 'community', seen)

    # User overrides
    if USER_DIR.exists():
        for f in sorted(USER_DIR.rglob('*.md')):
            _index_workflow(f, 'local', seen)

    return list(seen.values())


def _index_workflow(path, source, seen):
    """Parse a workflow file and add to seen dict (keyed by name)."""
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return
    meta, _ = parse_frontmatter(text)
    name = meta.get('name') or path.stem
    seen[name] = {
        'name': name,
        'description': meta.get('description', ''),
        'version': meta.get('version', ''),
        'platform': meta.get('platform', []),
        'app': meta.get('app', ''),
        'tags': meta.get('tags', []),
        'author': meta.get('author', 'anonymous'),
        'source': source,
        'path': str(path),
    }


def load_workflow(name_or_path):
    """Load a workflow by name (searches both dirs) or by file path.

    Returns {meta, steps, path, raw} or None.
    """
    path = None

    # Direct path
    p = Path(name_or_path)
    if p.exists() and p.suffix == '.md':
        path = p
    else:
        # Search by name
        for d in [USER_DIR, COMMUNITY_DIR]:
            if not d.exists():
                continue
            for f in d.rglob('*.md'):
                try:
                    text = f.read_text(encoding='utf-8')
                except Exception:
                    continue
                meta, _ = parse_frontmatter(text)
                wf_name = meta.get('name') or f.stem
                if wf_name == name_or_path:
                    path = f
                    break
            if path:
                break

    if path is None:
        return None

    raw = path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(raw)
    steps = parse_steps(body)

    return {
        'meta': meta,
        'steps': steps,
        'path': str(path),
        'raw': raw,
    }


# ── Validation ───────────────────────────────────────────────────────────────

REQUIRED_META_FIELDS = ('name', 'description')


def validate_workflow(workflow):
    """Validate a loaded workflow dict. Returns list of error strings (empty = valid)."""
    errors = []
    meta = workflow.get('meta', {})
    steps = workflow.get('steps', [])

    # Required fields
    for field in REQUIRED_META_FIELDS:
        if not meta.get(field):
            errors.append(f'Missing required field: {field}')

    # Steps
    if not steps:
        errors.append('Workflow has no steps')
    else:
        numbers = [s['number'] for s in steps]
        if numbers != sorted(numbers):
            errors.append('Steps are not in ascending order')
        if len(numbers) != len(set(numbers)):
            errors.append('Duplicate step numbers found')
        for step in steps:
            if not step.get('commands'):
                errors.append(f"Step {step['number']} has no commands")

    # Parameter consistency: check declared params are referenced in commands
    params = meta.get('parameters', []) or []
    if isinstance(params, list):
        declared = {p['name'] for p in params if isinstance(p, dict) and 'name' in p}
        all_cmds = ' '.join(
            cmd for step in steps for cmd in step.get('commands', [])
        )
        for pname in declared:
            if f'${pname}' not in all_cmds and '${' + pname + '}' not in all_cmds:
                errors.append(f"Declared parameter '{pname}' is never referenced in steps")

    return errors


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(description='Workflow loader and validator')
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('discover', help='List all available workflows')

    p_load = sub.add_parser('load', help='Load and display a workflow')
    p_load.add_argument('--workflow', required=True, help='Workflow name or path')

    p_val = sub.add_parser('validate', help='Validate a workflow')
    p_val.add_argument('--workflow', required=True, help='Workflow name or path')

    args = ap.parse_args()

    if args.cmd == 'discover':
        workflows = discover_workflows()
        jprint({'ok': True, 'workflows': workflows, 'count': len(workflows)})

    elif args.cmd == 'load':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('load', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        jprint({
            'ok': True,
            'meta': wf['meta'],
            'steps': wf['steps'],
            'path': wf['path'],
        })

    elif args.cmd == 'validate':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('validate', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        errors = validate_workflow(wf)
        jprint({
            'ok': len(errors) == 0,
            'errors': errors,
            'workflow': wf['meta'].get('name', ''),
        })


if __name__ == '__main__':
    main()
