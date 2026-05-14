# Session Manager

管理 agent 之间的会话生命周期，维护会话状态和上下文。

## 职责

- 会话的创建与销毁
- 会话状态的持久化
- 会话上下文的维护
- 多 agent 会话协调

## 核心功能

- `create_session()` — 创建新会话
- `get_session()` — 获取会话信息
- `update_session()` — 更新会话状态
- `close_session()` — 关闭会话
- `list_sessions()` — 列出所有会话
