"""
Agent Flows CLI - 命令行接口
用法: python -m agent_flows.cli <command>
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog='agent-flows',
        description='Agent Flows - 多阶段工作流程管理'
    )
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

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

    if args.command is None:
        parser.print_help()
        return

    # 延迟导入，避免循环依赖
    if args.command == 'list':
        from .list import list_flows
        list_flows()
    elif args.command == 'load':
        from .load import load_flow
        load_flow(args.flow_name, args.team_id)
    elif args.command == 'status':
        from .status import get_status
        get_status(args.team_id)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
