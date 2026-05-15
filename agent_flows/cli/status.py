"""
status 命令 - 获取团队的当前阶段信息
"""

import json
import sys
from pathlib import Path

try:
    import toml
except ImportError:
    print("Error: toml library required. Install with: pip install toml")
    sys.exit(1)

# Flows 目录
FLOWS_DIR = Path(__file__).parent.parent.parent / 'flows'

# Teams 状态目录
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
    flow_path = FLOWS_DIR / f'{flow_name}.toml'
    if not flow_path.exists():
        print(f"Error: Flow '{flow_name}' not found")
        sys.exit(1)

    flow_data = toml.load(flow_path)
    completed = team_data.get('completed_phases', [])

    # 找到当前阶段
    phases = flow_data.get('phases', [])
    current_phase = None
    next_phase_name = None

    for i, phase in enumerate(phases):
        phase_name = phase.get('name')
        blocked_by = phase.get('blocked_by', [])

        if phase_name in completed:
            continue

        if all(b in completed for b in blocked_by):
            current_phase = phase
            if i + 1 < len(phases):
                next_phase_name = phases[i + 1].get('name')
            break

    # 构建 phase_info
    phase_info = None
    if current_phase:
        roles = current_phase.get('roles', {})
        skills = current_phase.get('skills', {})
        phase_info = {
            'name': current_phase.get('name'),
            'display_name': current_phase.get('display_name'),
            'description': current_phase.get('description'),
            'owner': roles.get('owner'),
            'reviewer': roles.get('reviewer'),
            'executor': roles.get('executor'),
            'required_skills': skills.get('required', []),
            'recommended_skills': skills.get('recommended', []),
            'output_dir': current_phase.get('artifacts', {}).get('output_dir', ''),
            'blocked_by': current_phase.get('blocked_by', [])
        }

    # 构建 pending（可执行但未完成）和 blocked（被阻塞）列表
    pending = []
    blocked = []
    for phase in phases:
        phase_name = phase.get('name')
        if phase_name in completed:
            continue
        blocked_by = phase.get('blocked_by', [])
        if all(b in completed for b in blocked_by):
            pending.append(phase_name)
        else:
            blocked.append(phase_name)

    # 构建输出
    output = {
        'team_id': team_id,
        'flow': flow_name,
        'current_phase': current_phase.get('name') if current_phase else None,
        'completed_phases': completed,
        'phase_info': phase_info,
        'next_phase': next_phase_name,
        'status': {
            'pending': pending,
            'blocked': blocked
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: status <team-id>")
    else:
        get_status(sys.argv[1])
