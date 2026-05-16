"""
advance 命令 - 进入下一阶段
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


def advance_phase(team_id: str):
    """进入团队的下一阶段"""
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
    phases = flow_data.get('phases', [])

    # 找到当前阶段
    current_phase = None
    next_phase = None
    next_phase_name = None

    for i, phase in enumerate(phases):
        phase_name = phase.get('name')
        blocked_by = phase.get('blocked_by', [])

        if phase_name in completed:
            continue

        if all(b in completed for b in blocked_by):
            current_phase = phase
            if i + 1 < len(phases):
                next_phase = phases[i + 1]
                next_phase_name = next_phase.get('name')
            break

    if current_phase is None:
        print(f"Error: No active phase found for team '{team_id}'")
        sys.exit(1)

    current_phase_name = current_phase.get('name')

    # 将当前阶段标记为完成
    completed.append(current_phase_name)

    # 更新团队状态
    team_data['completed_phases'] = completed
    team_data['current_phase'] = next_phase_name

    with open(team_file, 'w') as f:
        json.dump(team_data, f, indent=2, ensure_ascii=False)

    if next_phase_name:
        print(f"✅ 阶段 '{current_phase_name}' 已完成")
        print(f"📍 当前阶段: {next_phase_name}")
        print(f"   下一步: {next_phase.get('display_name', next_phase_name)}")
    else:
        print(f"✅ 阶段 '{current_phase_name}' 已完成")
        print(f"🎉 所有阶段已完成！")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: advance <team-id>")
    else:
        advance_phase(sys.argv[1])
