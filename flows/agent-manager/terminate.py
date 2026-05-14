"""
Agent Termination Module

负责优雅地终止 agent 生命周期。
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .create import Agent, AgentState


class TerminationReason(Enum):
    """终止原因"""
    USER_REQUEST = "user_request"
    TASK_COMPLETE = "task_complete"
    TIMEOUT = "timeout"
    ERROR = "error"
    IDLE_TIMEOUT = "idle_timeout"
    RESOURCE_LIMIT = "resource_limit"


@dataclass
class TerminationResult:
    """终止结果"""
    agent_id: str
    success: bool
    reason: TerminationReason
    message: str
    cleanup_stats: Dict[str, Any]


class GracefulTerminator:
    """优雅终止器"""
    
    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry
        self._termination_handlers: Dict[str, List[callable]] = {}
    
    def register_handler(self, agent_id: str, handler: callable):
        """注册终止前的处理函数"""
        if agent_id not in self._termination_handlers:
            self._termination_handlers[agent_id] = []
        self._termination_handlers[agent_id].append(handler)
    
    async def terminate(
        self,
        agent: Agent,
        reason: TerminationReason = TerminationReason.USER_REQUEST,
        timeout: int = 30,
        force: bool = False
    ) -> TerminationResult:
        """
        终止 agent
        
        Args:
            agent: 要终止的 agent
            reason: 终止原因
            timeout: 优雅终止超时时间（秒）
            force: 是否强制终止
            
        Returns:
            TerminationResult 终止结果
        """
        agent_id = agent.id
        
        try:
            # 1. 调用终止前处理函数
            if agent_id in self._termination_handlers:
                for handler in self._termination_handlers[agent_id]:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(agent)
                    else:
                        handler(agent)
            
            # 2. 通知 agent 准备关闭
            agent.metadata["termination_reason"] = reason.value
            agent.state = AgentState.TERMINATED
            
            # 3. 执行清理
            cleanup_stats = await self._cleanup(agent, timeout, force)
            
            # 4. 从注册表移除
            await self.registry.unregister(agent_id)
            
            return TerminationResult(
                agent_id=agent_id,
                success=True,
                reason=reason,
                message=f"Agent {agent_id} terminated successfully",
                cleanup_stats=cleanup_stats
            )
            
        except Exception as e:
            return TerminationResult(
                agent_id=agent_id,
                success=False,
                reason=reason,
                message=f"Termination failed: {str(e)}",
                cleanup_stats={}
            )
    
    async def _cleanup(
        self,
        agent: Agent,
        timeout: int,
        force: bool
    ) -> Dict[str, Any]:
        """执行清理操作"""
        stats = {
            "handlers_executed": 0,
            "tasks_cancelled": 0,
            "resources_released": []
        }
        
        # 如果 agent 有运行中的任务，取消它们
        if hasattr(agent, 'tasks') and agent.tasks:
            for task in agent.tasks:
                if not task.done():
                    task.cancel()
                    stats["tasks_cancelled"] += 1
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(task),
                            timeout=timeout if not force else 0.1
                        )
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
        
        # 释放资源
        if hasattr(agent, 'resources'):
            for resource in agent.resources:
                try:
                    if hasattr(resource, 'close'):
                        resource.close()
                    stats["resources_released"].append(str(resource))
                except Exception:
                    pass
        
        stats["handlers_executed"] = len(
            self._termination_handlers.get(agent.id, [])
        )
        
        return stats
    
    async def terminate_all(
        self,
        reason: TerminationReason = TerminationReason.USER_REQUEST,
        timeout: int = 30,
        force: bool = False
    ) -> List[TerminationResult]:
        """终止所有 agent"""
        agents = list(self.registry.agents.values())
        results = []
        
        for agent in agents:
            result = await self.terminate(agent, reason, timeout, force)
            results.append(result)
        
        return results


async def terminate_agent(
    agent: Agent,
    registry: 'AgentRegistry' = None,
    reason: TerminationReason = TerminationReason.USER_REQUEST,
    **kwargs
) -> TerminationResult:
    """终止 agent 的便捷函数"""
    if registry is None:
        from .registry import AgentRegistry
        registry = AgentRegistry()
    
    terminator = GracefulTerminator(registry)
    return await terminator.terminate(agent, reason, **kwargs)


async def terminate_all_agents(
    registry: 'AgentRegistry' = None,
    **kwargs
) -> List[TerminationResult]:
    """终止所有 agent 的便捷函数"""
    if registry is None:
        from .registry import AgentRegistry
        registry = AgentRegistry()
    
    terminator = GracefulTerminator(registry)
    return await terminator.terminate_all(**kwargs)


__all__ = [
    'TerminationReason', 'TerminationResult',
    'GracefulTerminator', 'terminate_agent', 'terminate_all_agents'
]
