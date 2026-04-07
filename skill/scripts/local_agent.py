#!/usr/bin/env python3
"""
local_agent.py — Executor engine for desktop automation via local LLM.

This module provides:
  1. Tool definitions (OpenAI function-calling format)
  2. Tool execution (maps function calls → desktop_ops.py CLI)
  3. Multimodal support (screenshots returned as base64 images)
  4. LM Studio API client
  5. Standalone agent loop (for direct use without dispatch_agent)

Architecture (standalone):
  User instruction → Local LLM (LM Studio) → tool calls → desktop_ops → results → LLM → ...

Architecture (with dispatch_agent — preferred):
  Main Agent (Claude) → dispatch_agent.py → this module → Local LLM (Gemma 4) → tools

Usage:
    # Standalone
    python3 local_agent.py --task "截图并告诉我屏幕上有什么"
    python3 local_agent.py --interactive

    # As module (used by dispatch_agent.py)
    from local_agent import TOOLS, execute_tool, build_system_prompt
"""
import argparse
import base64
import json
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ─────────────────────────────────────────────
# Tool definitions (OpenAI function calling format)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Take a screenshot of the current screen or a specific region. Returns the image file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output": {"type": "string", "description": "Output file path (optional)"},
                    "with_cursor": {"type": "boolean", "description": "Include cursor in screenshot"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "focus_app",
            "description": "Bring an application to the front (make it frontmost).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name, e.g. 'Finder', 'WeChat', 'Safari'"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "frontmost",
            "description": "Get the name of the currently frontmost (active) application.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_apps",
            "description": "List all running applications.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "front_window_bounds",
            "description": "Get the position and size of an app's front window. Returns {x, y, width, height}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Application name"},
                },
                "required": ["app"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at screen coordinates (x, y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_click",
            "description": "Double-click at screen coordinates (x, y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": "Move the mouse cursor to screen coordinates (x, y) without clicking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into the currently focused input field. Uses clipboard paste for reliability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key (e.g. 'return', 'escape', 'tab', 'delete', 'space').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name: return, escape, tab, delete, space, up, down, left, right"},
                },
                "required": ["key"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hotkey",
            "description": "Press a keyboard shortcut (e.g. cmd+c, cmd+v, cmd+tab).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys to press together, e.g. ['cmd', 'c'] for Cmd+C",
                    },
                },
                "required": ["keys"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll at a specific position. Negative amount = scroll down, positive = scroll up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "Scroll amount (negative=down, positive=up)"},
                    "x": {"type": "integer", "description": "X coordinate to scroll at"},
                    "y": {"type": "integer", "description": "Y coordinate to scroll at"},
                },
                "required": ["amount"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_element",
            "description": "Find a UI element by text within an app's window. Uses Accessibility API first, then OCR. Returns coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Target application name"},
                    "text": {"type": "string", "description": "Text to find (button label, menu item, etc.)"},
                    "region_label": {
                        "type": "string",
                        "enum": ["top_search", "left_sidebar", "content_area", "bottom_input", "primary_action", "toolbar_row", "title_header"],
                        "description": "Optional: limit search to a specific window region",
                    },
                },
                "required": ["app", "text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screen_size",
            "description": "Get the screen resolution in logical coordinates.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_position",
            "description": "Get the current mouse cursor position.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


# ─────────────────────────────────────────────
# Tool execution
# ─────────────────────────────────────────────

def run_desktop_op(python_exec, *args):
    """Run a desktop_ops.py command and return JSON result."""
    cmd = [python_exec, str(ROOT / "desktop_ops.py"), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if p.returncode == 0 and p.stdout.strip():
            return json.loads(p.stdout)
        return {"ok": False, "error": p.stderr.strip() or "command_failed"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_target_resolver(python_exec, app, text, region_label=None):
    """Run target_resolver.py and return result."""
    cmd = [python_exec, str(ROOT / "target_resolver.py"),
           "--app", app, "--text", text, "--python", python_exec]
    if region_label:
        cmd += ["--region-label", region_label]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if p.returncode == 0 and p.stdout.strip():
            return json.loads(p.stdout)
        return {"ok": False, "error": p.stderr.strip() or "resolver_failed"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def encode_image_base64(image_path):
    """Read an image file and return base64-encoded string."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def execute_tool(name, arguments, python_exec):
    """Execute a tool call and return the result as a string.

    For screenshot tool, also returns the image data for multimodal models.
    Returns: (result_str, image_data_or_None)
      - result_str: JSON string of the tool result
      - image_data: dict with {base64, path, mime_type} if screenshot, else None
    """
    args = json.loads(arguments) if isinstance(arguments, str) else arguments

    if name == "screenshot":
        result = run_desktop_op(python_exec, "screenshot",
                                *(["--output", args["output"]] if args.get("output") else []),
                                *(["--with-cursor"] if args.get("with_cursor") else []))
        # Attach image data for multimodal
        image_data = None
        if result.get("ok") and result.get("output"):
            b64 = encode_image_base64(result["output"])
            if b64:
                image_data = {
                    "base64": b64,
                    "path": result["output"],
                    "mime_type": "image/png",
                }
        return json.dumps(result, ensure_ascii=False), image_data
    elif name == "focus_app":
        result = run_desktop_op(python_exec, "focus-app", "--name", args["name"])
    elif name == "frontmost":
        result = run_desktop_op(python_exec, "frontmost")
    elif name == "list_apps":
        result = run_desktop_op(python_exec, "list-apps")
    elif name == "front_window_bounds":
        result = run_desktop_op(python_exec, "front-window-bounds", "--app", args["app"])
    elif name == "click":
        cmd_args = ["click", "--x", str(args["x"]), "--y", str(args["y"])]
        if args.get("button"):
            cmd_args += ["--button", args["button"]]
        result = run_desktop_op(python_exec, *cmd_args)
    elif name == "double_click":
        result = run_desktop_op(python_exec, "double-click",
                                "--x", str(args["x"]), "--y", str(args["y"]))
    elif name == "move":
        result = run_desktop_op(python_exec, "move",
                                "--x", str(args["x"]), "--y", str(args["y"]))
    elif name == "type_text":
        result = run_desktop_op(python_exec, "type", "--text", args["text"])
    elif name == "press_key":
        result = run_desktop_op(python_exec, "press", "--key", args["key"])
    elif name == "hotkey":
        result = run_desktop_op(python_exec, "hotkey", "--keys", *args["keys"])
    elif name == "scroll":
        cmd_args = ["scroll", "--amount", str(args["amount"])]
        if args.get("x") is not None:
            cmd_args += ["--x", str(args["x"])]
        if args.get("y") is not None:
            cmd_args += ["--y", str(args["y"])]
        result = run_desktop_op(python_exec, *cmd_args)
    elif name == "find_element":
        result = run_target_resolver(python_exec, args["app"], args["text"],
                                     args.get("region_label"))
        # Simplify output for the model
        best = result.get("best_candidate")
        if best:
            result = {
                "ok": True,
                "found": True,
                "x": best["x"], "y": best["y"],
                "within_window": best.get("within_window"),
                "source": best.get("source"),
                "label": best.get("label"),
            }
        else:
            result = {"ok": True, "found": False, "message": "Element not found"}
    elif name == "screen_size":
        result = run_desktop_op(python_exec, "screen-size")
    elif name == "mouse_position":
        result = run_desktop_op(python_exec, "mouse-position")
    else:
        result = {"ok": False, "error": f"unknown_tool: {name}"}

    return json.dumps(result, ensure_ascii=False), None


# ─────────────────────────────────────────────
# LM Studio API client (pure urllib, no deps)
# ─────────────────────────────────────────────

def api_request(base_url, endpoint, payload):
    """Make a POST request to LM Studio API."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"\n[ERROR] Cannot connect to LM Studio at {base_url}")
        print(f"  Make sure LM Studio is running with the API server enabled.")
        print(f"  Error: {e}")
        sys.exit(1)


def get_loaded_model(base_url):
    """Get the currently loaded model from LM Studio."""
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            if models:
                return models[0]["id"]
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are a precise desktop automation executor on macOS. You receive instructions from a Main Agent and execute them by calling tools. You can SEE screenshots — analyze them carefully.

## Identity
- You are the **Executor**. You do NOT plan — you execute.
- The Main Agent tells you WHAT to do. You figure out HOW using your tools.
- You report results honestly — success or failure, never fabricate.

## Core Rules
1. **See before acting**: Always take a screenshot first to understand the current screen state.
2. **One action, one verification**: After every click/type/press, take a screenshot to confirm the result.
3. **Focus first**: Always call focus_app before interacting with any application.
4. **Coordinates from tools only**: Never guess coordinates. Use find_element or analyze screenshots to determine where to click.
5. **Report concisely**: When done, state exactly what happened in 1-2 sentences.
6. **Report failures immediately**: If a tool returns an error or an action didn't work, say so. Don't retry blindly — report back to the Main Agent.

## Tool Usage Guide

### Seeing the screen
- `screenshot` → Returns an image you can see. Analyze it to understand what's on screen.
- `find_element(app, text)` → Searches for UI text using Accessibility API + OCR. Returns x, y coordinates.
  - Use `region_label` to narrow the search area (e.g. "primary_action" for send buttons, "bottom_input" for text fields).

### Interacting
- `focus_app(name)` → Bring app to front and restore a usable window when possible. Run `list_apps()` first to find the exact app name — do not guess. See app-names.md for platform conventions (macOS = English process names, Windows = window titles).
- `click(x, y)` → Left click. `double_click(x, y)` → Double click.
- `type_text(text)` → Types into the currently focused input field via clipboard paste.
- `press_key(key)` → Press: return, escape, tab, delete, space, up, down, left, right.
- `hotkey(keys)` → Shortcut: ["cmd", "c"] for Cmd+C, ["cmd", "v"] for Cmd+V.
- `scroll(amount)` → Negative = down, positive = up. Can specify x, y position.

### Info queries
- `screen_size` / `mouse_position` / `frontmost` / `list_apps` / `front_window_bounds(app)`

## Execution Pattern
```
1. screenshot → understand current state
2. focus_app → ensure target app is frontmost
3. screenshot → confirm app is focused, see its layout
4. find_element or analyze screenshot → locate target element
5. click/type/press → perform the action
6. screenshot → verify result
7. report to Main Agent
```

## App Names: Discover Dynamically
**NEVER assume the correct app name.** Always discover it first:
1. Run `list_apps()` to see all running apps
2. If the target app is not running, try launching it (e.g. `osascript -e 'open app "WeChat"'` (macOS) or `subprocess.run(["start", "", "WeChat"])` (Windows))
3. If the app name is uncertain (Chinese vs English), use web search
4. If focus_app fails with "not found", re-run list_apps() to check exact spelling
5. Use the EXACT name from list_apps() output — do not guess or translate names
6. See `skill/references/app-names.md` for patterns: macOS uses English process names (always),
   Windows uses window titles (vary by Windows language version)

## Error Handling
- If find_element returns found:false → take screenshot and describe what you see
- If focus_app fails → check list_apps to see if the app is running
- If focus_app succeeds but front_window_bounds still fails → treat it as a window-restore problem, report it, and do not guess coordinates
- If a click had no effect → screenshot and report the discrepancy
- NEVER retry more than twice — report failure to Main Agent instead

{extra_context}"""


def build_system_prompt(extra_context=""):
    """Build the system prompt, optionally with extra context from Main Agent."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        extra_context=f"\n## Additional Context\n{extra_context}" if extra_context else ""
    )


# Keep backward compatibility
SYSTEM_PROMPT = build_system_prompt()


# ─────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────

def run_agent(task, base_url, model, python_exec, max_steps, verbose):
    """Run the agent loop: send task → LLM calls tools → execute → repeat."""
    if not model:
        model = get_loaded_model(base_url)
        if not model:
            print("[ERROR] No model loaded in LM Studio. Load a model first.")
            sys.exit(1)
        print(f"[INFO] Using model: {model}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        if verbose:
            print(f"\n--- Step {step} ---")

        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        resp = api_request(base_url, "/chat/completions", payload)
        choice = resp["choices"][0]
        msg = choice["message"]

        # If model wants to call tools
        if choice.get("finish_reason") == "tool_calls" or msg.get("tool_calls"):
            messages.append(msg)
            tool_calls = msg.get("tool_calls", [])

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"]["arguments"]
                tc_id = tc.get("id", f"call_{step}")

                print(f"  [{step}] 🔧 {fn_name}({fn_args})")

                result_str, image_data = execute_tool(fn_name, fn_args, python_exec)

                if verbose:
                    print(f"       → {result_str[:200]}{'...' if len(result_str) > 200 else ''}")

                # Build tool response — multimodal if screenshot
                if image_data:
                    tool_content = [
                        {"type": "text", "text": result_str},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_data['mime_type']};base64,{image_data['base64']}"
                            },
                        },
                    ]
                else:
                    tool_content = result_str

                messages.append({
                    "role": "tool",
                    "content": tool_content,
                    "tool_call_id": tc_id,
                })

        # If model responds with text (done or thinking)
        elif msg.get("content"):
            text = msg["content"].strip()
            print(f"\n[Agent] {text}")
            # If no tool calls, the agent is done
            if not msg.get("tool_calls"):
                return text

        # Stop condition
        if choice.get("finish_reason") == "stop" and not msg.get("tool_calls"):
            final = msg.get("content", "").strip()
            if final:
                print(f"\n[Agent] {final}")
            return final

    print(f"\n[WARN] Reached max steps ({max_steps})")
    return None


def interactive_mode(base_url, model, python_exec, max_steps, verbose):
    """Interactive mode: user types instructions, agent executes."""
    print("=" * 60)
    print("  Desktop Agent (Local LLM via LM Studio)")
    print("  Type your instruction, or 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            task = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not task or task.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break
        run_agent(task, base_url, model, python_exec, max_steps, verbose)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Local LLM desktop agent — connects to LM Studio and uses desktop-agent-ops tools"
    )
    ap.add_argument("--task", help="Task instruction for the agent")
    ap.add_argument("--interactive", action="store_true", help="Interactive mode")
    ap.add_argument("--base-url", default="http://localhost:1234/v1",
                     help="LM Studio API endpoint (default: http://localhost:1234/v1)")
    ap.add_argument("--model", default=None,
                     help="Model name in LM Studio (default: auto-detect)")
    ap.add_argument("--python", default="python3",
                     help="Python executable for desktop_ops scripts")
    ap.add_argument("--max-steps", type=int, default=20,
                     help="Maximum tool call rounds (default: 20)")
    ap.add_argument("--verbose", "-v", action="store_true",
                     help="Print full API messages")

    args = ap.parse_args()

    if args.interactive:
        interactive_mode(args.base_url, args.model, args.python,
                         args.max_steps, args.verbose)
    elif args.task:
        run_agent(args.task, args.base_url, args.model, args.python,
                  args.max_steps, args.verbose)
    else:
        ap.print_help()
        print("\nExample:")
        print('  python3 local_agent.py --task "截图并告诉我屏幕上有什么"')
        print('  python3 local_agent.py --interactive')


if __name__ == "__main__":
    main()
