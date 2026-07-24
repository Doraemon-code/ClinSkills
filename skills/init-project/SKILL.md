---
name: init-project
description: >
  初始化临床试验数据审核报告项目：标准化目录结构、骨架文件、EDC 类型选择、Python 虚拟环境。
  当用户提到"初始化项目"、"创建新项目"、"scaffold"、"搭项目骨架"、"搭建项目结构"、
  "准备项目环境"、或进入一个新的临床试验项目目录需要建立标准结构时触发。
---

# init-project

将任意目录初始化为标准临床试验数据审核报告项目——创建/标准化目录结构、
部署骨架配置文件、选定 EDC 类型并写入 CLAUDE.md。

## 为什么需要这个 skill

临床试验项目有固定的目录结构（`01 rawdata/` ~ `04 scripts/`）、配置文件骨架
（`.gitignore`、`config.yaml`、`requirements.txt` 等）和工具层 `utils/`。
在解析 EDC 元数据之前，必须先准备好这套基础设施。这个 skill 把这些工作自动化。

## 执行流程

### Step 0: 确保环境与依赖可用

**0a. 初始化 Git 仓库**（如尚未初始化）：

```bash
git init
```

**0b. 初始化 Python 虚拟环境并安装依赖**：

```bash
python -m venv .venv && .venv\Scripts\python -m pip install --quiet openpyxl
```

> 直接调用 `.venv\Scripts\python` 而非先激活，避免 shell 隔离导致激活失效。

**0c. 确定项目根路径**：

后续步骤中 `${CLAUDE_PROJECT_DIR}` 若未设置，改用以下命令获取项目根目录，并将结果作为 `PROJECT_ROOT` 使用：

```bash
git rev-parse --show-toplevel
```

### Step 1: 询问 EDC 类型

使用 AskUserQuestion 询问：

**问题**: 请选择 EDC 系统类型
**选项**:
- 太美5（taimei5）
- 太美6（taimei6）
- cmis / 赛美斯（cmis）
- clinflash / 易迪希（clinflash）

> EDC 类型决定表头结构约定（写入 CLAUDE.md）和解码列后缀（后续脚本依赖），
> 必须在初始化骨架文件之前确定。

### Step 2: 校验项目目录结构

读取标准结构参考文件（Read 工具不展开变量，须先将 `$CLAUDE_PLUGIN_ROOT` 解析为绝对路径——PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`——再读）：

```bash
Read "$CLAUDE_PLUGIN_ROOT/skills/init-project/reference/project-structure.md"
```

按以下顺序校验并修正：

**2a. 检测并修正目录命名**

扫描项目根目录，仅对下表中**精确列出**的旧名称执行重命名，不在表中的目录名一律跳过，不做猜测：

| 旧名称（精确匹配，仅限此列） | 标准名称 |
|---|---|
| `raw/`、`rawdata/`、`sourcedata/` | `01 rawdata/` |
| `metadata/`、`meta/` | `02 metadata/` |
| `output/`、`out/`、`reports/` | `03 output/` |
| `scripts/`、`src/`、`code/` | `04 scripts/` |
| （无旧名，缺失则创建 `.gitkeep` 占位） | `05 DRP/` |

- 已存在标准名称（如 `01 rawdata/`）→ 跳过
- 存在旧式名称（如 `raw/`）→ 用 `PowerShell: Rename-Item` 重命名
- 两者都不存在 → 创建空的标准目录（留 `.gitkeep` 占位）

> **重命名后必须同步路径引用**。按参考文件的「目录重命名时的路径同步清单」逐项更新所有受影响文件。

**2b. 初始化骨架文件**

按 `project-structure.md`「骨架文件」表（Step 2 开头已读），从 `$CLAUDE_PLUGIN_ROOT/skills/init-project/reference/skeleton/` **复制对应 `.template` 到项目根、去掉 `.template` 后缀**（`.gitattributes` / `.gitignore` 目标名需加前导点；`.claude/settings.json` 应复制到 `.claude/settings.json`）。已存在的文件**不覆盖**，仅补缺。其中 `CLAUDE.md`：复制后按下方规则替换 EDC header 区块，并提示用户填写 `<项目名>`。

> `.claude/settings.json` 预授权了临床项目常用操作（Read/Bash/Grep/Edit 等），可大幅减少权限提示。用户后续可按需增减 allow/deny 规则。

**CLAUDE.md EDC 类型替换规则：** 删除 `<!-- EDC_TYPE_HEADER_START -->` 至 `<!-- EDC_TYPE_HEADER_END -->` 之间的全部行（含注释与默认占位行），插入 Step 1 选定 EDC 对应的表头约定行——**三类取值见 `$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/header-structure.md`「写回 CLAUDE.md 的格式」节（表头规则的权威表述；Read 前须将 `$CLAUDE_PLUGIN_ROOT` 解析为绝对路径，PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`）**。

**2c. 部署工具层 `utils/`**

`utils/`（`loaders` 数据读取 + `output_docx`/`output_xlsx`/`output_format` 报表输出 + `date_compare` 等）是脚本**运行时 import** 的代码层，缺它 write-script 生成的脚本无法运行。

- 项目根**无** `utils/` → 复制工具层到项目 `utils/`，来源按布局二选一：
  - **plugin 安装（常规）**：从 `$CLAUDE_PLUGIN_ROOT/utils/` 复制全部 `.py`（plugin 自带权威源；先将 `$CLAUDE_PLUGIN_ROOT` 解析为绝对路径——PowerShell 取 `$env:CLAUDE_PLUGIN_ROOT`）。
  - **裸 skill 布局（legacy）**：上者不存在时，回退从 `$CLAUDE_PLUGIN_ROOT/skills/init-project/reference/skeleton/utils/` 复制（该目录由 legacy `install.ps1` 置入 `~/.claude/skills/` 布局）。
- 已有 `utils/`（源码仓库自身开发），或两个来源都不存在，则跳过并明确告知用户。

> **项目无需自带 `.claude/`**：skills、agents、语法检查 hook、raw 数据保护均通过 ClinSkills plugin 分发（推荐 `claude plugin install clin-skills`）或在非 plugin 语境下由 legacy `install.ps1` 全局安装，跨项目生效。

**2d. 报告校验结果**

向用户报告：
- 哪些目录被创建或重命名
- 哪些骨架文件被初始化
- 哪些路径引用已同步更新
- 无变更则报告「目录结构已符合标准」

### Step 3: 后续步骤提示

项目结构初始化完成后，提示用户：

> 项目结构已就绪。如手头有 EDC 元数据 Excel，可执行 `/clin-skills:build-metadata` 解析元数据为 JSON；
> 否则可直接将 Excel 放入 `02 metadata/` 后运行 build-metadata。

## 参考文件

| 文件 | 用途 |
|------|------|
| `$CLAUDE_PLUGIN_ROOT/skills/init-project/reference/project-structure.md` | 标准目录结构 + 骨架文件表 + 重命名同步清单 |
| `$CLAUDE_PLUGIN_ROOT/skills/init-project/reference/skeleton/` | 骨架 `.template` 文件 |

## 与 build-metadata 的关系

`init-project` 负责**项目基础设施**（目录 + 配置 + utils/ + EDC 类型），
`build-metadata` 负责**元数据解析**（定位 Excel → 解析 → 输出 JSON）。
两个 skill 可独立运行——先 init-project 搭好骨架，
等拿到元数据 Excel 后再运行 build-metadata 也完全正常。
