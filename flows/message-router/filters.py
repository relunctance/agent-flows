"""
Message Filters Module

负责消息过滤和处理，支持基于规则的过滤、条件过滤等。
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio


@dataclass
class FilterResult:
    """过滤结果"""
    passed: bool
    reason: str = ""
    modified_content: Any = None


class FilterType(Enum):
    """过滤器类型"""
    ALLOW = "allow"      # 白名单
    DENY = "deny"        # 黑名单
    TRANSFORM = "transform"  # 转换
    VALIDATE = "validate"    # 验证


class BaseFilter:
    """过滤器基类"""
    
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
    
    async def filter(self, message: 'Message') -> FilterResult:
        """执行过滤"""
        raise NotImplementedError
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r})"


class ContentFilter(BaseFilter):
    """内容过滤器 - 基于内容过滤消息"""
    
    def __init__(
        self,
        patterns: List[str] = None,
        filter_type: FilterType = FilterType.DENY,
        case_sensitive: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.patterns = patterns or []
        self.filter_type = filter_type
        self.case_sensitive = case_sensitive
        self._compiled_patterns = [
            re.compile(p, 0 if case_sensitive else re.IGNORECASE)
            for p in self.patterns
        ]
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于内容过滤"""
        content_str = str(message.content)
        
        matched = any(p.search(content_str) for p in self._compiled_patterns)
        
        if self.filter_type == FilterType.ALLOW:
            if not matched:
                return FilterResult(passed=True, reason="No patterns matched")
            return FilterResult(passed=False, reason="Content matched deny pattern")
        
        elif self.filter_type == FilterType.DENY:
            if matched:
                return FilterResult(passed=False, reason="Content matched block pattern")
            return FilterResult(passed=True)
        
        return FilterResult(passed=True)


