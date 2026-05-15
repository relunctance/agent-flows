# Agent Flows CLI 实现计划

## 目标

实现 Agent Flows 命令行接口，支持 Expert Teams 通过 CLI 调用 Flow 管理功能。

## 交付物

| # | 交付物 | 位置 | 验收标准 |
|---|--------|------|----------|
| 1 | CLI 主入口 | `agent_flows/cli/__main__.py` | `python -m agent_flows.cli --help` 正常输出 |
| 2 | list 命令 | `agent_flows/cli/list.py` | `list` 输出所有 flow 名称 |
| 3 | load 命令 | `agent_flows/cli/load.py` | `load <flow> <team>` 绑定成功 |
| 4 | status 命令 | `agent_flows/cli/status.py` | `status <team>` 输出 JSON 格式阶段信息 |
| 5 | 团队状态存储 | `~/.agent-flows/teams/` | team_id.json 文件存储绑定状态 |

## 目录结构

```
agent-flows/
├── agent_flows/
│   ├── __init__.py
│   └── cli/
│       ├── __init__.py
│       ├── __main__.py      # CLI 主入口
│       ├── list.py          # list 命令
│       ├── load.py          # load 命令
│       └── status.py        # status 命令
├── flows/                   # Flow 定义 (*.toml)
└── sdk/                     # Python SDK (规划中)
```

## CLI 命令详细规格

### 1. list 命令

**命令**: `python -m agent_flows.cli list`

**功能**: 列出所有可用的 flow

**输出**: 每行一个 flow 名称

```
software-dev
legal-consultation
stock-analysis
```

**错误处理**:
| 错误情况 | 输出 |
|----------|------|
| flows 目录不存在 | `Error: No flows directory found at /path/to/flows` |
| flows 目录为空 | `Error: No flows found` |

### 2. load 命令

**命令**: `python -m agent_flows.cli load <flow-name> <team-id>`

**功能**: 将指定 flow 绑定到团队

**参数**:
- `flow-name`: flow 名称（不含 .toml 后缀）
- `team-id`: 团队标识符

**输出（成功）**:
```
✅ Flow 'software-dev' 已绑定到团队 'myteam'
```

**输出（错误）**:
| 错误情况 | 输出 |
|----------|------|
| flow 不存在 | `Error: Flow 'xxx' not found` |
| team 已绑定其他 flow | `Error: Team 'xxx' already has flow 'yyy' bound` |
| 缺少参数 | `Error: Missing argument. Usage: load <flow-name> <team-id>` |

**状态存储**: `~/.agent-flows/teams/<team-id>.json`

```json
{
  "team_id": "myteam",
  "flow": "software-dev",
  "bound_at": "2025-05-15T20:00:00",
  "completed_phases": []
}
```

### 3. status 命令

**命令**: `python -m agent_flows.cli status <team-id>`

**功能**: 获取团队的当前阶段信息

**输出格式**: JSON

```json
{
  "team_id": "myteam",
  "flow": "software-dev",
  "current_phase": "plan",
  "completed_phases": [],
  "phase_info": {
    "name": "plan",
    "display_name": "规划阶段",
    "description": "需求分析、任务分解、架构设计",
    "owner": "architect",
    "reviewer": "delivery-director",
    "required_skills": ["brainstorming", "writing-plans"],
    "recommended_skills": ["systematic-debugging"],
    "output_dir": "artifacts/plan",
    "blocked_by": []
  },
  "next_phase": "implement",
  "status": {
    "pending": ["implement", "test", "release"],
    "blocked": []
  }
}
```

**错误处理**:
| 错误情况 | 输出 |
|----------|------|
| 团队未绑定 flow | `Error: Team 'xxx' has no flow bound` |
| 团队状态文件丢失 | `Error: Team 'xxx' not found` |

## 实现步骤

### Step 1: 创建 CLI 目录结构

```bash
mkdir -p agent_flows/cli
touch agent_flows/__init__.py
touch agent_flows/cli/__init__.py
```

### Step 2: 实现 CLI 主入口

文件: `agent_flows/cli/__main__.py`

```python
import argparse
import sys
from .list import list_flows
from .load import load_flow
from .status import get_status

def main():
    parser = argparse.ArgumentParser(prog='agent-flows')
    subparsers = parser.add_subparsers(dest='command')

    # list 命令
    subparsers.add_parser('list', help='列出所有可用 flow')

    # load 命令
    load_parser = subparsers.add_parser('load', help='绑定 flow 到团队')
    load_parser.add_argument('flow_name', help='Flow 名称')
    load_parser.add_argument('team_id', help='团队 ID')

    # status 命令
    status_parser = subparsers.add_parser('status', help='获取团队当前阶段')
    status_parser.add_argument('team_id', help='团队 ID')

    args = parser.parse_args()

    if args.command == 'list':
        list_flows()
    elif args.command == 'load':
        load_flow(args.flow_name, args.team_id)
    elif args.command == 'status':
        get_status(args.team_id)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

### Step 3: 实现 list 命令

文件: `agent_flows/cli/list.py`

```python
import os
from pathlib import Path

