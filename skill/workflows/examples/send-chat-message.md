---
name: send-chat-message
description: 在聊天应用中搜索联系人并发送消息（适用于微信、Slack 等）
version: 1.0.0
author: desktop-agent-ops
platform: [macos, windows]
app: $app
tags: [chat, message, wechat, slack]
parameters:
  - name: app, default: "微信", description: 目标聊天应用名称
  - name: contact, required: true, description: 联系人名称
  - name: message, required: true, description: 要发送的消息内容
---

# Send Chat Message / 发送聊天消息

在聊天应用中查找联系人并发送一条消息。

## Step 1: Focus chat app

```bash
$PY desktop_ops.py focus-app --name "$app"
```

### Verify
- frontmost app matches $app

## Step 2: Get window bounds

```bash
$PY desktop_ops.py front-window-bounds --app "$app"
```

### Verify
- window bounds returned with valid x, y, width, height

## Step 3: Search for contact

```bash
# 使用 Cmd+F 或点击搜索栏搜索联系人
$PY desktop_ops.py hotkey --keys cmd f
$PY desktop_ops.py type --text "$contact"
```

### Verify
- capture screenshot and confirm search results contain $contact

## Step 4: Click the contact

```bash
# 用 OCR 定位联系人，然后点击
$PY ocr_text.py --app "$app" --python $PY
$PY desktop_ops.py click --x $RESULT_X --y $RESULT_Y
```

### Verify
- conversation title/header matches $contact
- input field is visible at bottom of window

## Step 5: Type the message

```bash
# 点击输入框区域后输入消息
$PY desktop_ops.py click --x $RESULT_X --y $RESULT_Y
$PY desktop_ops.py type --text "$message"
```

### Verify
- capture screenshot and confirm $message is visible in the input field

## Step 6: Send the message

```bash
$PY desktop_ops.py press --key return
```

### Verify
- wait 0.5s, then capture screenshot
- outgoing message bubble containing $message appears in conversation
- message is in the correct conversation with $contact
