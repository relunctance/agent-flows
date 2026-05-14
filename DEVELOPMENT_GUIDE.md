# Flows 打磨指南

> 如何创建、验证和迭代多阶段工作流程

---

## 概述

本指南帮助你理解如何为 Expert Teams 打磨高质量的流程。

**流程（Flow）** 是完整的工作过程定义，由多个**阶段（Phase）**组成，每个阶段有明确的责任人和评审机制。

---

## 目录结构

```
agent-flows/
├── flows/                      # 流程定义文件
│   └── {flow-name}.toml       # 单个流程文件
├── schemas/                   # JSON Schema 验证文件
├── validators/                # 校验工具
│   ├── validate_flow.py       # 流程校验
│   └── check_consistency.py   # 一致性检查
└── templates/                # 流程模板
    └── flow-template.toml
```

---

## 创建新流程

### 1. 使用模板

```bash
# 复制模板
cp templates/flow-template.toml flows/my-new-flow.toml
```

### 2. 编辑流程文件

```toml
[flow]
name = "my-new-flow"           # 唯一标识符（小写字母、数字、连字符）
display_name = "我的新流程"
description = "流程描述"

[[phases]]
name = "phase-1"              # 阶段唯一标识符
display_name = "阶段1"
description = "阶段描述"

[phases.roles]
owner = "architect"            # 主负责人（必须）
reviewer = "delivery-director" # 评审人（可选）
executor = "architect"        # 执行人（可选，默认等于 owner）

[phases.skills]
required = ["brainstorming"]   # 必须安装的 skills
recommended = ["writing-plans"] # 建议安装的 skills

[phases.artifacts]
output_dir = "artifacts/phase-1"  # 产物输出目录
versioned = true                    # 是否启用版本管理
files = ["*.md"]                    # 预期的产物文件

[phases.review]
required = true                # 是否必须评审
auto_advance = false          # 评审通过后是否自动进入下一阶段
reject_action = "revise"      # 评审不通过时的处理
human_required = false         # 是否需要人类审批
escalate_to = "delivery-director"  # 评审升级到的角色

# 阶段依赖（可选）
[phases.blocked_by]
phases = ["前一个阶段"]
```

---

## 阶段（Phase）设计原则

### 1. 每个阶段只有一个 Owner

❌ 避免：
```toml
[phases.roles]
owner = "architect"
reviewer = "engineer"  # 模糊：谁最终负责？
```

✅ 推荐：
```toml
[phases.roles]
owner = "architect"     # architect 负责
reviewer = "engineer"   # engineer 评审
executor = "architect"  # architect 执行
```

### 2. 明确评审边界

每个阶段应该定义：
- **什么时候需要评审？** (`required`)
- **评审不通过怎么办？** (`reject_action`)
- **谁来评审？** (`reviewer`)

```toml
[phases.review]
required = true
reject_action = "revise"        # 打回重做，不跳过
human_required = false          # 不需要人类审批
escalate_to = "delivery-director"  # 升级到这里
```

### 3. 合理设置 blocked_by

使用 `blocked_by` 表示**真正的依赖**，不是时间顺序：

```toml
# 正确的依赖
[[phases]]
name = "implement"
blocked_by = ["plan"]  # 实现依赖计划

[[phases]]
name = "test"
blocked_by = ["implement"]  # 测试依赖实现
```

❌ 避免：把 `blocked_by` 当作"必须先做 Phase A 再做 Phase B"

---

## 打磨流程的最佳实践

### 1. 从简单开始

❌ 避免：一开始就创建复杂的 10 阶段流程

✅ 推荐：从 2-3 个核心阶段开始，逐步扩展

```
simple-flow:
  phase-1 (plan)     →  phase-2 (implement)  →  phase-3 (test)
```

### 2. 每个阶段有明确的产物

每个阶段应该产出明确的**产物（Artifacts）**：

```toml
[phases.artifacts]
output_dir = "artifacts/plan"
files = ["plan.md", "tasks.yaml"]
```