FLOWS_DIR = Path(__file__).parent.parent.parent / 'flows'

def list_flows():
    """列出所有可用的 flow"""
    if not FLOWS_DIR.exists():
        print(f"Error: No flows directory found at {FLOWS_DIR}")
        return

    flows = [f.stem for f in FLOWS_DIR.glob('*.toml')]

    if not flows:
        print("Error: No flows found")
        return

    for flow in sorted(flows):
        print(flow)
```

### Step 4: 实现 load 命令

文件: `agent_flows/cli/load.py`

```python
import json
import os
from pathlib import Path

FLOWS_DIR = Path(__file__).parent.parent.parent / 'flows'
TEAMS_DIR = Path.home() / '.agent-flows' / 'teams'

def load_flow(flow_name: str, team_id: str):
    """绑定 flow 到团队"""
    # 检查 flow 是否存在
    flow_path = FLOWS_DIR / f'{flow_name}.toml'
    if not flow_path.exists():
        print(f"Error: Flow '{flow_name}' not found")
        return

    # 确保目录存在
    TEAMS_DIR.mkdir(parents=True, exist_ok=True)

    # 检查团队是否已绑定
    team_file = TEAMS_DIR / f'{team_id}.json'
    if team_file.exists():
        with open(team_file) as f:
            data = json.load(f)
        if data.get('flow'):
            print(f"Error: Team '{team_id}' already has flow '{data['flow']}' bound")
            return

    # 保存绑定状态
    data = {
        'team_id': team_id,
        'flow': flow_name,
        'bound_at': str(datetime.now()),
        'completed_phases': []
    }

    with open(team_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Flow '{flow_name}' 已绑定到团队 '{team_id}'")
```

### Step 5: 实现 status 命令

文件: `agent_flows/cli/status.py`

```python
import json
import sys
from pathlib import Path

FLOWS_DIR = Path(__file__).parent.parent.parent / 'flows'
TEAMS_DIR = Path.home() / '.agent-flows' / 'teams'

def get_status(team_id: str):
    """获取团队的当前阶段信息"""
    team_file = TEAMS_DIR / f'{team_id}.json'

    if not team_file.exists():
        print(f"Error: Team '{team_id}' not found")
        sys.exit(1)

    with open(team_file) as f:
        team_data = json.load(f)

    flow_name = team_data.get('flow')
    if not flow_name:
        print(f"Error: Team '{team_id}' has no flow bound")
        sys.exit(1)

    # 加载 flow 定义
    import toml
    flow_path = FLOWS_DIR / f'{flow_name}.toml'
    flow_data = toml.load(flow_path)

    completed = team_data.get('completed_phases', [])

    # 找到当前阶段
    phases = flow_data.get('phases', [])
    current_phase = None
    next_phase = None

    for i, phase in enumerate(phases):
        phase_name = phase.get('name')
        blocked_by = phase.get('blocked_by', [])

        if phase_name in completed:
            continue

        if all(b in completed for b in blocked_by):
            current_phase = phase
            if i + 1 < len(phases):
                next_phase = phases[i + 1].get('name')
            break

    # 构建输出
    output = {
        'team_id': team_id,
        'flow': flow_name,
        'current_phase': current_phase.get('name') if current_phase else None,
        'completed_phases': completed,
        'phase_info': current_phase,
        'next_phase': next_phase,
        'status': {
            'pending': [p.get('name') for p in phases if p.get('name') not in completed],
            'blocked': []
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
```

## 验证测试

### 测试 1: list 命令

```bash
$ python -m agent_flows.cli list
software-dev
```

### 测试 2: load 命令

```bash
$ python -m agent_flows.cli load software-dev myteam
✅ Flow 'software-dev' 已绑定到团队 'myteam'
```

### 测试 3: status 命令

```bash
$ python -m agent_flows.cli status myteam
{
  "team_id": "myteam",
  "flow": "software-dev",
  "current_phase": "plan",
  "completed_phases": [],
  ...
}
```

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.8 | 运行环境 |
| toml | >= 0.10 | 解析 .toml 文件 |

## 时间估算

| 步骤 | 预估时间 |
|------|----------|
| Step 1-3: CLI 框架 + list | 30 分钟 |
| Step 4: load 命令 | 30 分钟 |
| Step 5: status 命令 | 45 分钟 |
| 测试验证 | 30 分钟 |
| **总计** | **2 小时 15 分钟** |