class MetadataFilter(BaseFilter):
    """元数据过滤器 - 基于消息元数据过滤"""
    
    def __init__(
        self,
        required_keys: List[str] = None,
        optional_keys: List[str] = None,
        key_conditions: Dict[str, Any] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.required_keys = required_keys or []
        self.optional_keys = optional_keys or []
        self.key_conditions = key_conditions or {}
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于元数据过滤"""
        metadata = message.metadata
        
        # 检查必需键
        for key in self.required_keys:
            if key not in metadata:
                return FilterResult(
                    passed=False,
                    reason=f"Missing required key: {key}"
                )
        
        # 检查键条件
        for key, expected in self.key_conditions.items():
            if key not in metadata:
                return FilterResult(
                    passed=False,
                    reason=f"Key not found: {key}"
                )
            
            actual = metadata[key]
            if isinstance(expected, (list, tuple)):
                if actual not in expected:
                    return FilterResult(
                        passed=False,
                        reason=f"Key {key} value {actual} not in allowed values"
                    )
            elif actual != expected:
                return FilterResult(
                    passed=False,
                    reason=f"Key {key} value mismatch: {actual} != {expected}"
                )
        
        return FilterResult(passed=True)


class SourceFilter(BaseFilter):
    """源过滤器 - 基于消息来源过滤"""
    
    def __init__(
        self,
        allowed_sources: List[str] = None,
        denied_sources: List[str] = None,
        source_patterns: List[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.allowed_sources = set(allowed_sources or [])
        self.denied_sources = set(denied_sources or [])
        self.source_patterns = source_patterns or []
        self._compiled_patterns = [
            re.compile(p) for p in self.source_patterns
        ]
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于来源过滤"""
        source = message.source_id
        
        # 白名单检查
        if self.allowed_sources:
            if source not in self.allowed_sources:
                return FilterResult(
                    passed=False,
                    reason=f"Source {source} not in allowed list"
                )
            return FilterResult(passed=True)
        
        # 黑名单检查
        if source in self.denied_sources:
            return FilterResult(
                passed=False,
                reason=f"Source {source} is blocked"
            )
        
        # 模式匹配
        for pattern in self._compiled_patterns:
            if pattern.match(source):
                return FilterResult(
                    passed=False,
                    reason=f"Source {source} matched blocked pattern"
                )
        
        return FilterResult(passed=True)


class PriorityFilter(BaseFilter):
    """优先级过滤器 - 基于消息优先级过滤"""
    
    def __init__(
        self,
        min_priority: int = 0,
        max_priority: int = 3,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_priority = min_priority
        self.max_priority = max_priority
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于优先级过滤"""
        priority = message.priority.value
        
        if priority < self.min_priority:
            return FilterResult(
                passed=False,
                reason=f"Priority {priority} below minimum {self.min_priority}"
            )
        
        if priority > self.max_priority:
            return FilterResult(
                passed=False,
                reason=f"Priority {priority} above maximum {self.max_priority}"
            )
        
        return FilterResult(passed=True)


class TimeWindowFilter(BaseFilter):
    """时间窗口过滤器 - 在特定时间范围内过滤"""
    
    def __init__(
        self,
        allowed_hours: List[int] = None,  # 0-23
        denied_hours: List[int] = None,
        allowed_days: List[int] = None,   # 0-6 (Mon-Sun)
        **kwargs
    ):
        super().__init__(**kwargs)
        self.allowed_hours = set(allowed_hours) if allowed_hours else None
        self.denied_hours = set(denied_hours) if denied_hours else set()
        self.allowed_days = set(allowed_days) if allowed_days else None
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于时间窗口过滤"""
        import time
        
        now = time.localtime()
        hour = now.tm_hour
        day = now.tm_wday
        
        # 检查被禁止的小时
        if hour in self.denied_hours:
            return FilterResult(
                passed=False,
                reason=f"Hour {hour} is blocked"
            )
        
        # 检查允许的小时（如果设置了）
        if self.allowed_hours is not None:
            if hour not in self.allowed_hours:
                return FilterResult(
                    passed=False,
                    reason=f"Hour {hour} not in allowed window"
                )
        
        # 检查允许的天（如果设置了）
        if self.allowed_days is not None:
            if day not in self.allowed_days:
                return FilterResult(
                    passed=False,
                    reason=f"Day {day} not in allowed days"
                )
        
        return FilterResult(passed=True)


class ConditionalFilter(BaseFilter):
    """条件过滤器 - 基于自定义条件的过滤器"""
    
    def __init__(
        self,
        condition: Callable[[Any], bool],
        error_message: str = "Condition not met",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.condition = condition
        self.error_message = error_message
    
    async def filter(self, message: 'Message') -> FilterResult:
        """基于条件过滤"""
        try:
            if asyncio.iscoroutinefunction(self.condition):
                passed = await self.condition(message)
            else:
                passed = self.condition(message)
            
            if passed:
                return FilterResult(passed=True)
            return FilterResult(passed=False, reason=self.error_message)
        except Exception as e:
            return FilterResult(
                passed=False,
                reason=f"Condition error: {str(e)}"
            )


class FilterChain:
    """过滤器链 - 按顺序执行多个过滤器"""
    
    def __init__(self, filters: List[BaseFilter] = None):
        self.filters = filters or []
    
    def add(self, filter: BaseFilter):
        """添加过滤器"""
        self.filters.append(filter)
    
    def remove(self, filter: BaseFilter):
        """移除过滤器"""
        self.filters.remove(filter)
    
    async def execute(self, message: 'Message') -> FilterResult:
        """执行过滤链"""
        for filter_obj in self.filters:
            result = await filter_obj.filter(message)
            if not result.passed:
                return result
        return FilterResult(passed=True)
    
    async def __call__(self, message: 'Message') -> FilterResult:
        """支持直接调用"""
        return await self.execute(message)


class FilterManager:
    """过滤器管理器"""
    
    def __init__(self):
        self._filters: Dict[str, List[BaseFilter]] = defaultdict(list)  # noqa
        self._global_filters: List[BaseFilter] = []
    
    def register_filter(
        self,
        agent_id: str,
        filter_obj: BaseFilter
    ):
        """为特定 agent 注册过滤器"""
        self._filters[agent_id].append(filter_obj)
    
    def register_global(self, filter_obj: BaseFilter):
        """注册全局过滤器"""
        self._global_filters.append(filter_obj)
    
    def unregister_filter(
        self,
        agent_id: str,
        filter_obj: BaseFilter
    ):
        """注销过滤器"""
        if agent_id in self._filters:
            self._filters[agent_id].remove(filter_obj)
    
    async def filter_message(
        self,
        message: 'Message'
    ) -> FilterResult:
        """过滤消息"""
        # 先执行全局过滤器
        for filter_obj in self._global_filters:
            result = await filter_obj.filter(message)
            if not result.passed:
                return result
        
        # 执行目标特定的过滤器
        if isinstance(message.target_id, str):
            target_id = message.target_id
        elif isinstance(message.target_id, list) and message.target_id:
            target_id = message.target_id[0]
        else:
            return FilterResult(passed=True)
        
        for filter_obj in self._filters.get(target_id, []):
            result = await filter_obj.filter(message)
            if not result.passed:
                return result
        
        return FilterResult(passed=True)


# 延迟导入避免循环引用
from .router import Message

__all__ = [
    'FilterType', 'FilterResult', 'BaseFilter',
    'ContentFilter', 'MetadataFilter', 'SourceFilter',
    'PriorityFilter', 'TimeWindowFilter', 'ConditionalFilter',
    'FilterChain', 'FilterManager'
]
