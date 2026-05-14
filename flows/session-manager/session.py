"""
Session Module

负责会话的创建、管理和状态维护。
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class SessionState(Enum):
    """会话状态"""
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class SessionType(Enum):
    """会话类型"""
    SINGLE = "single"           # 单 agent 会话
    COLLABORATIVE = "collaborative"  # 协作会话
    BROADCAST = "broadcast"    # 广播会话


@dataclass
class SessionConfig:
    """会话配置"""
    session_type: SessionType = SessionType.SINGLE
    max_agents: int = 10
    idle_timeout: int = 3600  # 秒
    max_history: int = 1000
    auto_save: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionParticipant:
    """会话参与者"""
    agent_id: str
    role: str = "member"
    joined_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """
    会话对象
    
    维护会话状态、参与者列表和会话上下文。
    """
    id: str
    name: str
    state: SessionState = SessionState.CREATING
    config: SessionConfig = field(default_factory=SessionConfig)
    participants: Dict[str, SessionParticipant] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class SessionManager:
    """
    会话管理器
    
    负责会话的创建、查询、更新和销毁。
    """
    
    _instance: Optional['SessionManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._session_by_agent: Dict[str, Set[str]] = defaultdict(set)
        self._state_listeners: Dict[str, List[callable]] = defaultdict(list)
        self._initialized = True
    
    async def create_session(
        self,
        name: str,
        session_type: SessionType = SessionType.SINGLE,
        config: Optional[SessionConfig] = None,
        creator_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        创建新会话
        
        Args:
            name: 会话名称
            session_type: 会话类型
            config: 会话配置
            creator_id: 创建者 agent ID
            metadata: 额外元数据
            
        Returns:
            Session 新创建的会话
        """
        async with self._lock:
            session_id = str(uuid.uuid4())
            
            if config is None:
                config = SessionConfig(session_type=session_type)
            
            session = Session(
                id=session_id,
                name=name,
                state=SessionState.ACTIVE,
                config=config,
                metadata=metadata or {}
            )
            
            self._sessions[session_id] = session
            
            # 如果有创建者，自动添加为参与者
            if creator_id:
                await self.add_participant(session_id, creator_id, role="creator")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        async with self._lock:
            return self._sessions.get(session_id)
    
    async def get_session_by_agent(
        self,
        agent_id: str
    ) -> List[Session]:
        """获取 agent 参与的所有会话"""
        async with self._lock:
            session_ids = self._session_by_agent.get(agent_id, set())
            return [
                self._sessions[sid]
                for sid in session_ids
                if sid in self._sessions
            ]
    
    async def list_sessions(
        self,
        state: Optional[SessionState] = None,
        session_type: Optional[SessionType] = None
    ) -> List[Session]:
        """列出所有会话"""
        async with self._lock:
            sessions = list(self._sessions.values())
            
            if state:
                sessions = [s for s in sessions if s.state == state]
            
            if session_type:
                sessions = [
                    s for s in sessions
                    if s.config.session_type == session_type
                ]
            
            return sessions
    
    async def update_session(
        self,
        session_id: str,
        **updates
    ) -> bool:
        """
        更新会话
        
        Args:
            session_id: 会话 ID
            **updates: 要更新的字段
            
        Returns:
            bool 更新是否成功
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            session.updated_at = time.time()
            return True
    
    async def add_participant(
        self,
        session_id: str,
        agent_id: str,
        role: str = "member",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加会话参与者"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # 检查参与人数限制
            if len(session.participants) >= session.config.max_agents:
                return False
            
            participant = SessionParticipant(
                agent_id=agent_id,
                role=role,
                metadata=metadata or {}
            )
            
            session.participants[agent_id] = participant
            session._session_by_agent[agent_id].add(session_id)
            session.updated_at = time.time()
            
            return True
    
    async def remove_participant(
        self,
        session_id: str,
        agent_id: str
    ) -> bool:
        """移除会话参与者"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            if agent_id in session.participants:
                del session.participants[agent_id]
                session._session_by_agent[agent_id].discard(session_id)
                session.updated_at = time.time()
            
            return True
    
    async def close_session(
        self,
        session_id: str,
        reason: str = ""
    ) -> bool:
        """关闭会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.state = SessionState.CLOSING
            session.closed_at = time.time()
            session.metadata["close_reason"] = reason
            session.updated_at = time.time()
            
            # 通知所有参与者
            await self._notify_listeners(session_id, "close", session)
            
            session.state = SessionState.CLOSED
            
            return True
    
    async def suspend_session(self, session_id: str) -> bool:
        """暂停会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.state != SessionState.ACTIVE:
                return False
            
            session.state = SessionState.SUSPENDED
            session.updated_at = time.time()
            return True
    
    async def resume_session(self, session_id: str) -> bool:
        """恢复会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.state != SessionState.SUSPENDED:
                return False
            
            session.state = SessionState.ACTIVE
            session.updated_at = time.time()
            return True
    
    def add_state_listener(
        self,
        session_id: str,
        listener: callable
    ):
        """添加状态监听器"""
        self._state_listeners[session_id].append(listener)
    
    def remove_state_listener(
        self,
        session_id: str,
        listener: callable
    ):
        """移除状态监听器"""
        if session_id in self._state_listeners:
            self._state_listeners[session_id].remove(listener)
    
    async def _notify_listeners(
        self,
        session_id: str,
        event: str,
        session: Session
    ):
        """通知所有监听器"""
        for listener in self._state_listeners.get(session_id, []):
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event, session)
                else:
                    listener(event, session)
            except Exception:
                pass
    
    @property
    def sessions(self) -> Dict[str, Session]:
        """获取所有会话（同步访问）"""
        return self._sessions
    
    def clear(self):
        """清空所有会话（主要用于测试）"""
        self._sessions.clear()
        self._session_by_agent.clear()
        self._state_listeners.clear()


def get_session_manager() -> SessionManager:
    """获取全局会话管理器实例"""
    return SessionManager()


async def create_session(name: str, **kwargs) -> Session:
    """创建新会话的便捷函数"""
    manager = get_session_manager()
    return await manager.create_session(name, **kwargs)


async def get_session(session_id: str) -> Optional[Session]:
    """获取会话的便捷函数"""
    manager = get_session_manager()
    return await manager.get_session(session_id)


async def close_session(session_id: str, **kwargs) -> bool:
    """关闭会话的便捷函数"""
    manager = get_session_manager()
    return await manager.close_session(session_id, **kwargs)


__all__ = [
    'SessionState', 'SessionType', 'SessionConfig',
    'SessionParticipant', 'Session', 'SessionManager',
    'get_session_manager', 'create_session', 'get_session', 'close_session'
]
