"""
Context Module

负责会话上下文的维护、管理和存储。
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class ContextScope(Enum):
    """上下文范围"""
    SESSION = "session"      # 会话级别
    AGENT = "agent"          # Agent 级别
    USER = "user"            # 用户级别
    GLOBAL = "global"        # 全局级别


class ContextEventType(Enum):
    """上下文事件类型"""
    SET = "set"
    UPDATE = "update"
    DELETE = "delete"
    CLEAR = "clear"


@dataclass
class ContextEntry:
    """上下文条目"""
    key: str
    value: Any
    scope: ContextScope
    created_at: float
    updated_at: float
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": self.metadata
        }


@dataclass
class ContextEvent:
    """上下文事件"""
    session_id: str
    event_type: ContextEventType
    key: str
    old_value: Any = None
    new_value: Any = None
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class ContextHistory:
    """上下文历史记录"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._history: List[ContextEvent] = []
    
    def add(self, event: ContextEvent):
        """添加历史记录"""
        self._history.append(event)
        if len(self._history) > self.max_size:
            self._history.pop(0)
    
    def get_recent(self, limit: int = 10) -> List[ContextEvent]:
        """获取最近的历史记录"""
        return self._history[-limit:]
    
    def clear(self):
        """清空历史"""
        self._history.clear()
    
    @property
    def entries(self) -> List[ContextEvent]:
        return self._history


