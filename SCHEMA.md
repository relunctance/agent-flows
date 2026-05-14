# Agent Flows 流程定义规范

## 概述

Agent Flows 是一个用于定义多阶段工作流程的规范。每个流程由多个阶段（Phase）组成，每个阶段有明确的责任人、评审机制和产物要求。

## 核心概念

### 流程（Flow）

流程是完整的工作过程定义，包含多个有序的阶段。

### 阶段（Phase）

阶段是流程中的一个工作单元，有明确的责任人和可定义的评审机制。

## 目录结构

```
agent-flows/
├── flows/                      # 流程定义文件
│   └── {flow-name}.toml
├── schemas/                   # JSON Schema 验证文件
│   ├── flow.schema.json
│   └── phase.schema.json
├── validators/                # 校验工具
│   ├── validate_flow.py
│   └── check_consistency.py
└── templates/                # 模板文件
    └── flow-template.toml
```

## Flow 文件格式

```toml
# Flow 定义
[flow]
name = "流程唯一标识符"           # 小写字母、数字、连字符
display_name = "人类可读名称"
description = "流程描述"

# 流程阶段定义
[[phases]]
name = "阶段唯一标识符"
display_name = "阶段显示名称"
description = "阶段描述"

# 阶段角色配置
[phases.roles]
owner = "角色名"                 # 主负责人（必须）
reviewer = "角色名"              # 评审人（可选，为 null 表示不需要评审）
executor = "角色名"             # 执行人（可选，默认等于 owner）

# 阶段技能要求
[phases.skills]
required = ["skill-1", "skill-2"]    # 必须安装的 skills
recommended = ["skill-3"]              # 建议安装的 skills（可选）

# 阶段产物配置
[phases.artifacts]
output_dir = "artifacts/阶段名"      # 产物输出目录
versioned = true                        # 是否启用版本管理（默认 true）
files = ["*.md", "*.yaml"]              # 预期的产物文件模式（可选）

# 阶段依赖配置
blocked_by = ["前置阶段名"]            # 依赖的前置阶段（可选）

# 评审配置
[phases.review]
required = true                       # 是否必须评审（默认 false）
auto_advance = false                  # 评审通过后是否自动进入下一阶段（默认 false）
reject_action = "revise"             # 评审不通过时的处理：revise | skip | abort
human_required = false               # 是否需要人类审批（默认 false）
escalate_to = "角色名"               # 评审升级到的角色（可选）
```

## 字段说明

### flow 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| name | string | 是 | 唯一标识符，只能包含小写字母、数字、连字符 |
| display_name | string | 是 | 人类可读的显示名称 |
| description | string | 否 | 流程的详细描述 |

### phases 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| name | string | 是 | 阶段唯一标识符 |
| display_name | string | 是 | 人类可读的阶段名称 |
| description | string | 否 | 阶段的详细描述 |
| roles | object | 是 | 角色配置（见下表） |
| skills | object | 否 | 技能要求配置 |
| artifacts | object | 否 | 产物配置 |
| blocked_by | array | 否 | 前置依赖阶段列表 |
| review | object | 否 | 评审配置 |

### phases.roles 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| owner | string | 是 | 主负责人角色名 |
| reviewer | string/null | 否 | 评审人角色名，null 表示不需要评审 |
| executor | string | 否 | 执行人，默认等于 owner |

### phases.skills 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| required | array | 是 | 必须安装的 skills 列表 |
| recommended | array | 否 | 建议安装的 skills 列表 |

### phases.artifacts 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| output_dir | string | 是 | 产物输出目录，相对于 workspace |
| versioned | boolean | 否 | 是否启用版本管理，默认 true |
| files | array | 否 | 预期的产物文件模式 |

### phases.review 字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| required | boolean | 否 | 是否必须评审，默认 false |
| auto_advance | boolean | 否 | 评审通过后是否自动进入下一阶段，默认 false |
| reject_action | string | 否 | 评审不通过时的处理：revise/skip/abort，默认 revise |
| human_required | boolean | 否 | 是否需要人类审批，默认 false |
| escalate_to | string | 否 | 评审升级到的角色 |

### reject_action 可选值

| 值 | 说明 |
|----|------|
| revise | 打回给执行人重做（推荐） |
| skip | 跳过评审继续（危险操作） |
| abort | 终止流程（用于关键节点） |

## 示例

```toml
# flows/software-dev.toml

[flow]
name = "software-dev"
display_name = "软件研发流程"
description = "适用于软件开发项目的标准流程"

[[phases]]
name = "plan"
display_name = "规划阶段"
description = "需求分析、任务分解、架构设计"

[phases.roles]
owner = "architect"
reviewer = "delivery-director"
executor = "architect"

[phases.skills]
required = ["brainstorming", "writing-plans"]
recommended = ["systematic-debugging"]

[phases.artifacts]
output_dir = "artifacts/plan"
versioned = true
files = ["plan.md", "tasks.yaml"]

[phases.review]
required = true
auto_advance = false
reject_action = "revise"
escalate_to = "delivery-director"

[[phases]]
name = "implement"
display_name = "实现阶段"
description = "编码实现"

[phases.roles]
owner = "engineer"
reviewer = "architect"
executor = "engineer"

[phases.skills]
required = ["test-driven-development", "writing-plans"]
recommended = ["systematic-debugging", "requesting-code-review"]

[phases.artifacts]
output_dir = "artifacts/implement"
versioned = true
files = ["src/**"]

[phases.review]
required = true
reject_action = "revise"

[phases.blocked_by]
phases = ["plan"]

[[phases]]
name = "test"
display_name = "测试阶段"
description = "集成测试、质量验证"

[phases.roles]
owner = "qa"
reviewer = "delivery-director"
executor = "qa"

[phases.skills]
required = ["verification-before-completion", "test-driven-development"]

[phases.artifacts]
output_dir = "artifacts/test"
versioned = true
files = ["test-report.md", "coverage.json"]

[phases.review]
required = false
auto_advance = true

[phases.blocked_by]
phases = ["implement"]

[[phases]]
name = "release"
display_name = "发布阶段"
description = "部署上线"

[phases.roles]
owner = "delivery-director"
executor = "delivery-director"

[phases.review]
required = true
human_required = true
auto_advance = false
reject_action = "abort"

[phases.blocked_by]
phases = ["test"]
```

## 校验

使用 `validators/validate_flow.py` 校验流程文件：

```bash
python validators/validate_flow.py flows/software-dev.toml
```

## 贡献指南

1. Fork agent-flows 仓库
2. 在 `flows/` 目录下创建新的流程文件
3. 确保通过 Schema 校验
4. 提交 Pull Request

## 许可

MIT License
