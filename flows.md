# Agent Flows 编排流程

整体编排流程说明，描述各个模块如何协同工作。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                      Agent Flows                         │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ Agent Manager │  │Message Router │  │Session Mgr  │  │
│  └───────────────┘  └───────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 模块职责

### Agent Manager
负责 agent 的生命周期管理，是整个系统的核心组件。

### Message Router
负责消息的路由与分发，连接各个 agent 之间的通信。

### Session Manager
维护会话状态和上下文，支持多 agent 协作。

## 协作流程

1. **初始化阶段**：Session Manager 创建会话，Agent Manager 创建并启动 agent
2. **运行阶段**：Message Router 负责消息路由，Session Manager 维护上下文
3. **结束阶段**：Agent Manager 停止并销毁 agent，Session Manager 关闭会话

## 数据流

```
User Input → Session Manager → Message Router → Agent Manager → Agent
                ↑                                         ↓
                └───────────── Response ←─────────────────┘
```
