#!/usr/bin/env python3
"""
workflow_runner.py — Workflow execution engine.

Loads workflows via workflow_loader.py and executes them step by step.
The AI Agent is expected to call `preview` first, review commands for safety,
then call `run`. This runner is a dumb executor — security is the Agent's job.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ── Resolve imports from same directory ─────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_loader import (
    discover_workflows,
    load_workflow,
    validate_workflow,
)

# ── JSON output helpers (match project convention) ──────────────────────────

def jprint(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def jerror(action, msg):
    jprint({'ok': False, 'action': action, 'error': msg})


# ── Default Python interpreter ──────────────────────────────────────────────

def _default_py():
    return os.environ.get('PYTHON', sys.executable)


# ── Parameter parsing ───────────────────────────────────────────────────────

def _parse_params(raw_params):
    """Parse ['key=value', ...] into a dict."""
    params = {}
    if not raw_params:
        return params
    for item in raw_params:
        if '=' not in item:
            continue
        key, _, value = item.partition('=')
        params[key.strip()] = value.strip()
    return params


def _check_required_params(meta, params):
    """Return list of missing required parameter names."""
    declared = meta.get('parameters') or []
    missing = []
    for p in declared:
        if not isinstance(p, dict):
            continue
        if p.get('required', False) and p['name'] not in params:
            if p.get('default') is None:
                missing.append(p['name'])
    return missing


def _apply_defaults(meta, params):
    """Return a new params dict with defaults filled in for missing keys."""
    result = dict(params)
    declared = meta.get('parameters') or []
    for p in declared:
        if not isinstance(p, dict):
            continue
        name = p.get('name', '')
        if name and name not in result and p.get('default') is not None:
            result[name] = str(p['default'])
    return result


# ── Variable substitution ──────────────────────────────────────────────────

_RESULT_VAR = re.compile(r'\$RESULT_(\w+)')


def substitute_vars(text, params, prev_result, app, py):
    """Replace workflow variables in a command string.

    Variables:
      $param_name    — user-supplied parameter
      $app           — meta.app field
      $PY            — Python interpreter path
      $RESULT_field  — field from previous step's JSON output
      $ARGUMENTS     — all params joined as "key=value" pairs
    """
    result = text

    # $PY
    result = result.replace('$PY', py)

    # $app
    if app:
        result = result.replace('$app', app)

    # $ARGUMENTS
    arguments = ' '.join(f'{k}={v}' for k, v in sorted(params.items()))
    result = result.replace('$ARGUMENTS', arguments)

    # $RESULT_field
    if prev_result and isinstance(prev_result, dict):
        def _replace_result(m):
            field = m.group(1)
            return str(prev_result.get(field, m.group(0)))
        result = _RESULT_VAR.sub(_replace_result, result)

    # $param_name — do this last so $RESULT_ and $ARGUMENTS aren't clobbered
    for key, value in params.items():
        result = result.replace(f'${key}', value)

    return result


# ── Preview (no execution) ─────────────────────────────────────────────────

def preview_commands(workflow, params, py):
    """Substitute variables in every step and return the resolved commands."""
    meta = workflow['meta']
    app = meta.get('app', '')
    prev_result = {}
    preview_steps = []

    for step in workflow['steps']:
        resolved = []
        for cmd in step['commands']:
            resolved.append(substitute_vars(cmd, params, prev_result, app, py))
        preview_steps.append({
            'number': step['number'],
            'title': step['title'],
            'commands': resolved,
        })

    return {'ok': True, 'steps': preview_steps}


# ── Step execution ──────────────────────────────────────────────────────────

def execute_step(step, params, prev_result, app, py, task_dir):
    """Execute one step's commands sequentially via subprocess.

    Returns {ok, step, results, error}.
    """
    results = []
    step_num = step['number']

    for cmd_template in step['commands']:
        cmd = substitute_vars(cmd_template, params, prev_result, app, py)

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(SCRIPTS_DIR),
                env={**os.environ, 'TASK_DIR': task_dir} if task_dir else None,
            )
        except subprocess.TimeoutExpired:
            return {
                'ok': False,
                'step': step_num,
                'results': results,
                'error': f'Command timed out (60s): {cmd}',
            }

        # Try to parse JSON stdout from the command
        stdout = proc.stdout.strip()
        parsed = None
        if stdout:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                parsed = None

        entry = {
            'command': cmd,
            'returncode': proc.returncode,
            'stdout': stdout,
            'stderr': proc.stderr.strip(),
            'parsed': parsed,
        }
        results.append(entry)

        # Update prev_result if we got valid JSON
        if parsed and isinstance(parsed, dict):
            prev_result.update(parsed)

        # Check for failure
        if proc.returncode != 0:
            return {
                'ok': False,
                'step': step_num,
                'results': results,
                'error': f'Command failed (rc={proc.returncode}): {cmd}',
            }

        # Check JSON-level ok flag
        if parsed and isinstance(parsed, dict) and parsed.get('ok') is False:
            return {
                'ok': False,
                'step': step_num,
                'results': results,
                'error': parsed.get('error', f'Step {step_num} command reported failure'),
            }

    return {'ok': True, 'step': step_num, 'results': results, 'error': None}


# ── Full workflow execution ─────────────────────────────────────────────────

MAX_RETRIES = 2


def run_workflow(workflow, params, py):
    """Execute the full workflow with task context management and retry logic."""
    meta = workflow['meta']
    name = meta.get('name', 'unnamed')
    app = meta.get('app', '')
    steps = workflow['steps']
    task_id = f'wf-{name}-{int(time.time())}'

    # Init task context
    init_result = subprocess.run(
        [py, str(SCRIPTS_DIR / 'task_context.py'), 'init', '--task-id', task_id],
        capture_output=True, text=True, timeout=15,
    )
    task_dir = ''
    if init_result.returncode == 0:
        try:
            init_data = json.loads(init_result.stdout.strip())
            task_dir = init_data.get('task_dir', '')
        except json.JSONDecodeError:
            pass

    prev_result = {}
    steps_completed = 0
    last_error = None

    for step in steps:
        success = False

        for attempt in range(1 + MAX_RETRIES):
            step_result = execute_step(step, params, prev_result, app, py, task_dir)

            if step_result['ok']:
                steps_completed += 1
                success = True
                break

            last_error = step_result.get('error')
            if attempt < MAX_RETRIES:
                time.sleep(1)

        if not success:
            break

    # Cleanup task context
    subprocess.run(
        [py, str(SCRIPTS_DIR / 'cleanup_task.py'), '--task-id', task_id],
        capture_output=True, text=True, timeout=15,
    )

    all_ok = steps_completed == len(steps)
    summary = {
        'ok': all_ok,
        'workflow': name,
        'steps_completed': steps_completed,
        'steps_total': len(steps),
        'task_id': task_id,
    }
    if not all_ok and last_error:
        summary['error'] = last_error

    return summary


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
        params = _parse_params(args.param)
        params = _apply_defaults(wf['meta'], params)
        missing = _check_required_params(wf['meta'], params)
        if missing:
            jerror('preview', f'Missing required parameters: {", ".join(missing)}')
            sys.exit(1)
        result = preview_commands(wf, params, py)
        jprint(result)
        return

    # ── run ──────────────────────────────────────────────────────────────────
    if args.cmd == 'run':
        wf = load_workflow(args.workflow)
        if wf is None:
            jerror('run', f'Workflow not found: {args.workflow}')
            sys.exit(1)
        params = _parse_params(args.param)
        params = _apply_defaults(wf['meta'], params)
        missing = _check_required_params(wf['meta'], params)
        if missing:
            jerror('run', f'Missing required parameters: {", ".join(missing)}')
            sys.exit(1)
        result = run_workflow(wf, params, py)
        jprint(result)
        return


if __name__ == '__main__':
    main()