class ContextManager:
    """
    上下文管理器
    
    负责会话上下文的存储、查询和生命周期管理。
    """
    
    def __init__(self, session_manager: 'SessionManager' = None):
        self._contexts: Dict[str, Dict[str, ContextEntry]] = defaultdict(dict)
        self._history: Dict[str, ContextHistory] = defaultdict(ContextHistory)
        self._lock = asyncio.Lock()
        self._session_manager = session_manager
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._hooks: Dict[str, List[Callable]] = defaultdict(list)
    
    def _get_context_key(
        self,
        session_id: str,
        scope: ContextScope,
        agent_id: Optional[str] = None
    ) -> str:
        """生成上下文存储键"""
        if scope == ContextScope.SESSION:
            return f"session:{session_id}"
        elif scope == ContextScope.AGENT:
            return f"agent:{agent_id}:{session_id}"
        elif scope == ContextScope.USER:
            return f"user:{agent_id}"
        else:
            return "global"
    
    async def set(
        self,
        session_id: str,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        设置上下文值
        
        Args:
            session_id: 会话 ID
            key: 键
            value: 值
            scope: 作用域
            agent_id: agent ID（用于 AGENT 和 USER 作用域）
            metadata: 额外元数据
            
        Returns:
            bool 设置是否成功
        """
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            now = time.time()
            
            # 检查是否已存在
            existing = self._contexts[ctx_key].get(key)
            
            if existing:
                event_type = ContextEventType.UPDATE
                old_value = existing.value
            else:
                event_type = ContextEventType.SET
                old_value = None
            
            entry = ContextEntry(
                key=key,
                value=value,
                scope=scope,
                created_at=now,
                updated_at=now,
                version=(existing.version + 1) if existing else 1,
                metadata=metadata or {}
            )
            
            self._contexts[ctx_key][key] = entry
            
            # 记录历史
            event = ContextEvent(
                session_id=session_id,
                event_type=event_type,
                key=key,
                old_value=old_value,
                new_value=value,
                source=agent_id or "system"
            )
            self._history[ctx_key].add(event)
            
            # 触发监听器
            await self._notify_listeners(session_id, event)
            
            return True
    
    async def get(
        self,
        session_id: str,
        key: str,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """获取上下文值"""
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            entry = self._contexts[ctx_key].get(key)
            return entry.value if entry else default
    
    async def get_all(
        self,
        session_id: str,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取所有上下文值"""
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            return {
                k: v.value for k, v in self._contexts[ctx_key].items()
            }
    
    async def delete(
        self,
        session_id: str,
        key: str,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None
    ) -> bool:
        """删除上下文值"""
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            
            if key in self._contexts[ctx_key]:
                entry = self._contexts[ctx_key][key]
                del self._contexts[ctx_key][key]
                
                event = ContextEvent(
                    session_id=session_id,
                    event_type=ContextEventType.DELETE,
                    key=key,
                    old_value=entry.value,
                    source=agent_id or "system"
                )
                self._history[ctx_key].add(event)
                
                await self._notify_listeners(session_id, event)
                return True
            
            return False
    
    async def clear(
        self,
        session_id: str,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None
    ) -> bool:
        """清空上下文"""
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            
            if ctx_key in self._contexts and self._contexts[ctx_key]:
                keys = list(self._contexts[ctx_key].keys())
                for key in keys:
                    del self._contexts[ctx_key][key]
                
                event = ContextEvent(
                    session_id=session_id,
                    event_type=ContextEventType.CLEAR,
                    key="*",
                    source=agent_id or "system"
                )
                self._history[ctx_key].add(event)
                
                await self._notify_listeners(session_id, event)
                return True
            
            return False
    
    async def update(
        self,
        session_id: str,
        data: Dict[str, Any],
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None
    ) -> bool:
        """批量更新上下文"""
        for key, value in data.items():
            await self.set(session_id, key, value, scope, agent_id)
        return True
    
    async def get_history(
        self,
        session_id: str,
        key: Optional[str] = None,
        limit: int = 10,
        scope: ContextScope = ContextScope.SESSION,
        agent_id: Optional[str] = None
    ) -> List[ContextEvent]:
        """获取上下文历史"""
        async with self._lock:
            ctx_key = self._get_context_key(session_id, scope, agent_id)
            history = self._history[ctx_key]
            
            events = history.get_recent(limit) if limit > 0 else history.entries
            
            if key:
                events = [e for e in events if e.key == key]
            
            return events
    
    def add_listener(
        self,
        session_id: str,
        listener: Callable
    ):
        """添加上下文监听器"""
        self._listeners[session_id].append(listener)
    
    def remove_listener(
        self,
        session_id: str,
        listener: Callable
    ):
        """移除上下文监听器"""
        if session_id in self._listeners:
            self._listeners[session_id].remove(listener)
    
    async def _notify_listeners(
        self,
        session_id: str,
        event: ContextEvent
    ):
        """通知所有监听器"""
        for listener in self._listeners.get(session_id, []):
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception:
                pass
    
    def add_hook(
        self,
        event_type: ContextEventType,
        hook: Callable
    ):
        """添加上下文钩子"""
        self._hooks[event_type.value].append(hook)
    
    async def export_context(
        self,
        session_id: str,
        format: str = "dict"
    ) -> Any:
        """导出上下文"""
        async with self._lock:
            session_contexts = {}
            
            for scope in ContextScope:
                ctx_key = self._get_context_key(session_id, scope, None)
                if ctx_key in self._contexts:
                    session_contexts[scope.value] = {
                        k: v.to_dict() for k, v in self._contexts[ctx_key].items()
                    }
            
            if format == "json":
                return json.dumps(session_contexts, default=str, indent=2)
            return session_contexts
    
    async def import_context(
        self,
        session_id: str,
        data: Dict[str, Any],
        merge: bool = True
    ):
        """导入上下文"""
        async with self._lock:
            for scope_str, entries in data.items():
                try:
                    scope = ContextScope(scope_str)
                except ValueError:
                    continue
                
                ctx_key = self._get_context_key(session_id, scope, None)
                
                if not merge:
                    self._contexts[ctx_key].clear()
                
                for key, entry_data in entries.items():
                    entry = ContextEntry(
                        key=entry_data["key"],
                        value=entry_data["value"],
                        scope=ContextScope(entry_data["scope"]),
                        created_at=entry_data["created_at"],
                        updated_at=entry_data["updated_at"],
                        version=entry_data["version"],
                        metadata=entry_data.get("metadata", {})
                    )
                    self._contexts[ctx_key][key] = entry


# 全局实例
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """获取全局上下文管理器"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


async def set_context(
    session_id: str,
    key: str,
    value: Any,
    **kwargs
) -> bool:
    """设置上下文值的便捷函数"""
    manager = get_context_manager()
    return await manager.set(session_id, key, value, **kwargs)


async def get_context(
    session_id: str,
    key: str,
    **kwargs
) -> Any:
    """获取上下文值的便捷函数"""
    manager = get_context_manager()
    return await manager.get(session_id, key, **kwargs)


__all__ = [
    'ContextScope', 'ContextEventType', 'ContextEntry',
    'ContextEvent', 'ContextHistory', 'ContextManager',
    'get_context_manager', 'set_context', 'get_context'
]
