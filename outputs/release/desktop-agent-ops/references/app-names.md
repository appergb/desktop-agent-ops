# App Names: Discovery Patterns and Platform Conventions

> This is a **pattern guide**, not a hardcoded table. The agent should understand HOW app names work on each platform, then discover the correct name at runtime.

## Core Principle: Always Discover First

**Step 0 is always the same on every platform:**

```bash
$PY scripts/desktop_ops.py list-apps
```

This returns the **authoritative list** of running app window titles/process names. Use the exact names from this output. Do not guess.

---

## macOS: How App Names Work

### Rule: Process names are always in English

**On macOS, app process names are ALWAYS in English** — regardless of the system language.

Even if the user is on Chinese macOS, the WeChat process name is `"WeChat"`, not `"微信"`. This is because:
- App process names are defined in the app's binary metadata
- They do not change based on system language
- The `localizedName()` property might show Chinese in the Dock, but the process name stays English

### How to find app process names on macOS

```bash
# Via desktop_ops (recommended)
$PY scripts/desktop_ops.py list-apps

# Via osascript (what desktop_ops calls internally)
osascript -e 'tell application "System Events" to get name of every application process'
# → Returns: ["Finder", "WeChat", "Safari", "Xcode", "Terminal"]
```

### How to find the Bundle ID (stable identifier)

Bundle IDs do not change across system languages or app versions (usually).

```bash
# Find Bundle ID for a running app
osascript -e 'id of app "WeChat"'
# → Returns: com.tencent.xin

# Or via AppleScript
osascript -e 'tell application "WeChat" to get id'
```

### Example patterns on macOS

| App | Process Name (use this) | Bundle ID | Why it's stable |
|-----|------------------------|----------|----------------|
| WeChat | `WeChat` | `com.tencent.xin` | Always "WeChat" even on Chinese macOS |
| QQ | `QQ` | `com.tencent.qq` | Process name stays "QQ" |
| Feishu (CN) | `Feishu` | `com.sgri.lark` | |
| Lark (intl) | `Lark` | `com.sgri.lark.international` | Different from CN version |
| DingTalk | `DingTalk` | `com.alibaba.DingTalk` | |
| WeChat Work | `WXWork` | `com.tencent.wxwork` | |
| Slack | `Slack` | `com.tinyspeck.slackmacgap` | |
| Discord | `Discord` | `com.hnc.Discord` | |
| Telegram | `Telegram` | `ru.keepcoder.Telegram` | |
| Safari | `Safari` | `com.apple.Safari` | |
| Chrome | `Google Chrome` | `com.google.Chrome` | Full name, not "Chrome" |
| Firefox | `Firefox` | `org.mozilla.firefox` | |
| Finder | `Finder` | `com.apple.finder` | |
| System Settings | `System Settings` | `com.apple.SystemSettings` | Ventura+ |
| Terminal | `Terminal` | `com.apple.Terminal` | |

### Common macOS mistakes to avoid

```
WRONG: focus-app --name "微信"      ← Chinese name, wrong on macOS
RIGHT: focus-app --name "WeChat"    ← English process name, always correct

WRONG: focus-app --name "Chrome"    ← "Chrome" won't match
RIGHT: focus-app --name "Google Chrome"

WRONG: focus-app --name "SystemSettings"    ← old name
RIGHT: focus-app --name "System Settings"   ← Ventura+ name
```

---

## Windows: How App Names Work

### Rule: Window titles vary by the Windows language version

On Windows, app window titles depend on **the language version of Windows itself**, not the app. There are two main cases:

**Chinese Windows** (most common in China):
- WeChat window title: `微信`
- Send button text: `发送`
- Calculator: `计算器`
- File Explorer: `文件资源管理器`

**English Windows**:
- WeChat window title: `WeChat`
- Send button text: `Send`
- Calculator: `Calculator`
- File Explorer: `File Explorer`

These are **separate builds** of WeChat, not just a language setting.

### How to find window titles on Windows

```bash
# Via desktop_ops (recommended)
$PY scripts/desktop_ops.py list-apps
# → Returns: {"apps": ["微信", "Microsoft Edge", "Slack", ...]}

# Via tasklist (raw system command)
tasklist /V /FO LIST
# Window Title field shows the actual title

# Filter for specific app
tasklist /FI "IMAGENAME eq WeChatApp.exe" /V
```

### Example patterns on Windows

| App | Windows EXE Name | Window Title (CN Win) | Window Title (EN Win) |
|-----|-----------------|----------------------|-----------------------|
| WeChat | `WeChatApp.exe` | `微信` | `WeChat` |
| QQ | `QQ.exe` | `QQ` | `QQ` | (usually same) |
| Feishu (CN) | `Feishu.exe` | `飞书` | `Feishu` |
| Lark (intl) | `lark.exe` | `Lark` | `Lark` |
| DingTalk | `DingTalk.exe` | `钉钉` | `DingTalk` |
| WeChat Work | `WXWork.exe` | `企业微信` | `WXWork` |
| Slack | `slack.exe` | `Slack` | `Slack` |
| Discord | `Discord.exe` | `Discord` | `Discord` |
| Telegram | `Telegram.exe` | `Telegram` | `Telegram` |
| Chrome | `chrome.exe` | (page title) ` - Google Chrome` | same |
| Edge | `msedge.exe` | (page title) ` - Microsoft Edge` | same |

