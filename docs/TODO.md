# Agent Flows 待办事项

## 当前冲刺

### CLI 实现

- [ ] 创建 CLI 目录结构 (`agent_flows/cli/`)
- [ ] 实现 `python -m agent_flows.cli list` 命令
- [ ] 实现 `python -m agent_flows.cli load <flow> <team>` 命令
- [ ] 实现 `python -m agent_flows.cli status <team>` 命令
- [ ] 添加 toml 依赖到项目
- [ ] 编写 CLI 测试用例
- [ ] 验证 list/load/status 命令

### Expert Teams 集成

- [ ] 在 expert-teams 的 manual_mode.py 中添加 `flow list` 命令
- [ ] 在 expert-teams 的 manual_mode.py 中添加 `flow load` 命令
- [ ] 在 expert-teams 的 manual_mode.py 中添加 `phase` 命令
- [ ] 测试 expert-teams 与 agent-flows CLI 的集成

## 计划中

### Flow 定义

- [ ] `flows/legal-consultation.toml` - 律师咨询流程
- [ ] `flows/stock-analysis.toml` - 股票分析流程

### SDK 开发

- [ ] 创建 `sdk/` 目录
- [ ] 实现 Flow 加载器
- [ ] 实现 Phase 状态管理
- [ ] 编写 SDK 文档

### 高级功能

- [ ] 支持 flow 版本管理
- [ ] 支持 flow 模板
- [ ] 支持 flow 可视化
- [ ] 支持 flow 导入/导出

## 已完成

### 项目初始化

- [x] 创建标准项目目录结构 (docs/, assets/, learns/, scripts/, logs/)
- [x] 创建 AGENTS.md 入口文件
- [x] 创建 docs/ARCHITECTURE.md 架构文档
- [x] 创建 docs/decisions/ADR-001 CLI 接口模式决策
- [x] 创建 docs/CLI_IMPLEMENTATION.md CLI 实现计划
- [x] 创建 docs/CHANGE_LOG.md 变更历史
