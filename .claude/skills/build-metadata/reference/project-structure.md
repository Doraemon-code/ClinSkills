# 标准项目目录结构

本文件是临床试验数据审核报告项目的标准目录结构。
`build-metadata` skill 的 Step 0.5 以此为基准校验项目目录，如有偏离则自动修正。

## 目录树

```
<project_root>/
├── 01 rawdata/                  # 原始数据（不入 Git）
├── 02 metadata/                 # EDC 元数据 Excel + build-metadata 生成的 JSON
├── 03 output/                   # 生成的报表（不入 Git）
├── 04 scripts/                  # 分析代码（按章节拆分，子目录由报告章节决定）
├── .claude/                     # Claude Code 配置（不随项目变动）
│   ├── hooks/
│   │   ├── raw_read_guard.py    # PreToolUse: 禁止直接读 rawdata
│   │   └── syntax_check.py      # PostToolUse: 脚本语法检查
│   ├── rules/
│   │   └── constraints.md       # 强制约束
│   ├── settings.json            # 权限与钩子配置
│   └── skills/
│       ├── build-metadata/      # 元数据解析技能
│       └── write-script/        # 脚本编写技能
├── utils/                       # 公共工具函数
│   ├── __init__.py
│   ├── loaders.py               # 数据读取层（load_sheet / load_rand）
│   └── output_format.py         # 报表输出函数（三线表、xlsx）
├── .gitattributes               # Git 行尾与二进制规则
├── .gitignore                   # Git 忽略规则
├── CLAUDE.md                    # 项目说明与 Claude Code 约定
├── config.py                    # 路径配置加载器（从 config.yaml 读取）
├── config.yaml                  # 数据路径配置
└── requirements.txt             # Python 依赖
```

## 目录命名规则

数据目录使用 `序号 名称` 格式（序号为两位数字，后跟空格），确保文件管理器中排序一致：

| 序号 | 目录名 | 用途 | 入 Git |
|------|--------|------|--------|
| 01 | rawdata | EDC 导出的原始 Excel 数据 | 否 |
| 02 | metadata | 元数据 Excel + 解析后的 JSON | 是 |
| 03 | output | 生成的报表文件 | 否 |
| 04 | scripts | 数据核查 Python 脚本 | 是 |

## 骨架文件

以下文件是项目的基础配置，初始化时如不存在则生成默认模板：

### `.gitattributes`

```text
# Auto detect text files and normalize line endings to LF in repository
* text=auto eol=lf

# Explicitly declare text types
*.py text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.txt text eol=lf

# Binary files
*.xlsx binary
*.docx binary
*.png binary
*.jpg binary
```

### `.gitignore`

```text
# Python cache
__pycache__/
*.pyc

# Generated output
03 output/

# Raw data (large / sensitive)
01 rawdata/

# OS
.DS_Store
Thumbs.db

.venv/
```

### `CLAUDE.md`

```markdown
# Project: <项目名>数据审核报告

## Overview
临床试验数据审核报告项目。通过 Python + pandas 处理 EDC 导出的 Excel 数据，生成 .docx/.xlsx 报表。

## Directory Structure
\```
├── 04 scripts/            # 分析代码（按章节拆分）
├── utils/              # 公共工具函数
│   ├── loaders.py      # 数据读取层（load_sheet / load_rand 等）
│   └── output_format.py # 报表输出函数（三线表、xlsx 等）
├── 02 metadata/         # EDC 元数据 Excel + build-metadata 生成的 JSON
├── 01 rawdata/          # 原始数据（不入 Git）
└── 03 output/           # 生成的报表（不入 Git）
\```

## Permissions
- `04 scripts/`、`utils/`、`config.py`、`config.yaml`：Claude Code 可编辑
- `01 rawdata/`、`03 output/`：不在 Git 中

## Conventions

编码规范（变量前缀、列名集中管理、八步操作模型、脚本模板等）详见 `/write-script` skill 的 `SKILL.md`。以下为跨 skill 的通用约定：

- 表头结构：`header=0, skiprows=[1]`（第 1 行中文列名，第 2 行英文列名被跳过）
- 报表函数来自 `utils/output_format.py`
- 数据读取函数来自 `utils/loaders.py`（`load_sheet` / `load_rand` 等）
- 生成文件路径由 `config.yaml` 的 `output_path` 控制（`config.py` 自动解析为绝对路径）
- 虚拟环境位于 `.venv/`，安装依赖：`pip install -r requirements.txt`
```

### `config.py`

```python
"""
config.py — 项目路径配置

从 config.yaml 加载数据路径，供各脚本直接 import。
"""

from pathlib import Path
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent
_CONFIG = _PROJECT_ROOT / "config.yaml"

with open(_CONFIG, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

raw_path    = str(_PROJECT_ROOT / _cfg["path"]["raw_path"])
pd_path     = str(_PROJECT_ROOT / _cfg["path"]["pd_path"])
code_path   = str(_PROJECT_ROOT / _cfg["path"]["code_path"])
remark_path = str(_PROJECT_ROOT / _cfg["path"]["remark_path"])
timewin_path = str(_PROJECT_ROOT / _cfg["path"]["timewin_path"])
output_path = str(_PROJECT_ROOT / _cfg["path"]["output_path"])
```

### `config.yaml`

```yaml
path:
  # 各原始数据 Excel 路径（相对项目根），按新项目实际填写
  raw_path: "01 rawdata/<日期>/<受试者数据导出>.xlsx"
  pd_path: "01 rawdata/<日期>/<方案偏离>.xlsx"
  code_path: "01 rawdata/<日期>/<医学编码报告>.xlsx"
  remark_path: "01 rawdata/<日期>/<备注明细>.xlsx"
  timewin_path: "01 rawdata/time window.xlsx"
  output_path: "03 output/<日期>"
```

### `requirements.txt`

```text
pandas>=2.0
numpy>=1.24
python-docx>=1.0
openpyxl>=3.1
scipy>=1.11
PyYAML>=6.0
XlsxWriter>=3.1
```

## 目录重命名时的路径同步清单

当数据目录（01-04）发生重命名时，以下文件中的路径引用必须同步更新：

| 文件 | 引用内容 |
|------|---------|
| `config.yaml` | `raw_path` / `pd_path` / `code_path` / `remark_path` / `timewin_path` / `output_path` |
| `CLAUDE.md` | 目录树、Permissions 节 |
| `.claude/settings.json` | Edit / Write / Bash 权限模式 |
| `.claude/settings.local.json` | PowerShell 权限模式（如有） |
| `.claude/rules/constraints.md` | `scripts/` 引用 |
| `.claude/hooks/syntax_check.py` | `parts[0]` 检查 + docstring |
| `.claude/hooks/raw_read_guard.py` | `_under_dir()` 参数 + docstring |
| `.claude/skills/write-script/SKILL.md` | 验证命令路径 |
| `.claude/skills/build-metadata/SKILL.md` | `metadata/` 路径描述 |
| `.claude/skills/write-script/scripts/query_metadata.py` | `_resolve_metadata_dir()` 默认路径 |
| `make_template.py` | `EMPTY_DIRS` + 骨架模板 |
| `.gitignore` | `rawdata/` / `output/` 规则 |
