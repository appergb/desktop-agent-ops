---
name: send-chat-message
description: 在聊天应用中搜索联系人并发送消息（适用于微信、Slack 等）
version: 1.0.2
author: desktop-agent-ops
platform: [macos, windows]
app: $app
tags: [chat, message, wechat, slack]
parameters:
  - name: app, required: true, description: 目标聊天应用名称（使用 list-apps 返回的准确名称）
  - name: contact, required: true, description: 联系人名称
  - name: message, required: true, description: 要发送的消息内容
  - name: send_button_text, default: "发送", description: 发送按钮文本
---

# Send Chat Message / 发送聊天消息

在聊天应用中查找联系人并发送一条消息。

## Step 1: Focus chat app

```bash
$PY $SCRIPT_DIR/desktop_ops.py focus-app --name "$app"
```

### Verify
- frontmost app matches $app

## Step 2: Get window bounds

```bash
$PY $SCRIPT_DIR/desktop_ops.py front-window-bounds --app "$app"
```

### Verify
- window bounds returned with valid x, y, width, height

## Step 3: Locate and click contact

使用 `target_resolver.py` 查找联系人并点击。
> 注意：ocr_text.py 只返回文本列表，不返回点击坐标；必须使用 target_resolver.py 才能获得 best_candidate.x/y。
> This example assumes the target conversation is already visible somewhere in the app window. If it is not visible in the sidebar, first use the app's search box manually or with a custom workflow, then return to this flow once the matching conversation row is visible.

```bash
$PY $SCRIPT_DIR/target_resolver.py --app "$app" --text "$contact" --python $PY
```

### Verify
- best_candidate found, within_window=true
- Click coordinates available as $STEP_3_best_candidate_x and $STEP_3_best_candidate_y

## Step 4: Click the contact

使用 Step 3 返回的 best_candidate 坐标点击联系人。

```bash
$PY $SCRIPT_DIR/desktop_ops.py click --x $STEP_3_best_candidate_x --y $STEP_3_best_candidate_y
```

### Verify
- conversation title/header matches $contact
- input field is visible at bottom of window

## Step 5: Locate and click input field

查找输入框区域并点击聚焦。

```bash
$PY $SCRIPT_DIR/target_resolver.py --app "$app" --label bottom_input --providers heuristic_region --python $PY
```
> 使用启发式底部输入区候选点聚焦输入框，避免对消息内容做空文本匹配。

### Verify
- best_candidate returned for input field area

## Step 6: Type the message

```bash
$PY $SCRIPT_DIR/desktop_ops.py click --x $STEP_5_x --y $STEP_5_y
$PY $SCRIPT_DIR/desktop_ops.py type --text "$message"
```

### Verify
- capture screenshot and confirm $message is visible in the input field

## Step 7: Send the message

使用可见的发送按钮。这个示例工作流不包含条件分支，因此要求目标应用存在可见的发送按钮。

```bash
$PY $SCRIPT_DIR/target_resolver.py --app "$app" --text "$send_button_text" --region-label primary_action --python $PY
```

### Verify
- best_candidate returned for send button
- coordinates available as $STEP_7_best_candidate_x and $STEP_7_best_candidate_y

## Step 8: Execute send

```bash
$PY $SCRIPT_DIR/desktop_ops.py click --x $STEP_7_best_candidate_x --y $STEP_7_best_candidate_y
```
> For macOS WeChat cases that do not expose a verified send button, follow `references/app-wechat-desktop.md` and use a separate verified `press --key return` path instead of this example workflow.

### Verify
- wait 0.5s, then capture screenshot
- outgoing message bubble containing $message appears in conversation
- message is in the correct conversation with $contact
