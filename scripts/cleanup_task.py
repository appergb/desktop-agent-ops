#!/usr/bin/env python3
import argparse
import json
import shutil
import tempfile
from pathlib import Path

BASE = Path(tempfile.gettempdir()) / 'openclaw-desktop-agent'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-id', required=True)
    args = ap.parse_args()
    target = BASE / args.task_id
    existed = target.exists()
    if existed:
        shutil.rmtree(target, ignore_errors=True)
    print(json.dumps({'ok': True, 'task_id': args.task_id, 'removed': existed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
