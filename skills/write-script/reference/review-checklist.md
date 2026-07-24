# 脚本编码规范审查清单

> **维护说明**：本文件是 `coding-guide.md` 的「可机器执行」检查表版本。
> 修改 `coding-guide.md` 中的任何规则后，**必须同步更新本文件**；反之亦然。
> 文件路径：`$CLAUDE_PLUGIN_ROOT/skills/write-script/reference/coding-guide.md`

供 `python-reviewer` Agent 在 write-script Step 5（`mode: full`）使用。逐项检查，返回违规项列表。

## 致命项（运行时错误 / 数据错误）

- [ ] **系统列硬编码**：禁止在脚本主体写死 `"受试者编号"` / `"SUBJID"` / `"行号"` 等系统列字面量。必须经 `utils.loaders.system_cols()` 取值。
- [ ] **码值列误用**：带编码表的字段必须使用解码列（`fields` 输出标注 `← 用此列`），不得使用码值列。CheckBox 字段标注 `码值列,无解码` 的除外。
- [ ] **直接读 raw**：禁止 `pd.read_excel(raw_path, ...)` 或 `openpyxl.load_workbook(...)` 直接读 `01 rawdata/`。必须走 `utils.loaders.load_sheet()`。
- [ ] **解码后缀硬编码**：禁止手写 `_TXT` / `_DEC` 后缀。解码列名由 `query_metadata.py fields` 输出提供。
- [ ] **clinflash 列名格式错误**：clinflash 项目的列名为 `{itemName}({fieldOID})` 格式（如 `临床评估(MIPERF)`），禁止只用 `itemName` 或只用 `fieldOID`。
- [ ] **输出路径未使用标准变量**：输出必须使用 `config.py` 的 `output_table_dir` / `output_listing_dir`，禁止绕过它们直接用 `output_path` 拼接或写死绝对路径。这两个变量由 `config.py` 自动保证日期与 rawdata 一致及子目录路由。

## 重要项（违反编码规范）

- [ ] **三区边界混乱**：`IMPORT_*` 只出现在 `load_sheet` 的 `cols` 参数；中间 `VAR_*` 用于逻辑；输出 `VAR_*`（中文）+ `OUTPUT_COLS` 用于最终选列。禁止 `IMPORT_*` 变量出现在筛选/派生逻辑中。
- [ ] **八步模型标记缺失**：脚本主体缺少 `# ── N 步骤名 ──` 标记（至少应有读取/筛选/输出步骤）。
- [ ] **变量命名违规**：DataFrame 未用 `df_` 前缀；列名常量未用 `VAR_` / `IMPORT_` 前缀；最终表用裸名 `df`；全大写无前缀变量存 DataFrame。
- [ ] **输出列名未还原中文**：最终输出表列名必须为中文报表表头。若内部用的是 SAS 变量名（cmis）或英文字段标签，输出前必须 rename 为中文。
- [ ] **文件头缺少路径引导**：脚本未包含 `sys.path.insert(0, _project_root)` 引导块。
- [ ] **导入方式错误**：未从 `config` import `output_table_dir` / `output_listing_dir`；未从 `utils` import 报表/读取函数；`pd`/`np` 经过中间模块间接 import。

## 建议项（可维护性）

- [ ] **硬编码输出路径**：文件路径未使用 `output_table_dir` / `output_listing_dir` 变量拼接，写死了绝对路径。
- [ ] **门控字段未排除**：涉及 `hasOther` 或门控字段（如 `CMYN`/`MHYN`）的表单，未在筛选时排除"否"记录。
- [ ] **日期格式化位置不当**：日期格式化（`strftime`）写在步骤 2-6 而非集中在步骤 7。
- [ ] **链式 merge 未使用**：多次 merge 未用链式写法，中间产生一次性临时 DataFrame。
- [ ] **Jupyter cell 标记**：脚本中含 `# %%` 或 `# %% [markdown]` 标记。
- [ ] **docx/xlsx 命名不规范**：文件名未遵循 `表格NN-标题.docx` / `清单NN-标题.xlsx` 格式；Excel sheet name 含全角冒号 `：`。
