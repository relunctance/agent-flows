"""
Health Check Module

负责 agent 的健康状态检查和故障检测。
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .create import Agent, AgentState


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    agent_id: str
    status: HealthStatus
    timestamp: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class HealthMetrics:
    """健康指标"""
    total_checks: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    degraded_count: int = 0
    last_check_time: float = 0.0
    avg_response_time_ms: float = 0.0


class HealthChecker:
    """健康检查器"""
    
    DEFAULT_TIMEOUT = 5.0
    DEFAULT_INTERVAL = 30.0
    MAX_CONSECUTIVE_FAILURES = 3
    
    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry
        self._custom_checks: Dict[str, Callable] = {}
        self._check_results: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        self._consecutive_failures: Dict[str, int] = defaultdict(int)
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def register_check(self, agent_type: str, check_func: Callable):
        """注册自定义健康检查函数"""
        self._custom_checks[agent_type] = check_func
    
    async def check_agent(
        self,
        agent: Agent,
        timeout: float = DEFAULT_TIMEOUT,
        include_details: bool = True
    ) -> HealthCheckResult:
        """
        检查单个 agent 的健康状态
        
        Args:
            agent: 要检查的 agent
            timeout: 检查超时时间
            include_details: 是否包含详细信息
            
        Returns:
            HealthCheckResult 健康检查结果
        """
        start_time = time.perf_counter()
        
        try:
            # 基础状态检查
            if agent.state == AgentState.TERMINATED:
                return HealthCheckResult(
                    agent_id=agent.id,
                    status=HealthStatus.UNHEALTHY,
                    timestamp=time.time(),
                    message="Agent is terminated",
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )
            
            # 心跳检查
            if agent.last_heartbeat:
                time_since_heartbeat = time.time() - agent.last_heartbeat
                if time_since_heartbeat > self.DEFAULT_INTERVAL * 2:
                    return HealthCheckResult(
                        agent_id=agent.id,
                        status=HealthStatus.UNHEALTHY,
                        timestamp=time.time(),
                        message=f"No heartbeat for {time_since_heartbeat:.1f}s",
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )
            
            # 自定义检查
            details = {}
            if agent.agent_type in self._custom_checks:
                check_func = self._custom_checks[agent.agent_type]
                result = await asyncio.wait_for(
                    check_func(agent),
                    timeout=timeout
                )
                details = result if isinstance(result, dict) else {"result": result}
            
            # 检查响应时间
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # 确定健康状态
            status = self._determine_status(agent, latency_ms, details)
            
            # 重置连续失败计数
            if status == HealthStatus.HEALTHY:
                self._consecutive_failures[agent.id] = 0
            else:
                self._consecutive_failures[agent.id] += 1
            
            return HealthCheckResult(
                agent_id=agent.id,
                status=status,
                timestamp=time.time(),
                message=self._get_status_message(status),
                details=details if include_details else {},
                latency_ms=latency_ms
            )
            
        except asyncio.TimeoutError:
            self._consecutive_failures[agent.id] += 1
            return HealthCheckResult(
                agent_id=agent.id,
                status=HealthStatus.UNHEALTHY,
                timestamp=time.time(),
                message="Health check timeout",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            self._consecutive_failures[agent.id] += 1
            return HealthCheckResult(
                agent_id=agent.id,
                status=HealthStatus.UNHEALTHY,
                timestamp=time.time(),
                message=f"Health check error: {str(e)}",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )
    
    def _determine_status(
        self,
        agent: Agent,
        latency_ms: float,
        details: Dict[str, Any]
    ) -> HealthStatus:
        """根据指标确定健康状态"""
        # 连续失败超过阈值
        if self._consecutive_failures[agent.id] >= self.MAX_CONSECUTIVE_FAILURES:
            return HealthStatus.UNHEALTHY
        
        # 响应时间过慢
        if latency_ms > 5000:  # 5秒
            return HealthStatus.DEGRADED
        
        # 基础状态判断
        if agent.state == AgentState.RUNNING:
            return HealthStatus.HEALTHY
        elif agent.state == AgentState.ERROR:
            return HealthStatus.UNHEALTHY
        elif agent.state == AgentState.IDLE:
            return HealthStatus.DEGRADED
        
        return HealthStatus.UNKNOWN
    
    def _get_status_message(self, status: HealthStatus) -> str:
        """获取状态消息"""
        messages = {
            HealthStatus.HEALTHY: "Agent is healthy",
            HealthStatus.DEGRADED: "Agent is degraded",
            HealthStatus.UNHEALTHY: "Agent is unhealthy",
            HealthStatus.UNKNOWN: "Agent status unknown"
        }
        return messages.get(status, "Unknown status")
    
    async def check_all(
        self,
        timeout: float = DEFAULT_TIMEOUT
    ) -> List[HealthCheckResult]:
        """检查所有注册 agent 的健康状态"""
        agents = list(self.registry.agents.values())
        tasks = [
            self.check_agent(agent, timeout, include_details=False)
            for agent in agents
        ]
        return await asyncio.gather(*tasks)
    
    def get_aggregated_metrics(self) -> HealthMetrics:
        """获取聚合健康指标"""
        all_results = []
        for results in self._check_results.values():
            all_results.extend(results[-100:])  # 只看最近100条
        
        if not all_results:
            return HealthMetrics()
        
        healthy = sum(1 for r in all_results if r.status == HealthStatus.HEALTHY)
        unhealthy = sum(1 for r in all_results if r.status == HealthStatus.UNHEALTHY)
        degraded = sum(1 for r in all_results if r.status == HealthStatus.DEGRADED)
        
        total_latency = sum(r.latency_ms for r in all_results)
        
        return HealthMetrics(
            total_checks=len(all_results),
            healthy_count=healthy,
            unhealthy_count=unhealthy,
            degraded_count=degraded,
            last_check_time=max(r.timestamp for r in all_results) if all_results else 0,
            avg_response_time_ms=total_latency / len(all_results) if all_results else 0
        )
    
    async def start_monitoring(
        self,
        interval: float = DEFAULT_INTERVAL,
        auto_remediate: bool = False
    ):
        """启动持续监控"""
        self._running = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval, auto_remediate)
        )
    
    async def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float, auto_remediate: bool):
        """监控循环"""
        while self._running:
            try:
                results = await self.check_all()
                
                # 记录结果
                for result in results:
                    self._check_results[result.agent_id].append(result)
                    # 保持最多100条记录
                    if len(self._check_results[result.agent_id]) > 100:
                        self._check_results[result.agent_id].pop(0)
                
                # 自动修复
                if auto_remediate:
                    await self._auto_remediate(results)
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception:
                pass
    
    async def _auto_remediate(self, results: List[HealthCheckResult]):
        """自动修复不健康的 agent"""
        from .terminate import terminate_agent, TerminationReason
        
        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                agent = self.registry.agents.get(result.agent_id)
                if agent:
                    await terminate_agent(
                        agent,
                        self.registry,
                        TerminationReason.ERROR
                    )


# 便捷函数
async def check_agent_health(
    agent: Agent,
    registry: 'AgentRegistry' = None,
    **kwargs
) -> HealthCheckResult:
    """检查 agent 健康状态的便捷函数"""
    if registry is None:
        from .registry import AgentRegistry
        registry = AgentRegistry()
    
    checker = HealthChecker(registry)
    return await checker.check_agent(agent, **kwargs)


async def check_all_health(
    registry: 'AgentRegistry' = None,
    **kwargs
) -> List[HealthCheckResult]:
    """检查所有 agent 健康状态的便捷函数"""
    if registry is None:
        from .registry import AgentRegistry
        registry = AgentRegistry()
    
    checker = HealthChecker(registry)
    return await checker.check_all(**kwargs)


__all__ = [
    'HealthStatus', 'HealthCheckResult', 'HealthMetrics',
    'HealthChecker', 'check_agent_health', 'check_all_health'
]