产物应该：
- **可验证**：能检查是否完成
- **可传递**：下游阶段能使用
- **有版本**：启用 `versioned = true`

### 3. 描述阶段的"完成标准"

在 `description` 中说明阶段何时算完成：

```toml
[[phases]]
name = "plan"
description = """
规划阶段完成标准：
1. 需求已澄清，所有疑问已回答
2. 任务已分解，每个任务 5-10 分钟
3. 架构决策已记录到 ADR
4. 计划已获得 delivery-director 批准
"""
```

### 4. 合理使用 skills

阶段应该有明确的 skills 要求：

```toml
[phases.skills]
required = ["superpowers:writing-plans"]
recommended = ["superpowers:systematic-debugging"]
```

**注意**：skill 名称应该与实际安装的 skill 匹配。

---

## 验证流程

### 自动校验

```bash
# 校验流程文件格式
python validators/validate_flow.py flows/my-new-flow.toml

# 检查一致性（角色是否存在、blocked_by 是否循环等）
python validators/check_consistency.py flows/my-new-flow.toml

# 使用 spawn_team.py 的 --validate-only
python scripts/spawn_team.py --flow my-new-flow --validate-only
```

### 手动检查清单

- [ ] 流程文件通过 JSON Schema 校验
- [ ] 每个阶段的 `owner` 角色存在
- [ ] 每个阶段的 `reviewer` 角色存在
- [ ] `blocked_by` 没有循环依赖
- [ ] 阶段的 `skills` 中引用的 skill 都存在
- [ ] 阶段的产物目录合理

---

## 常见问题

### Q: 流程太长了怎么办？

**A:** 考虑拆分成子流程：

```toml
# 主流程
[flow]
name = "software-dev"
display_name = "软件研发流程"

[[phases]]
name = "plan"
# ... 计划阶段

[[phases]]
name = "implement"
# ... 实现阶段

[[phases]]
name = "release"
# ... 发布阶段

# 但是 implement 本身可以是一个完整的小流程
```

### Q: 阶段之间有太多依赖怎么办？

**A:** 审查是否真的需要依赖：

1. **真正的依赖**：A 的输出是 B 的输入
2. **时间顺序**：只是先 A 后 B，不代表依赖

真正的依赖：
```
implement (输出代码) → test (需要代码作为输入)
```

非真正依赖：
```
plan → design  # 只是习惯先计划再设计，但不是 plan 输出 design 输入
```

### Q: 如何决定评审时机？

**A:** 以下情况需要评审：

| 情况 | 评审类型 |
|------|----------|
| 架构决策 | 必须评审，影响深远 |
| 大规模重构 | 必须评审，风险高 |
| 小 bug fix | 可选，快速迭代 |
| 文档更新 | 可跳过或简化为同行 review |

---

## 迭代流程

### 1. 创建流程（v0.1）
```bash
cp templates/flow-template.toml flows/new-flow.toml
```

### 2. 定义基本结构
- 设计阶段数量
- 定义每个阶段的角色
- 设置基本的 blocked_by 关系

### 3. 在团队中测试
```bash
python spawn_team.py --team-name test --goal "测试" --flow new-flow
```

### 4. 观察执行
- 阶段之间是否有死锁？
- 评审是否太频繁/太少？
- 产物是否正确传递？

### 5. 迭代改进

根据观察调整：
- 增加/减少阶段
- 调整评审时机
- 修改角色分配

---

## Flow 与 Role 的关系

Flow 定义**做什么**，Role 定义**谁来做**。

```
Flow: 阶段 1 (owner=architect) → 阶段 2 (owner=engineer)
Role: architect 有架构设计技能，engineer 有编码技能
```

好的设计：
- Flow 关注流程逻辑，不关心具体实现
- Role 关注职责和技能，可复用于多个 Flow

---

## 参考

- [SCHEMA.md](./SCHEMA.md) - 流程定义规范
- [Expert Teams](https://github.com/relunctance/expert-teams)
- [Superpowers](https://github.com/obra/superpowers) - 开发方法论 skills
