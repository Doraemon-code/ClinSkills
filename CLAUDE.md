# Project: 脊痛宁数据审核报告

## Overview
临床试验数据审核报告项目。通过 Python + pandas 处理 EDC 导出的 Excel 数据，生成 .docx/.xlsx 报表。

## Directory Structure
```
├── config.py           # 项目路径配置（从 config.yaml 加载路径变量）
├── config.yaml         # 数据路径配置
├── requirements.txt    # Python 依赖
├── 注意事项.md          # 业务规则说明
├── scripts/            # 分析代码（按章节拆分）
│   ├── a.试验整体情况小结/
│   ├── b.入排标准/
│   ├── c.方案偏离/
│   ├── d.超窗/
│   ├── e.缺失/
│   ├── f.用药后异常有临床意义/
│   ├── g.不良事件相关汇总/
│   ├── h.常规附件清单/
│   ├── i.方案禁止的合并用药清单/
│   └── j.依从性计算/
├── utils/              # 公共工具函数
│   ├── loaders.py      # 数据读取层（load_sheet / load_rand 等）
│   └── output_format.py # 报表输出函数（三线表、xlsx 等）
├── raw/                # 原始数据（不入 Git）
└── output/             # 生成的报表（不入 Git）
```

## Permissions
- `scripts/`、`utils/`、`config.py`、`config.yaml`：Claude Code 可编辑
- `raw/`、`output/`：不在 Git 中

## Conventions

编码规范（变量前缀、列名集中管理、八步操作模型、脚本模板等）详见 `/write-script` skill 的 `SKILL.md`。以下为跨 skill 的通用约定：

- 表头结构：`header=0, skiprows=[1]`（第 1 行中文列名，第 2 行英文列名被跳过）
- 报表函数来自 `utils/output_format.py`
- 数据读取函数来自 `utils/loaders.py`（`load_sheet` / `load_rand` 等）
- 生成文件路径由 `config.yaml` 的 `output_path` 控制（`config.py` 自动解析为绝对路径）
- 虚拟环境位于 `.venv/`，安装依赖：`pip install -r requirements.txt`

