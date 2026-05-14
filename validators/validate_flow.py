#!/usr/bin/env python3
"""
Flow 模板校验脚本

校验流程定义文件是否符合 schema 规范。
"""

import json
import sys
from pathlib import Path

import jsonschema
import tomllib


def load_schema(schema_path: Path) -> dict:
    """加载 JSON Schema"""
    with open(schema_path) as f:
        return json.load(f)


def load_flow(flow_path: Path) -> dict:
    """加载 TOML 格式的流程定义"""
    with open(flow_path, "rb") as f:
        return tomllib.load(f)


def validate_flow(flow_path: Path, schema_path: Path) -> tuple[bool, list[str]]:
    """
    校验流程文件

    Returns:
        (是否通过, 错误信息列表)
    """
    errors = []

    # 加载 schema
    try:
        schema = load_schema(schema_path)
    except Exception as e:
        return False, [f"无法加载 schema: {e}"]

    # 加载 flow
    try:
        flow = load_flow(flow_path)
    except Exception as e:
        return False, [f"无法加载流程文件: {e}"]

    # 校验
    try:
        jsonschema.validate(flow, schema)
    except jsonschema.ValidationError as e:
        # 提取有用的错误信息
        path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        message = e.message
        errors.append(f"[{path}] {message}")
    except jsonschema.SchemaError as e:
        return False, [f"Schema 错误: {e}"]

    # 额外校验：blocked_by 引用是否存在
    phase_names = {p["name"] for p in flow.get("phases", [])}
    for phase in flow.get("phases", []):
        if "blocked_by" in phase:
            for dep in phase["blocked_by"]:
                if dep not in phase_names:
                    errors.append(f"[phases.{phase['name']}.blocked_by] 引用了不存在的阶段: {dep}")

    # 额外校验：阶段 reviewer 是否在角色中存在
    role_names = set()
    for phase in flow.get("phases", []):
        if "roles" in phase:
            for role_type, role_name in phase["roles"].items():
                if role_name is not None:
                    role_names.add(role_name)

    for phase in flow.get("phases", []):
        if "review" in phase:
            reviewer = phase["review"].get("reviewer")
            escalate = phase["review"].get("escalate_to")
            if reviewer and reviewer not in role_names:
                errors.append(f"[phases.{phase['name']}.review.reviewer] 角色不存在: {reviewer}")
            if escalate and escalate not in role_names:
                errors.append(f"[phases.{phase['name']}.review.escalate_to] 角色不存在: {escalate}")

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("用法: python validate_flow.py <flow-file> [schema-file]")
        print("示例: python validate_flow.py flows/software-dev.toml")
        sys.exit(1)

    flow_path = Path(sys.argv[1])

    # 默认 schema 路径
    if len(sys.argv) >= 3:
        schema_path = Path(sys.argv[2])
    else:
        # 相对于脚本位置查找 schema
        script_dir = Path(__file__).parent.parent
        schema_path = script_dir / "schemas" / "flow.schema.json"

    if not flow_path.exists():
        print(f"❌ 流程文件不存在: {flow_path}")
        sys.exit(1)

    if not schema_path.exists():
        print(f"❌ Schema 文件不存在: {schema_path}")
        sys.exit(1)

    print(f"📋 校验流程: {flow_path}")
    print(f"📋 使用 Schema: {schema_path}")
    print()

    valid, errors = validate_flow(flow_path, schema_path)

    if valid:
        print("✅ 校验通过！")
        sys.exit(0)
    else:
        print("❌ 校验失败：")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
