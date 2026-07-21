## 强制约束

常驻不变量。详细操作以 write-script skill 为准——本文件只声明"必须做什么"，不复制"怎么做"的命令与路径，避免两处维护漂移。

1. **改脚本前先加载 write-script skill**：任何对 `04 scripts/` 下 Python 脚本的编写或修改，必须先触发 `/write-script` 并按其流程执行，不得跳过直接动手。例外：仅限单行明确拼写 / 注释修正可跳过 skill。如 skill 不可用（调用失败或被拒绝），暂停并告知用户，不得自行推进。
2. **查数据形状用 query_metadata.py**：确认字段名、编码表、列名结构时，先查元数据（`query_metadata.py`），query_metadata.py 无结果或报错时回退读 Excel 表头；字段名对不上时以 Excel 实际列名为准。write-script 流程中优先通过 `metadata-explorer` Agent 查询，Agent 内部仍走 `query_metadata.py`。用法见 skill Step 2。**严禁直接读取 `01 rawdata/` 下的数据文件**——`.claude/settings.json` 已用 `permission.deny` 硬拦截 Read 工具读取该目录。Bash 命令中也不得用 `pd.read_excel` / `openpyxl` 等直接读 raw（`load_sheet` 内部走 loader 是允许的，因为它通过 `04 scripts/` 脚本调用）。如需查看实际数据值，通过运行 `04 scripts/` 下的脚本间接获取。
   - **唯一例外（经穷尽元数据后兜底）**：已用尽 `query_metadata.py` 的相关命令仍无法获取足够信息、且明确说明了"为什么元数据不够"时，允许通过 Bash 用 `pd.read_excel` 直接读 raw，但**单次及整个流程累计读取上限为含标题行在内最多 3 行**——即 `pd.read_excel(..., nrows=2)`（表头 1 行 + 数据 2 行 = 3 行）；用 `openpyxl` 时必须 `iter_rows` 到第 3 行即停，不得 load 整张表后遍历。**该上限适用于兜底读取的全过程，任何一次读取或中间步骤都不得突破；严禁无 `nrows` 限制的整表读取。** 仅限确认字段名 / 列结构 / 样本取值，不得用于批量取数。
3. **改脚本后必须验证**：`04 scripts/` 下脚本编写或修改后，必须实跑（数据不可用时做语法检查）确认通过，才提醒用户复核；同一错误修复尝试达 2 次仍失败时，停止并将完整报错交给用户定夺。命令与降级路径见 skill Step 5。语法检查用 `python -c "import ast; ast.parse(open(r'<路径>', encoding='utf-8').read()); print('OK')"`。

> **hooks 说明**：`.claude/hooks/` 下的 `raw_read_guard.py` 和 `syntax_check.py` 在 Claude Code 桌面版 / IDE 插件中通过 `PreToolUse`/`PostToolUse` 自动生效；命令行 `claude` 及其他客户端不支持 hooks 时，rawdata 保护依赖 `permission.deny` 规则 + 本约束文件的行为指引，语法检查依赖 skill Step 5 的手动验证。

> **分发同步**：下游项目（全局安装、零 `.claude/`）经 `build-metadata` 的 `CLAUDE.md.template`「强制约束」节获得本约束的精简版并自动加载；改动本文件的约束条目，须同步该模板。
