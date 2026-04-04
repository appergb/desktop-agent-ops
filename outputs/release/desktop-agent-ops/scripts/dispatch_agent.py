#!/usr/bin/env python3
"""
dispatch_agent.py — Main Agent → Executor step-by-step orchestration.

Design Principles:
  1. Small models have limited attention — send ONE clear step at a time
  2. Each step gets fresh context with task background + specific instruction
  3. Main Agent decides what to do next based on executor feedback
  4. Screenshots are passed as images so the executor can SEE the screen
  5. Multiple scenarios supported — not hardcoded to any specific task

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │  Main Agent (Claude / Python caller)                     │
  │  → Understands the full goal                             │
  │  → Breaks into atomic steps                              │
  │  → Sends one step at a time with clear context           │
  │  → Analyzes executor feedback → decides next step        │
  │  → Handles errors: retry / skip / abort                  │
  └───────────────────┬──────────────────────────────────────┘
                      │ step()
  ┌───────────────────▼──────────────────────────────────────┐
  │  ExecutorSession                                         │
  │  → Builds focused context for each step                  │
  │  → Manages multimodal screenshots                        │
  │  → Tracks step history within the task                   │
  │  → Auto-cleans temp files                                │
  └───────────────────┬──────────────────────────────────────┘
                      │ OpenAI-compatible API
  ┌───────────────────▼──────────────────────────────────────┐
  │  Executor LLM (Gemma 4 / any local model via LM Studio) │
  │  → Receives focused instruction + screenshot             │
  │  → Calls desktop-agent-ops tools                         │
  │  → Reports result in 1-2 sentences                       │
  └──────────────────────────────────────────────────────────┘

Context Strategy (for small models):
  - Each step() call builds a FRESH message list:
    [system_prompt, task_background, step_history_summary, current_instruction]
  - This keeps the context small and focused
  - Task background provides continuity between steps
  - Step history summary keeps the model aware of what already happened

Usage:
    # Programmatic (from Python — preferred)
    session = ExecutorSession(task="发送微信消息给文件传输助手")
    r1 = session.step("聚焦微信应用（进程名 WeChat）并截图确认")
    r2 = session.step("在左侧列表找到'文件传输助手'并点击")
    r3 = session.step("在底部输入框输入'你好'然后按回车发送")

    # CLI — single step
    python3 dispatch_agent.py step --task "发微信" "聚焦WeChat并截图"

    # CLI — workflow (auto step-by-step)
    python3 dispatch_agent.py workflow --task "发微信给文件传输助手" \\
        --steps "聚焦WeChat" "找到文件传输助手并点击" "输入你好并回车发送"

    # CLI — interactive
    python3 dispatch_agent.py interactive
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from local_agent import TOOLS, execute_tool, build_system_prompt


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAX_TOOL_ROUNDS_PER_STEP = 8   # per step, not per task
MAX_CACHED_SCREENSHOTS = 3     # temp files to keep


# ─────────────────────────────────────────────
# Executor Session
# ─────────────────────────────────────────────

class ExecutorSession:
    """Step-by-step executor session for desktop automation.

    Each step() call:
      1. Builds a fresh, focused context (system + background + history + instruction)
      2. Lets the executor call tools until it responds with text
      3. Records the result in step_history
      4. Returns structured feedback to the Main Agent

    This keeps the context window small and the executor focused.
    """

    def __init__(self, task="", base_url="http://localhost:1234/v1",
                 model=None, python_exec="python3", verbose=False,
                 max_tool_rounds=MAX_TOOL_ROUNDS_PER_STEP):
        self.task = task
        self.base_url = base_url.rstrip("/")
        self.model = model or self._detect_model()
        self.python_exec = python_exec
        self.verbose = verbose
        self.max_tool_rounds = max_tool_rounds

        # State
        self.step_history = []    # [{step_num, instruction, response, ok, tools}]
        self.step_count = 0
        self._screenshot_paths = []
        self._last_screenshot = None  # most recent screenshot base64

    def _detect_model(self):
        try:
            url = f"{self.base_url}/models"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                models = data.get("data", [])
                if models:
                    return models[0]["id"]
        except Exception:
            pass
        return None

    def _api_call(self, payload):
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    # ── Context builder ──

    def _build_step_context(self, instruction):
        """Build a fresh, focused context for this step.

        Structure:
          [0] system — who you are, what tools you have, how to behave
          [1] user   — task background + what happened so far + current instruction
                       (optionally includes last screenshot as image)

        This is intentionally minimal. Small models work best with
        short, clear context — not long conversation history.
        """
        system = build_system_prompt()
        messages = [{"role": "system", "content": system}]

        # Build the step instruction with context
        parts = []

        # Task background (always present for continuity)
        if self.task:
            parts.append(f"## Task\n{self.task}")

        # What happened so far (brief summary)
        if self.step_history:
            history_lines = []
            for h in self.step_history[-5:]:  # last 5 steps max
                status = "✓" if h["ok"] else "✗"
                history_lines.append(f"  Step {h['step_num']}: {status} {h['instruction'][:60]} → {h['response'][:80]}")
            parts.append("## Completed Steps\n" + "\n".join(history_lines))

        # Current instruction (the main focus)
        parts.append(f"## Current Step (Step {self.step_count + 1})\n{instruction}")

        # Combine into user message
        user_text = "\n\n".join(parts)

        # If we have a recent screenshot, include it as multimodal content
        if self._last_screenshot:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{self._last_screenshot}"
                        },
                    },
                ],
            })
            # Consumed — next step won't see this unless a new screenshot is taken
            self._last_screenshot = None
        else:
            messages.append({"role": "user", "content": user_text})

        return messages

    # ── Core step execution ──

    def step(self, instruction):
        """Execute a single step. This is the main API for the Main Agent.

        The executor receives:
          - System prompt (who it is, available tools)
          - Task background (what the overall goal is)
          - History summary (what steps completed so far)
          - Current instruction (what to do NOW)
          - Last screenshot (if available, as image)

        Returns:
            dict with keys:
              ok (bool)       — did the step succeed?
              response (str)  — executor's text response
              tools (list)    — tools that were called [{name, args, result}]
              error (str)     — error message if ok=False
        """
        if not self.model:
            return {"ok": False, "error": "No model loaded in LM Studio",
                    "response": "", "tools": []}

        self.step_count += 1
        step_num = self.step_count

        print(f"\n{'='*60}")
        print(f"  [Step {step_num}] {instruction}")
        print(f"{'='*60}")

        # Build fresh context for this step
        messages = self._build_step_context(instruction)
        tool_log = []

        for round_num in range(1, self.max_tool_rounds + 1):
            payload = {
                "model": self.model,
                "messages": messages,
                "tools": TOOLS,
                "temperature": 0.2,
                "max_tokens": 2048,
            }

            try:
                resp = self._api_call(payload)
            except Exception as e:
                error_msg = f"API error: {e}"
                print(f"  [ERROR] {error_msg}")
                self._record_step(step_num, instruction, error_msg, False, tool_log)
                return {"ok": False, "error": error_msg, "response": "", "tools": tool_log}

            choice = resp["choices"][0]
            msg = choice["message"]

            # ── Tool calls ──
            if msg.get("tool_calls"):
                messages.append(msg)
                for tc in msg["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    fn_args = tc["function"]["arguments"]
                    tc_id = tc.get("id", f"call_{step_num}_{round_num}")

                    print(f"  [{step_num}.{round_num}] 🔧 {fn_name}({fn_args})")

                    result_str, image_data = execute_tool(fn_name, fn_args, self.python_exec)
                    tool_log.append({"name": fn_name, "args": fn_args, "result": result_str})

                    if self.verbose:
                        print(f"          → {result_str[:300]}")

                    # Track and cache screenshots
                    if image_data and image_data.get("path"):
                        self._track_screenshot(image_data["path"])
                    if image_data and image_data.get("base64"):
                        self._last_screenshot = image_data["base64"]
                        if self.verbose:
                            print(f"          📸 Screenshot cached for next context")

                    # Tool response (text only — image goes in next user message)
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                        "tool_call_id": tc_id,
                    })

                # If screenshot was taken, inject it as user message for the model to see
                if self._last_screenshot:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Above is the screenshot result. Analyze it and continue with the task."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self._last_screenshot}"
                                },
                            },
                        ],
                    })
                continue

            # ── Text response (step done) ──
            if msg.get("content"):
                text = msg["content"].strip()
                print(f"\n  [Executor] {text}")
                self._record_step(step_num, instruction, text, True, tool_log)
                return {"ok": True, "response": text, "tools": tool_log}

            # ── Finished without content ──
            if choice.get("finish_reason") == "stop":
                print(f"\n  [Executor] (step done, no text)")
                self._record_step(step_num, instruction, "(completed)", True, tool_log)
                return {"ok": True, "response": "(completed)", "tools": tool_log}

        # ── Max rounds ──
        print(f"\n  [WARN] Step {step_num}: max tool rounds ({self.max_tool_rounds})")
        self._record_step(step_num, instruction, "max_rounds_reached", False, tool_log)
        return {"ok": False, "error": "max_rounds_reached", "response": "", "tools": tool_log}

    def _record_step(self, step_num, instruction, response, ok, tools):
        self.step_history.append({
            "step_num": step_num,
            "instruction": instruction,
            "response": response,
            "ok": ok,
            "tools": len(tools),
        })

    # ── Screenshot management ──

    def _track_screenshot(self, path):
        if path and path not in self._screenshot_paths:
            self._screenshot_paths.append(path)
        while len(self._screenshot_paths) > MAX_CACHED_SCREENSHOTS:
            old = self._screenshot_paths.pop(0)
            try:
                os.remove(old)
            except OSError:
                pass

    def cleanup(self):
        """Clean up all temp files."""
        for p in self._screenshot_paths:
            try:
                os.remove(p)
            except OSError:
                pass
        self._screenshot_paths.clear()
        self._last_screenshot = None

    # ── Task context update ──

    def set_task(self, task):
        """Update task description (e.g. when Main Agent changes the goal)."""
        self.task = task

    def reset(self, new_task=""):
        """Full reset — new task, clear all history and cache."""
        self.cleanup()
        self.task = new_task
        self.step_history.clear()
        self.step_count = 0
        self._last_screenshot = None
        if self.verbose:
            print(f"  [Session Reset] {'Task: ' + new_task[:50] if new_task else 'No task'}")

    # ── Status ──

    def print_status(self):
        print(f"\n--- Session Status ---")
        print(f"  Model:      {self.model}")
        print(f"  Task:       {self.task[:60] or '(none)'}")
        print(f"  Steps:      {self.step_count}")
        print(f"  Screenshots: {len(self._screenshot_paths)} cached")
        for h in self.step_history:
            mark = "✓" if h["ok"] else "✗"
            print(f"    [{h['step_num']}] {mark} {h['instruction'][:50]} → {h['response'][:50]}")


# ─────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────

def cmd_step(args):
    """Execute a single step within a task context."""
    session = ExecutorSession(
        task=args.task or "", base_url=args.base_url,
        model=args.model, python_exec=args.python,
        verbose=args.verbose,
    )
    try:
        result = session.step(args.instruction)
        _print_result(result)
    finally:
        session.cleanup()


def cmd_workflow(args):
    """Execute multiple steps with shared task context."""
    session = ExecutorSession(
        task=args.task or "", base_url=args.base_url,
        model=args.model, python_exec=args.python,
        verbose=args.verbose,
    )
    try:
        for i, step_instruction in enumerate(args.steps, 1):
            print(f"\n{'#'*60}")
            print(f"  Workflow Step {i}/{len(args.steps)}")
            print(f"{'#'*60}")

            result = session.step(step_instruction)

            if not result.get("ok"):
                print(f"\n  [WORKFLOW STOPPED] Step {i} failed")
                break

            time.sleep(0.5)

        print(f"\n{'#'*60}")
        ok_count = sum(1 for h in session.step_history if h["ok"])
        print(f"  Workflow: {ok_count}/{len(args.steps)} steps completed")
        print(f"{'#'*60}")
        session.print_status()
    finally:
        session.cleanup()


def cmd_interactive(args):
    """Interactive mode — you are the Main Agent."""
    session = ExecutorSession(
        base_url=args.base_url, model=args.model,
        python_exec=args.python, verbose=args.verbose,
    )
    print("=" * 60)
    print("  Main Agent → Executor (step-by-step dispatch)")
    print(f"  Model: {session.model or '(not detected)'}")
    print("─" * 60)
    print("  Commands:")
    print("    task <description>  — set/change task context")
    print("    reset               — clear everything")
    print("    status              — show session info")
    print("    quit                — exit")
    print("  Anything else is sent as a step instruction.")
    print("=" * 60)

    try:
        while True:
            try:
                line = input("\n[Main Agent] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSession ended.")
                break

            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            if line.lower() == "status":
                session.print_status()
                continue
            if line.lower() == "reset":
                session.reset()
                print("  [Session cleared]")
                continue
            if line.lower().startswith("task "):
                task_desc = line[5:].strip()
                session.set_task(task_desc)
                print(f"  [Task set: {task_desc[:50]}]")
                continue

            result = session.step(line)
            _print_result(result)
    finally:
        session.cleanup()


def _print_result(result):
    print(f"\n{'─'*60}")
    if result.get("ok"):
        print(f"  ✓ Step completed ({len(result.get('tools', []))} tool calls)")
    else:
        print(f"  ✗ Step failed: {result.get('error', 'unknown')}")


def main():
    ap = argparse.ArgumentParser(
        description="Main Agent → Executor: step-by-step desktop automation dispatch"
    )
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--model", default=None)
    ap.add_argument("--python", default="python3")
    ap.add_argument("--verbose", "-v", action="store_true")

    sub = ap.add_subparsers(dest="command")

    # step — single step
    p_step = sub.add_parser("step", help="Execute one step")
    p_step.add_argument("instruction", help="Step instruction")
    p_step.add_argument("--task", default="", help="Task context/background")

    # workflow — multi-step
    p_wf = sub.add_parser("workflow", help="Execute steps in sequence")
    p_wf.add_argument("--task", default="", help="Task description")
    p_wf.add_argument("--steps", nargs="+", required=True, help="Steps to execute")

    # interactive
    sub.add_parser("interactive", help="Interactive dispatch mode")

    args = ap.parse_args()

    if args.command == "step":
        cmd_step(args)
    elif args.command == "workflow":
        cmd_workflow(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    else:
        ap.print_help()
        print("\n" + "─" * 60)
        print("Examples:")
        print()
        print("  # Single step with task context")
        print('  python3 dispatch_agent.py step "聚焦WeChat并截图" --task "发微信消息"')
        print()
        print("  # Multi-step workflow (Main Agent pre-plans all steps)")
        print('  python3 dispatch_agent.py workflow --task "给文件传输助手发微信" \\')
        print('      --steps \\')
        print('      "聚焦WeChat应用并截图确认当前界面" \\')
        print('      "在左侧联系人列表中找到文件传输助手并点击" \\')
        print('      "在底部输入框点击，输入你好，然后按回车键发送"')
        print()
        print("  # Interactive — you are the Main Agent")
        print("  python3 dispatch_agent.py interactive")


if __name__ == "__main__":
    main()
