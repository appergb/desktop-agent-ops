#!/usr/bin/env python3
import argparse
import json
import time

from task_paths import resolve_task_dir


def path_for(task_id):
    return resolve_task_dir(task_id)


def _load_state(task_id):
    """Load state.json for a task. Returns (path, state_dict) or raises."""
    p = path_for(task_id) / 'state.json'
    if not p.exists():
        return None, None
    return p, json.loads(p.read_text())


def _save_state(state_path, state):
    """Write state dict back to state.json."""
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_init(task_id):
    p = path_for(task_id)
    p.mkdir(parents=True, exist_ok=True)
    state = {
        'task_id': p.name,
        'started_at': int(time.time()),
        'last_action': None,
        'last_capture': None,
        'last_target': None,
        'step_count': 0,
        'current_step_retries': 0,
        'max_retries': 3,
        'last_action_result': None,
        'task_result': '',
        'total_actions': 0,
        'error_log': [],
    }
    (p / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(json.dumps({'ok': True, 'task_dir': str(p), 'state_file': str(p / 'state.json')}, ensure_ascii=False))


def cmd_show(task_id):
    p = path_for(task_id) / 'state.json'
    if not p.exists():
        print(json.dumps({'ok': False, 'error': 'state_not_found'}, ensure_ascii=False))
        return
    print(p.read_text())


def cmd_step(task_id):
    state_path, state = _load_state(task_id)
    if state is None:
        print(json.dumps({'ok': False, 'error': 'state_not_found'}, ensure_ascii=False))
        return
    state['step_count'] += 1
    state['current_step_retries'] = 0
    state['total_actions'] += 1
    _save_state(state_path, state)
    print(json.dumps({
        'ok': True,
        'step_count': state['step_count'],
        'total_actions': state['total_actions'],
    }, ensure_ascii=False))


def cmd_retry(task_id):
    state_path, state = _load_state(task_id)
    if state is None:
        print(json.dumps({'ok': False, 'error': 'state_not_found'}, ensure_ascii=False))
        return
    state['current_step_retries'] += 1
    if state['current_step_retries'] > state['max_retries']:
        _save_state(state_path, state)
        print(json.dumps({
            'ok': False,
            'error': 'max_retries_exceeded',
            'current_step_retries': state['current_step_retries'],
            'max_retries': state['max_retries'],
        }, ensure_ascii=False))
        return
    _save_state(state_path, state)
    print(json.dumps({
        'ok': True,
        'current_step_retries': state['current_step_retries'],
        'max_retries': state['max_retries'],
    }, ensure_ascii=False))


def cmd_finalize(task_id, result):
    state_path, state = _load_state(task_id)
    if state is None:
        print(json.dumps({'ok': False, 'error': 'state_not_found'}, ensure_ascii=False))
        return
    state['task_result'] = result
    _save_state(state_path, state)
    # Write summary.json alongside state.json
    summary = {
        'task_id': state['task_id'],
        'started_at': state['started_at'],
        'finished_at': int(time.time()),
        'task_result': result,
        'step_count': state['step_count'],
        'total_actions': state['total_actions'],
        'error_log': state['error_log'],
    }
    summary_path = state_path.parent / 'summary.json'
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({
        'ok': True,
        'summary_file': str(summary_path),
        'task_result': result,
    }, ensure_ascii=False))


def cmd_record_error(task_id, error):
    state_path, state = _load_state(task_id)
    if state is None:
        print(json.dumps({'ok': False, 'error': 'state_not_found'}, ensure_ascii=False))
        return
    state['error_log'].append({
        'timestamp': int(time.time()),
        'error': error,
        'step': state['step_count'],
    })
    _save_state(state_path, state)
    print(json.dumps({
        'ok': True,
        'error_count': len(state['error_log']),
    }, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    i = sub.add_parser('init', aliases=['create'])
    i.add_argument('--task-id', '--name', required=True, dest='task_id')

    s = sub.add_parser('show', aliases=['get'])
    s.add_argument('--task-id', '--name', required=True, dest='task_id')

    st = sub.add_parser('step')
    st.add_argument('--task-id', '--name', required=True, dest='task_id')

    rt = sub.add_parser('retry')
    rt.add_argument('--task-id', '--name', required=True, dest='task_id')

    fn = sub.add_parser('finalize')
    fn.add_argument('--task-id', '--name', required=True, dest='task_id')
    fn.add_argument('--result', required=True)

    re = sub.add_parser('record-error')
    re.add_argument('--task-id', '--name', required=True, dest='task_id')
    re.add_argument('--error', required=True)

    args = ap.parse_args()

    if args.cmd in ('init', 'create'):
        cmd_init(args.task_id)
    elif args.cmd in ('show', 'get'):
        cmd_show(args.task_id)
    elif args.cmd == 'step':
        cmd_step(args.task_id)
    elif args.cmd == 'retry':
        cmd_retry(args.task_id)
    elif args.cmd == 'finalize':
        cmd_finalize(args.task_id, args.result)
    elif args.cmd == 'record-error':
        cmd_record_error(args.task_id, args.error)


if __name__ == '__main__':
    main()
