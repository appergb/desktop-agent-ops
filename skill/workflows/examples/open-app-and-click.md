---
name: open-app-and-click
description: 打开指定应用并通过 OCR 定位点击目标元素
version: 1.0.1
author: desktop-agent-ops
platform: [macos, windows, linux]
app: $app_name
tags: [generic, click, ocr]
parameters:
  - name: app_name, required: true, description: 目标应用名称
  - name: target_text, required: true, description: 要点击的按钮或元素文本
---

# Open App and Click / 打开应用并点击目标

通用工作流：打开任意应用，用 target_resolver 找到目标文本的精确坐标，然后点击。

> ⚠️ 重要：不要使用 ocr_text.py + $RESULT_X/$RESULT_Y 组合。
> ocr_text.py 只返回文本列表，坐标嵌套在 boxes[].abs_box 中，不返回顶层 x/y 字段。
> 必须使用 target_resolver.py，它返回 best_candidate.x 和 best_candidate.y 作为可直接引用的顶层字段。

## Step 1: Focus target app

```bash
$PY $SCRIPT_DIR/desktop_ops.py focus-app --name "$app_name"
```

### Verify
- frontmost app matches $app_name

## Step 2: Get window bounds

```bash
$PY $SCRIPT_DIR/desktop_ops.py front-window-bounds --app "$app_name"
```

### Verify
- window bounds are valid (x, y, width, height)

## Step 3: Locate target element

使用 target_resolver.py 查找目标文本，返回 best_candidate.x/y。
传入 --text "$target_text" 过滤只返回匹配目标元素的坐标。

```bash
$PY $SCRIPT_DIR/target_resolver.py --app "$app_name" --text "$target_text" --python $PY
```

### Verify
- best_candidate found, within_window=true
- coordinates available as $STEP_3_best_candidate_x and $STEP_3_best_candidate_y

## Step 4: Click the target

使用 Step 3 返回的 best_candidate 坐标执行点击。

```bash
$PY $SCRIPT_DIR/desktop_ops.py click --x $STEP_3_best_candidate_x --y $STEP_3_best_candidate_y
```

### Verify
- capture screenshot after click
- UI state changed as expected (button pressed, menu opened, page navigated, etc.)
