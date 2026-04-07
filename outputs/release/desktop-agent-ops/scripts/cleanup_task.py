#!/usr/bin/env python3
import argparse
import json
import shutil

from resolve_python import resolve_ops_home
from task_paths import resolve_task_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-id', required=True)
    args = ap.parse_args()
    target = resolve_task_dir(args.task_id)
    existed = target.exists()

    summary_archived = False
    if existed:
        # Archive summary.json before deleting the task directory
        summary_src = target / 'summary.json'
        if summary_src.exists():
            history_dir = resolve_ops_home() / 'task-history'
            history_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(summary_src, history_dir / f'{args.task_id}.json')
            summary_archived = True

        shutil.rmtree(target, ignore_errors=True)

    print(json.dumps({
        'ok': True,
        'task_id': args.task_id,
        'removed': existed,
        'summary_archived': summary_archived,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
