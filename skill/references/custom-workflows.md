# Custom Workflows / 自定义工作流指南

## What are workflows? / 什么是工作流

工作流（Workflow）是用 Markdown 编写的可复用桌面自动化脚本。每个工作流定义了一组有序步骤，
AI Agent 按顺序执行并在每步之后验证结果。工作流让你可以把常用的桌面操作固化为模板，
避免每次从零开始描述任务。

Benefits / 优势:
- 可复用：写一次，反复执行
- 可验证：每步都有验证条件，出错即停
- 可分享：纯文本格式，易于版本管理和团队共享
- 跨平台：通过 platform 字段适配不同操作系统

## File format / 文件格式

工作流文件由两部分组成：YAML 前置元数据 + Markdown 步骤正文。

```markdown
---
name: my-workflow
description: 工作流简要描述
version: 1.0.0
author: your-name
platform: [macos, windows, linux]
app: $app
tags: [tag1, tag2]
parameters:
  - name: app, default: "Safari", description: 目标应用
  - name: query, required: true, description: 搜索关键词
---

# Workflow Title

简要说明这个工作流做什么。

## Step 1: First action

\```bash
$PY desktop_ops.py focus-app --name "$app"
\```

### Verify
- expected outcome description
```

## Frontmatter fields / 元数据字段

| Field         | Required | Type         | Description                           |
|---------------|----------|--------------|---------------------------------------|
| `name`        | Yes      | string       | 工作流唯一标识名（英文、连字符）         |
| `description` | Yes      | string       | 简要描述工作流用途                      |
| `version`     | No       | string       | 语义化版本号，如 `1.0.0`               |
| `author`      | No       | string       | 作者名称                               |
| `platform`    | No       | list         | 支持的平台: `macos`, `windows`, `linux` |
| `app`         | No       | string       | 目标应用名称，可用 `$param` 引用参数     |
| `tags`        | No       | list         | 分类标签，便于搜索发现                   |
| `parameters`  | No       | list of dict | 参数定义列表（见下方说明）               |

### Parameter definition / 参数定义

每个参数是一个字典，支持以下字段：

- `name` — 参数名（必填），在步骤中用 `$name` 引用
- `required` — 是否必填，`true` 或 `false`
- `default` — 默认值（可选）
- `description` — 参数说明

## Steps / 步骤定义

每个步骤用二级标题定义，格式为 `## Step N: Title`。

步骤包含：
1. **命令块** — 用 ` ```bash ` 代码块包裹的 shell 命令
2. **验证段**（可选）— 用 `### Verify` 标题加无序列表描述期望结果

步骤编号必须递增且不重复。每个步骤至少包含一条命令。

## Variable substitution / 变量替换

工作流中可使用以下变量：

| Variable     | Description                                    |
|--------------|------------------------------------------------|
| `$PY`        | Python 解释器路径（由 first_run_setup 设置）      |
| `$app`       | 目标应用名称（若在 frontmatter 中声明）            |
| `$param_name`| 任何在 parameters 中声明的参数                    |
| `$RESULT_X`  | 上一步返回的 X 坐标                              |
| `$RESULT_Y`  | 上一步返回的 Y 坐标                              |
| `$RESULT_W`  | 上一步返回的宽度                                  |
| `$RESULT_H`  | 上一步返回的高度                                  |

## Where to save / 存放位置

- **社区/内置工作流**: `skill/workflows/` 及其子目录（随项目发布）
- **用户自定义工作流**: `~/.openclaw-desktop-agent-ops/workflows/`

用户目录中的工作流优先级高于社区工作流（同名时用户版本覆盖社区版本）。

## CLI commands / 命令行操作

通过 `workflow_loader.py` 管理工作流：

```bash
# 列出所有可用工作流
$PY workflow_loader.py discover

# 加载并显示工作流详情
$PY workflow_loader.py load --workflow send-chat-message

# 验证工作流格式是否正确
$PY workflow_loader.py validate --workflow send-chat-message
```

## Tips for writing good workflows / 编写技巧

1. **小步快跑** — 每步只做一个动作，不要在一步中串联多个操作
2. **先观察后操作** — 在点击之前先截图确认目标位置
3. **必写验证** — 每步都加 `### Verify`，确保出错时能及时发现
4. **参数化** — 把应用名、搜索词等可变部分提取为 parameters
5. **跨平台** — 用 `platform` 字段标注支持的系统，快捷键注意 Cmd/Ctrl 差异
6. **保持幂等** — 工作流应能安全重复执行，不产生副作用
7. **写好描述** — description 和 tags 帮助其他用户找到你的工作流
8. **先测试** — 用 `validate` 命令检查格式，再实际运行验证效果
