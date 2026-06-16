## 强制约束

常驻不变量。详细操作以 write-script skill 为准——本文件只声明"必须做什么"，不复制"怎么做"的命令与路径，避免两处维护漂移。

1. **改脚本前先加载 write-script skill**：任何对 `scripts/` 下 Python 脚本的编写或修改，必须先触发 `/write-script` 并按其流程执行，不得跳过直接动手。
2. **查数据形状用 query_metadata.py**：确认字段名、编码表、列名结构时，先查元数据（`query_metadata.py`），查不到才回退读 Excel 表头。用法见 skill Step 2。
3. **改脚本后必须验证**：`scripts/` 下脚本编写或修改后，必须实跑（数据不可用时做语法检查）确认通过，才提醒用户复核；遇报错且无法判断修复方向时，把完整报错交给用户定夺。命令与降级路径见 skill Step 4。语法地板已由 PostToolUse 钩子（`.claude/hooks/syntax_check.py`）自动执行——你的职责是更高一层的实跑与输出文件核对。
