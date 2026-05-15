"""
load 命令 - 绑定 flow 到团队
"""

import json
from datetime import datetime
from pathlib import Path

# Flows 目录
FLOWS_DIR = Path(__file__).parent.parent.parent / 'flows'

# Teams 状态目录
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
        'bound_at': datetime.now().isoformat(),
        'completed_phases': []
    }

    with open(team_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Flow '{flow_name}' 已绑定到团队 '{team_id}'")


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: load <flow-name> <team-id>")
    else:
        load_flow(sys.argv[1], sys.argv[2])
