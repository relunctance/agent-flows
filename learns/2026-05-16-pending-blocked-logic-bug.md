# pending/blocked 逻辑 Bug

日期: 2026-05-16

## 问题

初始实现时 pending/blocked 的定义搞反了：

```python
# 错误的逻辑
"pending": ["implement", "test", "release"],  # 这些阶段还没开始
"blocked": []  # 没有被阻塞的阶段
```

## 原因

对 "pending" 和 "blocked" 的语义理解错误：

- **pending** = 可执行但尚未完成的阶段
- **blocked** = 被阻塞的阶段（有未完成的 blocked_by）

## 正确逻辑

```python
"status": {
    "pending": ["plan"],           # plan 可执行（blocked_by=[]）
    "blocked": ["implement", "test", "release"]  # 被阻塞（有 blocked_by 未完成）
}
```

## 验证

```bash
python -m agent_flows.cli status test-team
```

输出：
```json
{
  "current_phase": "plan",
  "status": {
    "pending": ["plan"],
    "blocked": ["implement", "test", "release"]
  }
}
```

## 教训

实现有状态逻辑前，先明确写出状态定义，不要想当然。
