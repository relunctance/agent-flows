"""
list 命令 - 列出所有可用的 flow
"""

from pathlib import Path

# Flows 目录：相对于项目根目录
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


if __name__ == '__main__':
    list_flows()