### Common Windows mistakes to avoid

```
WRONG: focus-app --name "WeChat"       ← might be "微信" on Chinese Windows
RIGHT: Run list-apps first, use the exact title shown
       e.g. focus-app --name "微信"     ← correct for Chinese Windows

WRONG: focus-app --name "Calculator"   ← on CN Windows this is "计算器"
RIGHT: Run list-apps first

WRONG: focus-app --name "chrome"      ← case-sensitive on Windows
RIGHT: focus-app --name "chrome.exe"   ← include .exe extension
```

---

## Cross-Platform Reasoning Patterns

### Pattern 1: System language vs App language

| Scenario | macOS | Windows |
|----------|-------|---------|
| User speaks Chinese, system is Chinese | App process name = `WeChat` (English) | Window title = `微信` (Chinese) |
| User speaks English, system is English | App process name = `WeChat` | Window title = `WeChat` |
| User speaks Chinese, system is English | App process name = `WeChat` | Window title depends on WeChat version |

**Takeaway**: On macOS, always use English process names. On Windows, always discover via `list-apps` first.

### Pattern 2: Multi-version apps

Some apps have separate CN and international builds:

| App | CN Version | International Version |
|-----|-----------|---------------------|
| Feishu/Lark | Window title `飞书`, EXE `Feishu.exe` | Window title `Lark`, EXE `lark.exe` |
| WeChat | Window title `微信` (CN build) | Window title `WeChat` (EN build) |

Both versions might be installed simultaneously. `list-apps` will show which one is running.

### Pattern 3: Dynamic window titles

Some apps change their window title based on content:

```
Notepad: "无标题 - 记事本" (no file open) → "report.txt - 记事本" (file open)
Chrome: "Google Chrome" → "页面标题 - Google Chrome"
File Explorer: "此电脑" → "文件夹名"
```

**For these apps**, use partial matching:
```bash
# WRONG: focus-app --name "无标题 - 记事本"  (will fail if file is open)
# RIGHT: focus-app --name "记事本"  (partial match works)
# OR: focus-app --name "Notepad" (English version)
```

### Pattern 4: When you don't know the exact name

**Step 1**: Run `list-apps` and look for the app
```bash
$PY scripts/desktop_ops.py list-apps
```

**Step 2**: If not found, the app might not be running — try to launch it:
```bash
# macOS
open -a "WeChat"

# Windows
start "" "WeChat"
```

**Step 3**: If you still don't know the name (e.g., user said "操作飞书" but you don't know if it's Feishu or Lark):
```
WebSearch: "飞书 Windows window title"
WebSearch: "Lark Windows window title"
```
Then re-run `list-apps` to confirm.

---

## Automation Approach Compatibility

| App Type | macOS AX Works? | Windows UIA Works? | Best Approach |
|----------|-----------------|--------------------|---------------|
| Native macOS (Finder, Safari, Notes) | ✅ Full UI tree | N/A | Accessibility API |
| Native Windows (Notepad, Calculator) | N/A | ✅ Usually good | Accessibility API |
| WeChat, QQ | ❌ Often sparse | ❌ Often sparse | OCR targeting |
| Electron (Slack, Discord, VS Code) | ❌ Often minimal | ⚠️ Partial / unstable | OCR targeting |
| Chrome, Edge | ❌ Minimal | ⚠️ Partial | MCP preferred, else OCR |

**When accessibility is degraded** (WeChat, QQ, Electron):
- Always fall back to `target_resolver.py` (OCR-based)
- The app process name is still needed for `focus-app`

---

## Quick Decision Tree

```
User asks to operate: "微信" / "WeChat" / "飞书" / "calculator"
            │
            ▼
Run: $PY scripts/desktop_ops.py list-apps
            │
            ▼
    ┌─────────────────────────────────┐
    │ App is in the list?             │
    └─────────────────────────────────┘
        │ YES                    │ NO
        ▼                         ▼
    Use exact name         Try to launch:
    from list-apps         macOS: open -a "WeChat"
                           Windows: start "" "WeChat"
                                │
                                ▼
                          Re-run list-apps
```

---

## Summary

1. **macOS process names** = always English, discover via `list-apps`
2. **Windows window titles** = vary by Windows language version, discover via `list-apps`
3. **Bundle IDs on macOS** = stable across languages (useful for verification)
4. **EXE names on Windows** = can be different from window title
5. **Always run `list-apps` first** — it is the source of truth
6. **When uncertain**, search for the app's window title pattern online
7. **When launching**, use the process/app name, not the window title
