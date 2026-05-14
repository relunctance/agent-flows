# Message Router

负责消息的路由与分发，确保消息能够准确送达目标 agent。

## 职责

- 消息路由规则的定义与管理
- 消息的转发与分发
- 路由策略的动态调整
- 消息队列管理

## 核心功能

- `route_message()` — 根据规则路由消息
- `add_route()` — 添加路由规则
- `remove_route()` — 移除路由规则
- `get_route_table()` — 获取路由表
