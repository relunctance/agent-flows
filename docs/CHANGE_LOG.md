# 变更历史

最后更新: 2025-05-15

---

## 2025-05-15

### 新增

- **CLI 实现**: `agent_flows/cli/` 目录及 `list.py`, `load.py`, `status.py`
  - `python -m agent_flows.cli list` - 列出所有 flow
  - `python -m agent_flows.cli load <flow> <team>` - 绑定 flow 到团队
  - `python -m agent_flows.cli status <team>` - 获取团队当前阶段
  - 团队状态存储在 `~/.agent-flows/teams/`

- **docs/ 目录结构**: 按照 dir-skill 规范创建标准项目目录
  - `docs/PRD/` - 产品需求文档
  - `docs/decisions/` - 关键决策记录
  - `assets/` - 设计素材和参考资料
  - `learns/` - 学习笔记
  - `scripts/` - 运维脚本
  - `logs/` - 日志文件

- **AGENTS.md**: 新增 AI Agent 工作入口文件

- **docs/ARCHITECTURE.md**: 新增架构文档，描述 Agent Flows 与 Expert Teams 的集成架构

- **docs/decisions/2025-05-15-cli-interface-pattern.md**: 新增 ADR-001，记录 Command Interface 模式决策

- **docs/CLI_IMPLEMENTATION.md**: 新增 CLI 实现计划文档

### 规划中

- 实现 CLI 命令 (list/load/status)
- 创建 Python SDK
- 支持更多 Flow 类型 (legal-consultation, stock-analysis)

---

## 2025-05-14

### 新增

- **flows/software-dev.toml**: 软件研发流程定义
- **flows/agent-manager/**: Agent 管理 Flow
- **flows/message-router/**: 消息路由 Flow
- **flows/session-manager/**: 会话管理 Flow
- **schemas/flow.schema.json**: Flow 定义 JSON Schema
- **schemas/phase.schema.json**: Phase 定义 JSON Schema
- **DEVELOPMENT_GUIDE.md**: 开发指南
- **SCHEMA.md**: Schema 定义规范
