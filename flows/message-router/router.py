"""
Message Router Module

负责消息的路由与分发，确保消息能够准确送达目标 agent。
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid


class MessageType(Enum):
    """消息类型"""
    DIRECT = "direct"           # 直接消息
    BROADCAST = "broadcast"     # 广播消息
    ROUND_ROBIN = "round_robin" # 轮询消息
    TOPIC = "topic"             # 主题消息


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Message:
    """消息结构"""
    id: str
    source_id: str
    target_id: Union[str, List[str]]
    content: Any
    msg_type: MessageType = MessageType.DIRECT
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            import time
            self.created_at = time.time()


@dataclass
class RouteRule:
    """路由规则"""
    rule_id: str
    source_pattern: str  # 支持通配符 *
    target_pattern: str
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class RoutingResult:
    """路由结果"""
    message: Message
    targets: List[str]
    routed: bool
    error: Optional[str] = None


class MessageRouter:
    """
    消息路由器
    
    负责消息的路由、分发和队列管理。
    """
    
    def __init__(self):
        self._routes: Dict[str, RouteRule] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # topic -> agent_ids
        self._message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._round_robin_index: Dict[str, int] = defaultdict(int)
        self._running = False
        self._router_task: Optional[asyncio.Task] = None
    
    def add_route(
        self,
        source_pattern: str,
        target_pattern: str,
        priority: int = 0,
        **metadata
    ) -> str:
        """
        添加路由规则
        
        Args:
            source_pattern: 源模式（如 "agent-*", "group:admins"）
            target_pattern: 目标模式
            priority: 优先级
            **metadata: 额外元数据
            
        Returns:
            str 规则 ID
        """
        rule_id = str(uuid.uuid4())
        rule = RouteRule(
            rule_id=rule_id,
            source_pattern=source_pattern,
            target_pattern=target_pattern,
            priority=priority,
            metadata=metadata
        )
        self._routes[rule_id] = rule
        return rule_id
    
    def remove_route(self, rule_id: str) -> bool:
        """移除路由规则"""
        if rule_id in self._routes:
            del self._routes[rule_id]
            return True
        return False
    
    def get_route_table(self) -> List[RouteRule]:
        """获取路由表"""
        return sorted(
            self._routes.values(),
            key=lambda r: r.priority,
            reverse=True
        )
    
    def subscribe(self, agent_id: str, topic: str):
        """订阅主题"""
        self._subscriptions[topic].add(agent_id)
    
    def unsubscribe(self, agent_id: str, topic: str):
        """取消订阅主题"""
        self._subscriptions[topic].discard(agent_id)
    
    def register_handler(self, agent_id: str, handler: Callable):
        """注册消息处理函数"""
        self._handlers[agent_id].append(handler)
    
    def unregister_handler(self, agent_id: str, handler: Callable):
        """注销消息处理函数"""
        if agent_id in self._handlers:
            self._handlers[agent_id].remove(handler)
    
    async def route_message(
        self,
        message: Message
    ) -> RoutingResult:
        """
        路由消息
        
        Args:
            message: 要路由的消息
            
        Returns:
            RoutingResult 路由结果
        """
        try:
            targets = await self._resolve_targets(message)
            
            if not targets:
                return RoutingResult(
                    message=message,
                    targets=[],
                    routed=False,
                    error="No valid targets found"
                )
            
            # 根据消息类型处理
            if message.msg_type == MessageType.BROADCAST:
                await self._deliver_to_all(targets, message)
            elif message.msg_type == MessageType.ROUND_ROBIN:
                target = await self._deliver_round_robin(targets, message)
                targets = [target] if target else []
            else:
                await self._deliver_to_all(targets, message)
            
            return RoutingResult(
                message=message,
                targets=targets,
                routed=True
            )
            
        except Exception as e:
            return RoutingResult(
                message=message,
                targets=[],
                routed=False,
                error=str(e)
            )
    
    async def _resolve_targets(self, message: Message) -> List[str]:
        """解析消息目标"""
        targets = []
        
        # 直接指定目标
        if isinstance(message.target_id, str):
            targets = [message.target_id]
        elif isinstance(message.target_id, list):
            targets = message.target_id
        
        # 广播到特定主题
        if message.msg_type == MessageType.TOPIC:
            topic = message.metadata.get("topic", "")
            if topic in self._subscriptions:
                targets = list(self._subscriptions[topic])
        
        # 应用路由规则
        for rule in self._routes.values():
            if not rule.enabled:
                continue
            if self._match_pattern(message.source_id, rule.source_pattern):
                resolved = await self._resolve_pattern(rule.target_pattern)
                targets.extend(resolved)
        
        # 去重
        return list(set(targets))
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """匹配模式（支持 * 通配符）"""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
    
    async def _resolve_pattern(self, pattern: str) -> List[str]:
        """解析模式获取目标列表"""
        # 如果是通配符模式，从注册表查找
        if '*' in pattern:
            from ..agent_manager.registry import get_registry
            registry = get_registry()
            agents = await registry.find_all()
            return [
                agent.id for agent in agents
                if self._match_pattern(agent.name, pattern) or 
                   self._match_pattern(agent.agent_type, pattern)
            ]
        return [pattern]
    
    async def _deliver_to_all(
        self,
        targets: List[str],
        message: Message
    ):
        """向所有目标投递消息"""
        for target_id in targets:
            await self._deliver_to_target(target_id, message)
    
    async def _deliver_round_robin(
        self,
        targets: List[str],
        message: Message
    ) -> Optional[str]:
        """轮询投递消息"""
        if not targets:
            return None
        
        # 创建一致的 key
        key = f"{message.source_id}:{message.target_id}"
        index = self._round_robin_index[key]
        target = targets[index % len(targets)]
        
        # 更新索引
        self._round_robin_index[key] = (index + 1) % len(targets)
        
        await self._deliver_to_target(target, message)
        return target
    
    async def _deliver_to_target(self, target_id: str, message: Message):
        """向单个目标投递消息"""
        handlers = self._handlers.get(target_id, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception:
                pass  # 不让 handler 错误影响路由
    
    async def start(self):
        """启动路由器"""
        self._running = True
        self._router_task = asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """停止路由器"""
        self._running = False
        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass
    
    async def _process_queue(self):
        """处理消息队列"""
        while self._running:
            try:
                _, message = await self._message_queue.get()
                await self.route_message(message)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
    
    async def enqueue(self, message: Message, delay: float = 0.0):
        """将消息加入队列"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        priority = message.priority.value
        await self._message_queue.put((priority, message))


# 便捷函数
def create_message(
    source_id: str,
    target_id: Union[str, List[str]],
    content: Any,
    msg_type: MessageType = MessageType.DIRECT,
    **kwargs
) -> Message:
    """创建消息的便捷函数"""
    return Message(
        id=str(uuid.uuid4()),
        source_id=source_id,
        target_id=target_id,
        content=content,
        msg_type=msg_type,
        **kwargs
    )


async def route_message(
    message: Message,
    router: MessageRouter = None
) -> RoutingResult:
    """路由消息的便捷函数"""
    if router is None:
        router = MessageRouter()
    return await router.route_message(message)


__all__ = [
    'MessageType', 'MessagePriority', 'Message',
    'RouteRule', 'RoutingResult', 'MessageRouter',
    'create_message', 'route_message'
]
