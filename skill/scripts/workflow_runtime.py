#!/usr/bin/env python3
"""Pure workflow parameter and variable helpers."""

import re
from pathlib import Path


_RESULT_VAR = re.compile(r"\$RESULT_(\w+)")
_STEP_VAR = re.compile(r"\$STEP_(\d+)_(\w+)")


def parse_params(raw_params):
    params = {}
    if not raw_params:
        return params
    for item in raw_params:
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        params[key.strip()] = value.strip()
    return params


def check_required_params(meta, params):
    declared = meta.get("parameters") or []
    missing = []
    for param in declared:
        if not isinstance(param, dict):
            continue
        if param.get("required", False) and param["name"] not in params and param.get("default") is None:
            missing.append(param["name"])
    return missing


def apply_defaults(meta, params):
    result = dict(params)
    declared = meta.get("parameters") or []
    for param in declared:
        if not isinstance(param, dict):
            continue
        name = param.get("name", "")
        if name and name not in result and param.get("default") is not None:
            result[name] = str(param["default"])
    return result


def flatten_result_fields(data, prefix=""):
    flat = {}
    if not isinstance(data, dict):
        return flat
    for key, value in data.items():
        full_key = f"{prefix}_{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_result_fields(value, full_key))
        else:
            flat[full_key] = value
    return flat


def substitute_vars(text, params, prev_result, app, py, step_results=None, scripts_dir=None, skill_dir=None):
    result = text
    scripts_dir = Path(scripts_dir or Path(__file__).resolve().parent).resolve()
    skill_dir = Path(skill_dir or scripts_dir.parent).resolve()

    builtins = [
        ("$SCRIPT_DIR", str(scripts_dir)),
        ("$SKILL_DIR", str(skill_dir)),
        ("$PY", py),
    ]
    for var_name, var_value in builtins:
        pattern = re.escape(var_name) + r"(?![A-Za-z0-9_])"
        result = re.sub(pattern, var_value.replace("\\", "\\\\"), result)

    if app:
        result = re.sub(r"\$app(?![A-Za-z0-9_])", app.replace("\\", "\\\\"), result)

    arguments = " ".join(f"{key}={value}" for key, value in sorted(params.items()))
    result = result.replace("$ARGUMENTS", arguments)

    if step_results:
        def _replace_step(match):
            step_num = int(match.group(1))
            field = match.group(2)
            step_data = flatten_result_fields(step_results.get(step_num, {}))
            return str(step_data.get(field, match.group(0)))
        result = _STEP_VAR.sub(_replace_step, result)

    if prev_result and isinstance(prev_result, dict):
        def _replace_result(match):
            field = match.group(1)
            flattened_prev = flatten_result_fields(prev_result)
            return str(flattened_prev.get(field, prev_result.get(field, match.group(0))))
        result = _RESULT_VAR.sub(_replace_result, result)

    for key, value in params.items():
        pattern = re.escape(f"${key}") + r"(?![A-Za-z0-9_])"
        result = re.sub(pattern, str(value).replace("\\", "\\\\"), result)

    return result


def preview_commands(workflow, params, py, scripts_dir=None, skill_dir=None):
    meta = workflow["meta"]
    app = meta.get("app", "")
    prev_result = {}
    step_results = {}
    preview_steps = []

    for step in workflow["steps"]:
        resolved = []
        for cmd in step["commands"]:
            resolved.append(
                substitute_vars(
                    cmd,
                    params,
                    prev_result,
                    app,
                    py,
                    step_results,
                    scripts_dir=scripts_dir,
                    skill_dir=skill_dir,
                )
            )
        preview_steps.append({
            "number": step["number"],
            "title": step["title"],
            "commands": resolved,
        })

    return {"ok": True, "steps": preview_steps}
