#!/usr/bin/env python3
"""Shared Python executable resolver for desktop-agent-ops scripts.

Resolves the correct Python executable using a three-level priority:
  1. DESKTOP_AGENT_OPS_PYTHON env var (set by setup/skill)
  2. Saved path in setup_state.json (persisted by first_run_setup.py)
  3. Fallback to 'python3'
"""

import json
import os
from pathlib import Path


def resolve_ops_home():
    """Return the shared runtime home for setup state and user workflows."""
    return Path(
        os.environ.get(
            "DESKTOP_AGENT_OPS_HOME",
            os.environ.get(
                "CODEX_DESKTOP_AGENT_OPS_HOME",
                os.environ.get(
                    "CLAUDE_DESKTOP_AGENT_OPS_HOME",
                    os.environ.get(
                        "OPENCLAW_DESKTOP_AGENT_OPS_HOME",
                        Path.home() / ".claude" / "desktop-agent-ops",
                    ),
                ),
            ),
        )
    ).expanduser().resolve()


PERMISSION_HOME = resolve_ops_home()


def resolve_python():
    """Return the best available Python executable path."""
    env_py = os.environ.get("DESKTOP_AGENT_OPS_PYTHON")
    if env_py and Path(env_py).exists():
        return env_py
    state_file = PERMISSION_HOME / "setup_state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            saved_py = state.get("env", {}).get("DESKTOP_AGENT_OPS_PYTHON")
            if saved_py and Path(saved_py).exists():
                return saved_py
            saved_py = (
                state.get("stages", {}).get("python_env", {}).get("python")
            )
            if saved_py and Path(saved_py).exists():
                return saved_py
        except Exception:
            pass
    return "python3"
