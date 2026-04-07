#!/usr/bin/env python3
"""
workflow_runner.py — Workflow execution engine.

Loads workflows via workflow_loader.py and executes them step by step.
The AI Agent is expected to call `preview` first, review commands for safety,
then call `run`. This runner is a dumb executor — security is the Agent's job.
"""
import argparse
import json
import sys
from pathlib import Path

# ── Resolve imports from same directory ─────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_loader import (
    discover_workflows,
    load_workflow,
    validate_workflow,
)
from workflow_executor import run_workflow
from workflow_runtime import (
    apply_defaults,
    check_required_params,
    flatten_result_fields,
    parse_params,
    preview_commands,
    substitute_vars,
)

# ── JSON output helpers (match project convention) ──────────────────────────

def jprint(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def jerror(action, msg):
    jprint({'ok': False, 'action': action, 'error': msg})


# ── Default Python interpreter ──────────────────────────────────────────────

def _default_py():
    import os
    return os.environ.get('PYTHON', sys.executable)


# Backward-compatible aliases for tests and external imports.
_parse_params = parse_params
_check_required_params = check_required_params
_apply_defaults = apply_defaults
_flatten_step_result = flatten_result_fields


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Workflow execution engine')
    ap.add_argument('--py', default=None, help='Python interpreter path')
    sub = ap.add_subparsers(dest='cmd', required=True)

    # list
    sub.add_parser('list', help='List all available workflows')

    # show
    p_show = sub.add_parser('show', help='Show workflow details')
    p_show.add_argument('--workflow', required=True, help='Workflow name or path')

    # validate
    p_val = sub.add_parser('validate', help='Validate a workflow')
    p_val.add_argument('--workflow', required=True, help='Workflow name or path')

    # preview
    p_prev = sub.add_parser('preview', help='Preview resolved commands (no execution)')
    p_prev.add_argument('--workflow', required=True, help='Workflow name or path')
    p_prev.add_argument('--param', action='append', default=[], metavar='key=value',
                        help='Parameter (repeatable)')

    # run
    p_run = sub.add_parser('run', help='Execute a workflow')
    p_run.add_argument('--workflow', required=True, help='Workflow name or path')
    p_run.add_argument('--param', action='append', default=[], metavar='key=value',
                       help='Parameter (repeatable)')

    args = ap.parse_args()
    py = args.py or _default_py()

    # ── list ────────────────────────────────────────────────────────────────
    if args.cmd == 'list':
        workflows = discover_workflows()
        jprint({'ok': True, 'workflows': workflows, 'count': len(workflows)})
        return

    # ── show ────────────────────────────────────────────────────────────────
    if args.cmd == 'show':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('show', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        meta = wf['meta']
        jprint({
            'ok': True,
            'name': meta.get('name', ''),
            'description': meta.get('description', ''),
            'parameters': meta.get('parameters', []),
            'app': meta.get('app', ''),
            'platform': meta.get('platform', []),
            'steps': [
                {'number': s['number'], 'title': s['title'],
                 'command_count': len(s['commands']), 'has_verify': s.get('verify') is not None}
                for s in wf['steps']
            ],
            'path': wf['path'],
        })
        return

    # ── validate ────────────────────────────────────────────────────────────
    if args.cmd == 'validate':
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
        return

    # ── preview ─────────────────────────────────────────────────────────────
    if args.cmd == 'preview':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('preview', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        params = parse_params(args.param)
        params = apply_defaults(wf['meta'], params)
        missing = check_required_params(wf['meta'], params)
        if missing:
            jerror('preview', f'Missing required parameters: {", ".join(missing)}')
            sys.exit(1)
        result = preview_commands(wf, params, py, scripts_dir=SCRIPTS_DIR, skill_dir=SKILL_DIR)
        jprint(result)
        return

    # ── run ──────────────────────────────────────────────────────────────────
    if args.cmd == 'run':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('run', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        params = parse_params(args.param)
        params = apply_defaults(wf['meta'], params)
        missing = check_required_params(wf['meta'], params)
        if missing:
            jerror('run', f'Missing required parameters: {", ".join(missing)}')
            sys.exit(1)
        result = run_workflow(wf, params, py, SCRIPTS_DIR, SKILL_DIR)
        jprint(result)
        return


if __name__ == '__main__':
    main()
