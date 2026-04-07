#!/usr/bin/env python3
"""Workflow execution helpers separated from the CLI entrypoint."""

import json
import os
import subprocess
import time

from workflow_runtime import substitute_vars


MAX_RETRIES = 2


def execute_step(step, params, prev_result, app, py, task_dir, step_results=None, default_timeout=60, skill_dir=None):
    results = []
    step_num = step["number"]
    step_timeout = step.get("timeout", default_timeout)

    for cmd_template in step["commands"]:
        cmd = substitute_vars(
            cmd_template,
            params,
            prev_result,
            app,
            py,
            step_results,
            skill_dir=skill_dir,
        )

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=step_timeout,
                cwd=str(skill_dir) if skill_dir else None,
                env={**os.environ, "TASK_DIR": task_dir} if task_dir else None,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "step": step_num,
                "results": results,
                "error": f"Command timed out ({step_timeout}s): {cmd}",
            }

        stdout = proc.stdout.strip()
        parsed = None
        if stdout:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                parsed = None

        entry = {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": proc.stderr.strip(),
            "parsed": parsed,
        }
        results.append(entry)

        if parsed and isinstance(parsed, dict):
            prev_result.update(parsed)

        if proc.returncode != 0:
            return {
                "ok": False,
                "step": step_num,
                "results": results,
                "error": f"Command failed (rc={proc.returncode}): {cmd}",
            }

        if parsed and isinstance(parsed, dict) and parsed.get("ok") is False:
            return {
                "ok": False,
                "step": step_num,
                "results": results,
                "error": parsed.get("error", f"Step {step_num} command reported failure"),
            }

    return {"ok": True, "step": step_num, "results": results, "error": None}


def run_workflow(workflow, params, py, scripts_dir, skill_dir):
    meta = workflow["meta"]
    name = meta.get("name", "unnamed")
    app = meta.get("app", "")
    steps = workflow["steps"]
    task_id = f"wf-{name}-{int(time.time())}"

    init_result = subprocess.run(
        [py, str(scripts_dir / "task_context.py"), "init", "--task-id", task_id],
        capture_output=True,
        text=True,
        timeout=15,
    )
    task_dir = ""
    if init_result.returncode == 0:
        try:
            init_data = json.loads(init_result.stdout.strip())
            task_dir = init_data.get("task_dir", "")
        except json.JSONDecodeError:
            pass

    prev_result = {}
    step_results = {}
    meta_timeout = meta.get("timeout", 60)
    steps_completed = 0
    last_error = None

    for step in steps:
        success = False
        for attempt in range(1 + MAX_RETRIES):
            step_prev = dict(prev_result)
            step_result = execute_step(
                step,
                params,
                step_prev,
                app,
                py,
                task_dir,
                step_results=step_results,
                default_timeout=meta_timeout,
                skill_dir=skill_dir,
            )
            if step_result["ok"]:
                prev_result.update(step_prev)
                step_num = step["number"]
                parsed_data = {}
                for entry in step_result.get("results", []):
                    parsed = entry.get("parsed")
                    if parsed and isinstance(parsed, dict):
                        parsed_data.update(parsed)
                step_results[step_num] = parsed_data
                steps_completed += 1
                success = True
                break

            last_error = step_result.get("error")
            if attempt < MAX_RETRIES:
                time.sleep(1)

        if not success:
            break

    subprocess.run(
        [py, str(scripts_dir / "cleanup_task.py"), "--task-id", task_id],
        capture_output=True,
        text=True,
        timeout=15,
    )

    summary = {
        "ok": steps_completed == len(steps),
        "workflow": name,
        "steps_completed": steps_completed,
        "steps_total": len(steps),
        "task_id": task_id,
    }
    if summary["ok"] is False and last_error:
        summary["error"] = last_error
    return summary
