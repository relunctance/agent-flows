"""
Agent Creation Module

负责使用 delegate_task spawn 创建新的 agent 实例。
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class AgentState(Enum):
    """Agent 状态枚举"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    IDLE = "idle"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str
    agent_type: str
    max_retries: int = 3
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """Agent 实例"""
    id: str
    name: str
    agent_type: str
    state: AgentState = AgentState.PENDING
    config: Optional[AgentConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[float] = None
    last_heartbeat: Optional[float] = None


class AgentCreator:
    """Agent 创建器"""
    
    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry
        self._spawn_callback: Optional[Callable] = None
    
    def set_spawn_callback(self, callback: Callable):
        """设置 spawn 回调函数（delegate_task spawn）"""
        self._spawn_callback = callback
    
    async def create_agent(
        self,
        name: str,
        agent_type: str,
        config: Optional[AgentConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        创建新的 agent 实例
        
        Args:
            name: agent 名称
            agent_type: agent 类型
            config: agent 配置
            metadata: 额外元数据
            
        Returns:
            创建的 Agent 实例
        """
        agent_id = str(uuid.uuid4())
        
        if config is None:
            config = AgentConfig(name=name, agent_type=agent_type)
        
        agent = Agent(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            state=AgentState.INITIALIZING,
            config=config,
            metadata=metadata or {},
            created_at=asyncio.get_event_loop().time()
        )
        
        # 注册到注册表
        await self.registry.register(agent)
        
        # 使用 spawn 回调启动 agent
        if self._spawn_callback:
            asyncio.create_task(self._spawn_callback(agent))
        else:
            # 默认启动逻辑
            agent.state = AgentState.RUNNING
            agent.last_heartbeat = asyncio.get_event_loop().time()
        
        return agent
    
    async def create_agent_with_task(
        self,
        name: str,
        agent_type: str,
        task_func: Callable,
        **kwargs
    ) -> Agent:
        """
        创建 agent 并关联任务函数
        
        Args:
            name: agent 名称
            agent_type: agent 类型
            task_func: 任务函数（用于 delegate_task spawn）
            **kwargs: 传递给 task_func 的参数
            
        Returns:
            创建的 Agent 实例
        """
        import functools
        
        agent_config = AgentConfig(
            name=name,
            agent_type=agent_type,
            metadata={"task_kwargs": kwargs}
        )
        
        async def wrapped_task():
            return await task_func(**kwargs)
        
        callback = functools.partial(
            self._spawn_with_task,
            task_func=wrapped_task
        )
        
        self.set_spawn_callback(callback)
        return await self.create_agent(name, agent_type, agent_config)
    
    async def _spawn_with_task(self, agent: Agent, task_func: Callable):
        """使用任务函数 spawn agent"""
        try:
            agent.state = AgentState.RUNNING
            agent.last_heartbeat = asyncio.get_event_loop().time()
            await task_func()
        except Exception as e:
            agent.state = AgentState.ERROR
            agent.metadata["error"] = str(e)


# 兼容旧API的便捷函数
async def create_agent(
    name: str,
    agent_type: str,
    registry: 'AgentRegistry' = None,
    **kwargs
) -> Agent:
    """创建新 agent 的便捷函数"""
    if registry is None:
        from .registry import AgentRegistry
        registry = AgentRegistry()
    
    creator = AgentCreator(registry)
    return await creator.create_agent(name, agent_type, **kwargs)


# 延迟导入避免循环引用
from .registry import AgentRegistry

__all__ = [
    'Agent', 'AgentConfig', 'AgentState',
    'AgentCreator', 'create_agent'
]
