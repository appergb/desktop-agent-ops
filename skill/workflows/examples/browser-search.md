---
name: browser-search
description: 打开浏览器并执行搜索查询
version: 1.0.0
author: desktop-agent-ops
platform: [macos, windows, linux]
app: $browser
tags: [browser, search, web]
parameters:
  - name: browser, default: "Safari", description: 浏览器应用名称
  - name: query, required: true, description: 搜索关键词
  - name: address_bar_modifier, default: "cmd", description: macOS 用 cmd，Windows/Linux 通常用 ctrl
---

# Browser Search / 浏览器搜索

打开指定浏览器，在地址栏中输入搜索词并查看结果。

## Step 1: Focus browser

```bash
$PY $SCRIPT_DIR/desktop_ops.py focus-app --name "$browser"
```

### Verify
- frontmost app matches $browser

## Step 2: Activate address bar

```bash
$PY $SCRIPT_DIR/desktop_ops.py hotkey --keys $address_bar_modifier l
```

### Verify
- address bar is highlighted / has focus

## Step 3: Type search query

```bash
$PY $SCRIPT_DIR/desktop_ops.py type --text "$query"
```

### Verify
- capture screenshot and confirm $query is visible in address bar

## Step 4: Execute search

```bash
$PY $SCRIPT_DIR/desktop_ops.py press --key return
```

### Verify
- wait for page load, then capture screenshot
- search results page is visible
- page title or content relates to $query

## Step 5: Capture search results

```bash
$PY $SCRIPT_DIR/desktop_ops.py screenshot --output /tmp/search_result.png
```

### Verify
- screenshot saved successfully
- search results are readable in the captured image
