# Agent Flows
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![version](https://img.shields.io/badge/version--green.svg)]()
[![category](https://img.shields.io/badge/category--blue.svg)]()
[![platforms](https://img.shields.io/badge/platforms-hermes-blue.svg)]()

多阶段工作流程定义库。

## 目录结构

```
agent-flows/
├── flows/                    # 流程定义文件
│   └── *.toml               # TOML 格式的流程定义
├── schemas/                  # JSON Schema 验证文件
│   └── flow.schema.json     # 流程定义 schema
├── validators/               # 校验工具
│   └── validate_flow.py     # 流程校验脚本
└── templates/               # 模板文件
    └── flow-template.toml   # 新建流程的模板
```

## 快速开始

### 1. 查看已有流程

```bash
ls flows/
```

### 2. 创建新流程

参考 `flows/software-dev.toml` 或使用模板：

```bash
cp templates/flow-template.toml flows/my-flow.toml
```

### 3. 校验流程

```bash
python validators/validate_flow.py flows/my-flow.toml
```

## 已有流程

| 流程 | 说明 |
|------|------|
| software-dev | 软件研发流程 |

## 贡献指南

### 创建新流程

1. 在 `flows/` 目录下创建新的 `.toml` 文件
2. 参考 `templates/flow-template.toml` 格式
3. 运行校验确保格式正确：

```bash
python validators/validate_flow.py flows/my-flow.toml
```

4. 提交 Pull Request

### 流程定义规范

详见 [SCHEMA.md](./SCHEMA.md)

## License

MIT
