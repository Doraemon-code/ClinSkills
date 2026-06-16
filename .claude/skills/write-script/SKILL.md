---
name: write-script
description: 根据用户需求编写数据核查脚本。当用户要求写新脚本、新清单、新表格、新增数据核查程序、写 Python 分析脚本、或口述/示例一个输出结果需要实现时触发。
---

# write-script

根据用户需求，查询元数据，编写符合项目规范的 Python 数据核查脚本。

## 工作流程

### 0. 确认源数据表头结构

**优先读取 CLAUDE.md**：先查看 `CLAUDE.md` 的 Conventions 中是否已记录 `表头结构`（`header` / `skiprows`）。有则直接沿用，无需再问。

没有记录时，用 AskUserQuestion 向用户确认：

- **标题行数**：Excel 前几行是标题/说明行（非数据、非列名）？常见的有 0 行（第 1 行即列名）、1 行（第 1 行标题，第 2 行列名）
- **英文列名行**：第几行是英文列名（SAS 字段名行）？（1-indexed，如"第 2 行"）

确认后**立即写入 `CLAUDE.md` 的 Conventions 节**，格式如下：

```markdown
- 表头结构：`header=0, skiprows=[1]`（第 1 行中文列名，第 2 行英文列名被跳过）
```

这样后续脚本无需重复询问。

### 1. 理解需求

需求来源可能是：
- 用户口述（如"我需要一个不良事件汇总表"）
- 参考已有脚本（如"按清单01的格式做一个新的"）
- 用户给出输出结果/图表示例

**关键动作：** 确认输出形状（三线表 docx 还是 Excel 清单）、涉及哪些数据域、筛选条件是什么。

任何时候需求不够清晰，直接用 AskUserQuestion 向用户提问。常见需要澄清的点：
- 输出是 docx 三线表还是 xlsx 清单
- 筛选条件（全量还是某个子集）
- 多列信息如何合并（取首/末、拼接、优先级）
- 合计行/百分比计算规则

### 2. 查询元数据

用 `query_metadata.py` 定位所需表和字段。路径相对于项目根目录：

```bash
python .claude/skills/write-script/scripts/query_metadata.py <command> [args]
```

命令清单与用法以脚本为准——**不带参数运行可打印完整命令列表**。常用命令速览：

| 命令 | 用途 |
|------|------|
| `summary` | 元数据概览（表单数 / 字段数 / 编码表数） |
| `search <关键字>` | 跨表搜索字段（按需求关键字定位候选） |
| `fields <表单名>` | 查看某表单全部字段（格式、编码表） |
| `codelist <名称>` | 查看编码表枚举值 |
| `find-field <SAS名>` | 按 SAS 字段名定位所在表单 |
| `field-codelist <字段名>` | 按字段名直接查其编码表枚举值 |
| `forms` / `codelists` / `visits` | 列出全部表单 / 编码表 / 访视 |

**查询策略（渐进式披露）：**

> 原则：用 `query_metadata.py` 按需逐条查询，**不要一次性读取整个 JSON 文件**。
> 先粗后细：`search` 定位 → `fields` 确认 → `codelist` 取值，每步只获取当前需要的信息。

1. 先 `search` 需求中的关键字，定位候选字段
2. 再 `fields <表单名>` 确认字段详情（格式、编码表）
3. 涉及编码值时 `codelist <名称>` 查看枚举
4. 确认哪些字段的列名带 `_TXT` 后缀（EDC 中表示文本值，load_sheet 读取时需加 `_TXT`）

**注意：** EDC 的 sheet 名就是表单 OID（如 `DS_END`、`EC_ED`、`SV`），不是中文表单名。`formOID` 字段就是 `load_sheet` 的第一个参数。

**元数据字段说明（FormField.json）：**

| 字段 | 含义 | 脚本中的用途 |
|---|---|---|
| `formOID` | 表单 OID = Excel sheet 名 | `load_sheet()` 第一个参数 |
| `formName` | 表单中文名 | 查询时定位表单 |
| `sasFieldName` | SAS 字段名（英文） | SAS 到 pandas 的映射参考 |
| `itemName` | 字段中文标签 = Excel 列名 | `IMPORT_*` / `load_sheet` 的 `cols` 参数 |
| `fieldFormat` | 字段类型（DropDownList / RadioButton / LongText / Date 等） | 判断是否需要 `_TXT` 列 |
| `codeList` | 编码表引用（name / count） | `codelist` 命令查枚举值 |
| `codeList.hasOther` | 是否含"其他"自由文本选项 | 必须读 `_TXT` 列，码值列只有 99 |

有 `codeList` 的字段一定有两列：码值列（`itemName`）和文本列（`itemName` + `_TXT`）。脚本中始终用 `_TXT` 列。

### 3. 编写脚本

确认数据需求后，**在动手写代码之前**先做两项检查：

**检查 utils/ 已有函数：** 读 `utils/loaders.py` 和 `utils/output_format.py`，看是否有可直接复用的函数。不重复造轮子。

**检查是否应封装为通用工具：** 如果当前逻辑（如日期解析、特定域的筛选合并、格式转换）很可能在后续脚本中重复出现，先将其封装到 `utils/` 中再调用，而不是在脚本内写死。

完成上述检查后，按编码规范编写。**首次编写脚本前**读取 `coding-guide.md`（同会话已读可跳过）：

```bash
Read .claude/skills/write-script/reference/coding-guide.md
```

### 9. 运行验证

脚本编写或修改完成后，**必须实际运行**，不得跳过。

**正常路径（原始数据可用）：**

```bash
python scripts/<章节>/<脚本名>.py
```

从项目根目录执行。检查：

1. **退出码为 0** — 有非零退出码即为失败
2. **输出文件已生成** — 检查 `output_path` 下对应路径的文件是否存在
3. **输出文件非空** — 文件大小 > 0

**降级路径（原始数据不可用）：**

```bash
python -c "import ast; ast.parse(open(r'scripts/<章节>/<脚本名>.py', encoding='utf-8').read()); print('语法检查通过')"
```

仅验证语法正确性，提醒用户数据层未验证。

**错误处理：**

- 能定位原因 → 修复后重跑，循环直到通过
- 无法判断修复方向（如数据层报错、不确定的业务逻辑歧义）→ **直接将完整报错输出给用户**，附上你的初步分析（如有），由用户指定下一步方向。不要猜测性修复

**验证通过后：** 提醒用户查看输出文件进行复核。

---

文件命名：`清单NN：标题.py` 或 `表格NN：标题.py`（NN 为两位数字序号）。
