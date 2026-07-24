# 标准项目目录结构

本文件是临床试验数据审核报告项目的标准目录结构。
`init-project` skill 的 Step 2 以此为基准校验项目目录，如有偏离则自动修正。

## 目录树

```
<project_root>/
├── 01 rawdata/                  # 原始数据（不入 Git）
├── 02 metadata/                 # EDC 元数据 Excel + build-metadata 生成的 JSON
├── 03 output/                   # 生成的报表（不入 Git）
├── 04 scripts/                  # 分析代码（新脚本默认平铺；已有章节目录保持不变）
├── 05 DRP/                      # 数据审核计划 Excel + parse-drp 生成的 DRP.json
├── utils/                       # 公共工具函数
│   ├── __init__.py
│   ├── loaders.py               # 数据读取层（load_sheet / system_cols）
│   ├── output_docx.py           # docx 三线表输出
│   ├── output_xlsx.py           # xlsx 清单输出
│   └── output_format.py         # 报表输出聚合入口（re-export docx/xlsx）
├── .gitattributes               # Git 行尾与二进制规则
├── .gitignore                   # Git 忽略规则
├── CLAUDE.md                    # 项目说明与 Claude Code 约定
├── config.py                    # 路径配置加载器（从 config.yaml 读取）
├── config.yaml                  # 数据路径配置
└── requirements.txt             # Python 依赖
```

> harness（skills / agents / hooks / settings）**不在项目内**——通过 ClinSkills plugin 分发（推荐 `claude plugin install clin-skills`）或全局安装 `install.ps1`（legacy）；项目只含数据、脚本、`utils/` 与配置。

## 目录命名规则

数据目录使用 `序号 名称` 格式（序号为两位数字，后跟空格），确保文件管理器中排序一致：

| 序号 | 目录名 | 用途 | 入 Git |
|------|--------|------|--------|
| 01 | rawdata | EDC 导出的原始 Excel 数据 | 否 |
| 02 | metadata | 元数据 Excel + 解析后的 JSON | 是 |
| 03 | output | 生成的报表文件 | 否 |
| 04 | scripts | 数据核查 Python 脚本 | 是 |
| 05 | DRP | 数据审核计划 Excel + parse-drp 解析的 JSON | 是 |

## 骨架文件

以下基础配置文件的模板存放在 `skeleton/` 目录。初始化时**复制对应 `.template` 文件到项目根、去掉 `.template` 后缀**即可（`.gitattributes` / `.gitignore` 目标名需加前导点）：

| 目标文件 | 模板 | 说明 |
|---|---|---|
| `.gitattributes` | `skeleton/gitattributes.template` | Git 行尾与二进制规则 |
| `.gitignore` | `skeleton/gitignore.template` | Git 忽略规则 |
| `CLAUDE.md` | `skeleton/CLAUDE.md.template` | 项目说明与约定；复制后按 EDC 类型替换 `<!-- EDC_TYPE_HEADER_START/END -->` 区块，含 Overview / Permissions / Conventions / Agent 清单 |
| `config.py` | `skeleton/config.py.template` | 从 config.yaml 读取路径的加载器 |
| `config.yaml` | `skeleton/config.yaml.template` | 数据路径配置（保留 `<日期>` 等占位，用户后填） |
| `requirements.txt` | `skeleton/requirements.txt.template` | Python 依赖 |
| `.claude/settings.json` | `skeleton/settings.json.template` | Claude Code 权限预授权（仅当目标不存在时复制，已存在则不覆盖以免丢失用户自定义） |

> 模板一律用 `.template` 后缀，避免 `.gitignore` / `config.py` 等在本目录被 git 或工具当作生效文件。
> **工具层 `utils/`**（不走根 `.template`）：由 init-project Step 2c 部署到项目根——plugin 安装时从 `$CLAUDE_PLUGIN_ROOT/utils/`（plugin 自带权威源）复制；裸 skill 布局回退 `skeleton/utils/`（由 legacy install.ps1 置入）。源码仓库自身开发时根 `utils/` 已存在，跳过。raw 数据保护与语法检查 hook 随 ClinSkills plugin 加载（通过 `hooks/hooks.json` 声明），项目不再自带 `.claude/hooks/`。

## 目录重命名时的路径同步清单

当数据目录（01-04）发生重命名时，以下文件中的路径引用必须同步更新：

| 文件 | 引用内容 |
|------|---------|
| `config.yaml` | `raw_path` / `pd_path` / `code_path` / `remark_path` / `timewin_path` / `output_path`；output 日期由 `config.py` 从 `raw_path` 自动提取 |
| `CLAUDE.md` | 目录树、Permissions 节 |
| `.claude/settings.json` | permission deny / allow 规则 |
| `scripts/syntax_check.py` | `parts[0]` 检查 + docstring（Claude Code 兼容） |
| `scripts/raw_read_guard.py` | `_under_dir()` 参数 + docstring（Claude Code 兼容） |
| `skills/write-script/SKILL.md` | 验证命令路径 |
| `skills/init-project/SKILL.md` | `metadata/` 路径描述 |
| `skills/write-script/scripts/query_metadata.py` | `_resolve_metadata_dir()` 默认路径 |
| `skills/init-project/reference/skeleton/*.template` | `config.yaml` / `gitignore` / `CLAUDE.md` 模板中的目录路径 |
| `.gitignore` | `rawdata/` / `output/` 规则 |
| `skills/write-script/reference/coding-guide.md` | `04 scripts/` 引用 |
| `skills/init-project/reference/project-structure.md` | 目录树 + sync checklist 自身 |

> 上表中 `.claude/settings.json` 与 `scripts/*.py` 三行仅适用于 plugin 源仓库——临床项目不含 harness 文件（见本文「目录树」节注），项目内重命名时跳过这三行。
