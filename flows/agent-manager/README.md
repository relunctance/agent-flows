# Agent Manager

管理 agent 的生命周期，包括创建、启动、停止、销毁等核心操作。

## 职责

- Agent 实例的创建与初始化
- Agent 状态的监控与管理
- Agent 资源的分配与释放
- Agent 故障检测与恢复

## 核心功能

- `create_agent()` — 创建新的 agent 实例
- `start_agent()` — 启动 agent
- `stop_agent()` — 停止 agent
- `destroy_agent()` — 销毁 agent
- `get_agent_status()` — 获取 agent 状态
