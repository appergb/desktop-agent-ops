---
name: open-app-and-click
description: 打开指定应用并通过 OCR 定位点击目标元素
version: 1.0.0
author: desktop-agent-ops
platform: [macos, windows, linux]
app: $app_name
tags: [generic, click, ocr]
parameters:
  - name: app_name, required: true, description: 目标应用名称
  - name: target_text, required: true, description: 要点击的按钮或元素文本
---

# Open App and Click / 打开应用并点击目标

通用工作流：打开任意应用，用 OCR 找到目标文本，然后点击。

## Step 1: Focus target app

```bash
$PY desktop_ops.py focus-app --name "$app_name"
```

### Verify
- frontmost app matches $app_name

## Step 2: Get window bounds and capture

```bash
$PY desktop_ops.py front-window-bounds --app "$app_name"
$PY desktop_ops.py capture-region --x $RESULT_X --y $RESULT_Y --width $RESULT_W --height $RESULT_H --output /tmp/app_window.png
```

### Verify
- window bounds are valid
- screenshot captured successfully

## Step 3: OCR locate target element

```bash
$PY ocr_text.py --app "$app_name" --python $PY
# 从 OCR 结果中找到包含 $target_text 的区域坐标
```

### Verify
- OCR results contain $target_text
- target coordinates are within window bounds

## Step 4: Click the target

```bash
$PY desktop_ops.py click --x $RESULT_X --y $RESULT_Y
```

### Verify
- capture screenshot after click
- UI state changed as expected (button pressed, menu opened, page navigated, etc.)
