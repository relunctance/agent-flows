# Agent Flows

> 多阶段工作流程定义与执行框架

## 项目概览

- **项目名称**: Agent Flows
- **描述**: 定义多阶段工作流程的规范，支持软件研发、律师咨询、股票分析等多种团队类型
- **状态**: 规划中
- **最后更新**: 2025-05-15

## 快速开始

### 查看可用 Flow

```bash
python -m agent_flows.cli list
```

### 加载 Flow 到团队

```bash
python -m agent_flows.cli load <flow-name> <team-id>
```

### 查看团队当前阶段

```bash
python -m agent_flows.cli status <team-id>
```

## 目录结构

```
agent-flows/
├── flows/              # Flow 定义文件 (*.toml)
├── cli/                # 命令行接口
├── sdk/                # Python SDK
├── docs/               # 项目文档
│   ├── ARCHITECTURE.md # 系统架构
│   ├── CHANGE_LOG.md   # 变更历史
│   └── TODO.md         # 待办事项
└── schemas/            # JSON Schema
```

## Flow 定义规范

Flow 使用 TOML 格式定义，参考 `flows/software-dev.toml`

## 当前冲刺

- [ ] 实现 CLI 命令 (list/load/status)
- [ ] 创建 Python SDK
- [ ] 编写详细文档

## 计划中

- [ ] 支持 flow 版本管理
- [ ] 支持 flow 模板
- [ ] 支持 flow 可视化

## 变更历史

详见 `docs/CHANGE_LOG.md`
