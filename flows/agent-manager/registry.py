"""
Agent Registry Module

负责 agent 的注册、查找、状态管理和信息存储。
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .create import Agent, AgentState


@dataclass
class RegistryStats:
    """注册表统计信息"""
    total_agents: int = 0
    by_state: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    last_update: Optional[datetime] = None


class AgentRegistry:
    """
    Agent 注册中心
    
    提供线程安全的 agent 注册、查找和管理功能。
    """
    
    _instance: Optional['AgentRegistry'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._state_index: Dict[AgentState, Set[str]] = defaultdict(set)
        self._name_index: Dict[str, str] = {}  # name -> id
        self._watchers: Dict[str, List[Callable]] = defaultdict(list)
        self._initialized = True
    
    async def register(self, agent: Agent) -> bool:
        """
        注册新的 agent
        
        Args:
            agent: 要注册的 agent 实例
            
        Returns:
            bool 注册是否成功
        """
        async with self._lock:
            if agent.id in self._agents:
                return False
            
            self._agents[agent.id] = agent
            self._type_index[agent.agent_type].add(agent.id)
            self._state_index[agent.state].add(agent.id)
            self._name_index[agent.name] = agent.id
            
            # 触发 watchers
            await self._notify_watchers(agent.id, "register", agent)
            
            return True
    
    async def unregister(self, agent_id: str) -> bool:
        """
        取消注册 agent
        
        Args:
            agent_id: 要取消注册的 agent ID
            
        Returns:
            bool 取消注册是否成功
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False
            
            agent = self._agents[agent_id]
            
            # 从索引中移除
            self._type_index[agent.agent_type].discard(agent_id)
            self._state_index[agent.state].discard(agent_id)
            self._name_index.pop(agent.name, None)
            
            # 从 agents 中删除
            del self._agents[agent_id]
            
            # 触发 watchers
            await self._notify_watchers(agent_id, "unregister", agent)
            
            return True
    
    async def get(self, agent_id: str) -> Optional[Agent]:
        """根据 ID 获取 agent"""
        async with self._lock:
            return self._agents.get(agent_id)
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """根据名称获取 agent"""
        async with self._lock:
            agent_id = self._name_index.get(name)
            return self._agents.get(agent_id) if agent_id else None
    
    async def find_by_type(self, agent_type: str) -> List[Agent]:
        """根据类型查找 agent"""
        async with self._lock:
            agent_ids = self._type_index.get(agent_type, set())
            return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    async def find_by_state(self, state: AgentState) -> List[Agent]:
        """根据状态查找 agent"""
        async with self._lock:
            agent_ids = self._state_index.get(state, set())
            return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    async def find_all(self) -> List[Agent]:
        """获取所有 agent"""
        async with self._lock:
            return list(self._agents.values())
    
    async def update_state(self, agent_id: str, new_state: AgentState) -> bool:
        """
        更新 agent 状态
        
        Args:
            agent_id: agent ID
            new_state: 新的状态
            
        Returns:
            bool 更新是否成功
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False
            
            agent = self._agents[agent_id]
            old_state = agent.state
            
            # 更新状态索引
            self._state_index[old_state].discard(agent_id)
            self._state_index[new_state].add(agent_id)
            
            agent.state = new_state
            
            # 触发 watchers
            await self._notify_watchers(agent_id, "state_change", agent, old_state, new_state)
            
            return True
    
    async def update_heartbeat(self, agent_id: str) -> bool:
        """更新 agent 心跳时间戳"""
        import time
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].last_heartbeat = time.time()
            return True
    
    def watch(self, agent_id: str, callback: Callable):
        """添加 watcher 监听 agent 变化"""
        self._watchers[agent_id].append(callback)
    
    def unwatch(self, agent_id: str, callback: Callable):
        """移除 watcher"""
        if agent_id in self._watchers:
            self._watchers[agent_id].remove(callback)
    
    async def _notify_watchers(
        self,
        agent_id: str,
        event: str,
        *args,
        **kwargs
    ):
        """通知所有 watcher"""
        for callback in self._watchers.get(agent_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, *args, **kwargs)
                else:
                    callback(event, *args, **kwargs)
            except Exception:
                pass  # 不让 watcher 错误影响主流程
    
    async def get_stats(self) -> RegistryStats:
        """获取注册表统计信息"""
        async with self._lock:
            by_state = defaultdict(int)
            by_type = defaultdict(int)
            
            for agent in self._agents.values():
                by_state[agent.state.value] += 1
                by_type[agent.agent_type] += 1
            
            return RegistryStats(
                total_agents=len(self._agents),
                by_state=dict(by_state),
                by_type=dict(by_type),
                last_update=datetime.now()
            )
    
    @property
    def agents(self) -> Dict[str, Agent]:
        """获取所有 agents（同步访问）"""
        return self._agents
    
    def clear(self):
        """清空注册表（主要用于测试）"""
        self._agents.clear()
        self._type_index.clear()
        self._state_index.clear()
        self._name_index.clear()
        self._watchers.clear()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# 便捷函数
def get_registry() -> AgentRegistry:
    """获取全局注册表实例"""
    return AgentRegistry()


async def register_agent(agent: Agent) -> bool:
    """注册 agent 的便捷函数"""
    registry = get_registry()
    return await registry.register(agent)


async def unregister_agent(agent_id: str) -> bool:
    """取消注册 agent 的便捷函数"""
    registry = get_registry()
    return await registry.unregister(agent_id)


async def get_agent(agent_id: str) -> Optional[Agent]:
    """获取 agent 的便捷函数"""
    registry = get_registry()
    return await registry.get(agent_id)


__all__ = [
    'AgentRegistry', 'RegistryStats',
    'get_registry', 'register_agent', 'unregister_agent', 'get_agent'
]
