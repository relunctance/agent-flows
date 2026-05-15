# ADR-001: Expert Teams 与 Agent Flows 的集成架构

## 状态
Accepted

## 日期
2025-05-15

## 背景

Expert Teams 需要支持流程（Flow）管理，但存在两种集成方案：

1. **方案A**: flows.py 作为独立 skill，解耦但多一个 skill
2. **方案B**: flows.py 放在 agent-flows 作为 SDK，紧耦合
3. **方案C**: flows.py 内嵌在 expert-teams，简单但紧耦合
4. **方案D（最终选择）**: Command Interface 模式，expert-teams 通过 CLI 调用 agent-flows

## 决策

采用 **Command Interface 模式**：

```
expert-teams (消费方)
    │
    └── 只需调用 agent-flows CLI 命令
            │
            ▼
    agent-flows (提供方)
    ├── flows/              # 流程定义
    ├── cli/                # 命令行接口
    │   ├── list           # 列出所有 flow
    │   ├── load <flow> <team_id>  # 绑定 team 到 flow
    │   └── status <team_id>      # 获取团队当前阶段
    └── sdk/               # 内部使用，不对外暴露
```

## 理由

| 维度 | Command Interface | SDK 嵌入 |
|------|------------------|----------|
| 解耦程度 | 最彻底 | 一般 |
| 依赖管理 | 无需 pip install | 需要安装 SDK |
| 可测试性 | CLI 可独立测试 | 依赖 SDK 测试 |
| 演进独立性 | agent-flows 可独立演进 | 两者版本需同步 |
| 多团队支持 | 可 fork 不同 agent-flows | 统一版本 |

## CLI 命令规范

### list 命令

```bash
python -m agent_flows.cli list
```

**输出格式**:
```
software-dev
legal-consultation
stock-analysis
```

**错误处理**:
- agent-flows 未安装: `Error: agent-flows not found`
- flows 目录不存在: `Error: No flows directory found`

### load 命令

```bash
python -m agent_flows.cli load <flow-name> <team-id>
```

**输出格式**:
```
✅ Flow 'software-dev' 已绑定到团队 'myteam'
```

**错误处理**:
- flow 不存在: `Error: Flow 'xxx' not found`
- 团队已绑定: `Error: Team 'xxx' already has flow 'yyy'`

### status 命令

```bash
python -m agent_flows.cli status <team-id>
```

**输出格式** (JSON):
```json
{
  "team_id": "myteam",
  "flow": "software-dev",
  "current_phase": "plan",
  "completed_phases": [],
  "phase_info": {
    "name": "plan",
    "display_name": "规划阶段",
    "owner": "architect",
    "reviewer": "delivery-director",
    "required_skills": ["brainstorming", "writing-plans"]
  },
  "next_phase": "implement"
}
```

**错误处理**:
- 团队未绑定 flow: `Error: Team 'xxx' has no flow bound`

## Expert Teams 集成

### flow list 命令

Expert Teams 的 `manual_mode.py` 中:

```python
elif action == "flow":
    if args and args[0] == "list":
        # 调用 agent-flows CLI
        result = subprocess.run(
            ["python", "-m", "agent_flows.cli", "list"],
            capture_output=True, text=True
        )
        print(result.stdout)
```

### flow load 命令

```python
elif action == "flow":
    if args and args[0] == "load":
        flow_name, team_id = args[1], args[2]
        result = subprocess.run(
            ["python", "-m", "agent_flows.cli", "load", flow_name, team_id],
            capture_output=True, text=True
        )
        print(result.stdout)
```

### phase 命令

```python
elif action == "phase":
    team_id = get_current_team_id()
    result = subprocess.run(
        ["python", "-m", "agent_flows.cli", "status", team_id],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    print(f"当前阶段: {data['phase_info']['display_name']}")
```

## 后果

### 正面

- Expert Teams 和 Agent Flows 完全解耦
- 可以独立演进
- 支持不同团队类型 fork 自己的 agent-flows
- CLI 可独立测试

### 负面

- 需要启动子进程（性能略低）
- 需要处理 CLI 输出格式

## 参考

- Expert Teams: https://github.com/relunctance/expert-teams
- Agent Flows: https://github.com/relunctance/agent-flows
