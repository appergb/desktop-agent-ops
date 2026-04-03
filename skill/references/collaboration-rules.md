# Collaboration Rules

## Tool Priority (MUST follow before any desktop automation)

Before using Desktop Agent Ops for screen recognition, the agent MUST check whether a higher-level tool can accomplish the task:

1. **MCP Servers** — If an MCP server controls the target (e.g., `chrome-devtools` for browsers, `fetch` for HTTP, `memory` for knowledge), use it. MCP is faster, more reliable, and does not require screenshots or OCR.
2. **Native CLI / AppleScript** — If the app is scriptable (e.g., `osascript`, `defaults`, shell commands), use that.
3. **Desktop Agent Ops** — Use ONLY when no structured API exists for the target app (e.g., WeChat, QQ, native GUI-only software).

> **Rule: Never use screen OCR to do what a structured API can do.**

## Default

The main agent should do the task itself.

## Escalate only when clearly helpful

Consider collaboration only when one or more of these are true:

- two or more apps need coordinated attention
- two or more windows need simultaneous tracking
- copy/compare/transfer work is easier split by role
- repeated single-agent attempts have already failed
- a subtask is well-bounded and can be delegated cleanly

## Control rule

Even in collaboration mode, keep the main agent as controller.

- the main agent defines the subtask
- the sub-agent returns observations or a bounded result
- the main agent decides the next step

## Avoid in MVP

Do not overbuild collaboration before the single-agent flow is stable.
