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

完成上述检查后，按以下规范编写。

---

## 脚本编码规范

### 文件头：路径引导 + 导入

```python
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet
```

- `pd`、`np` 直接 import，不经过任何中间模块
- `output_path` 等路径变量从 `config.py` 导入
- 报表函数从 `utils.output_format` 按需导入（`save_table_to_docx_threeline`、`export_to_excel_with_format`）
- 数据读取统一走 `utils/loaders.py` 的 `load_sheet` / `load_rand`，不直接调用 `pd.read_excel`
- 禁止使用 `# %%` Jupyter cell 标记

### 列名集中管理

导入之后、逻辑之前，用 `# ── 列名集中管理 ──` 引出声明区：

```python
# ── 列名集中管理 ──

# 导入列名（load_sheet / load_rand 的 usecols）
IMPORT_RAND  = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_ICF   = ['受试者', '知情同意书签署日期']

# 中间列名（归一化 / 筛选 / 派生阶段产生或引用）
VAR_SUBJ          = "受试者"
VAR_ICF_SIGN_DATE = "知情同意书签署日期"

# 输出列名（rename 映射目标 + 最终列序）
VAR_SCREEN_NO     = "筛选号"
OUTPUT_COLS = [VAR_SUBJ, VAR_SCREEN_NO, ...]
```

**三区职责边界：**
- `IMPORT_*`：只出现在 `load_sheet` / `load_rand` 的 `cols` 参数中
- `VAR_*`（中间）：出现在归一化、筛选、派生、连接步骤的逻辑中
- `VAR_*`（输出）+ `OUTPUT_COLS`：只出现在 rename 映射和最终选列中

### 编码字段与 `_TXT` 后缀

EDC 导出的 Excel 中，带编码表的字段有两列：
- **码值列**（如 `临床评估`）：存储编码值（如 1=正常, 2=异常无临床意义, 3=异常有临床意义, 99=其他）
- **文本列**（`_TXT` 后缀，如 `临床评估_TXT`）：存储显示文本

**规则：脚本中必须使用 `_TXT` 列，不使用码值列。**

判断依据——`query_metadata.py` 的 `fields` / `field-codelist` 输出中，带编码表的字段（格式为 `DropDownList`、`RadioButton`、`CheckBox` 等）都需要读 `_TXT` 列。元数据中 `hasOther` 标记的字段尤其重要：用户选"其他"时码值列为 99，实际文本只在 `_TXT` 列中。

`IMPORT_*` 中写原始列名（含 `_TXT`），`_RENAME_MAP` 中去掉 `_TXT` 后缀映射为语义名：

```python
# IMPORT_* 写 _TXT 列名
IMPORT_PE = ["临床评估_TXT", "异常，请描述_TXT"]

# _RENAME_MAP 去掉 _TXT 后缀
_RENAME_MAP = {
    "临床评估_TXT":    VAR_CS,     # "临床意义"
    "异常，请描述_TXT": VAR_DESC,   # "异常描述"
}
```

### 变量命名前缀

| 类别 | 前缀 | 示例 |
|---|---|---|
| DataFrame | `df_` | `df_icf`, `df_end_info`, `df_out` |
| 列名字符串常量（中间） | `VAR_` | `VAR_SUBJ`, `VAR_STUDY_END` |
| 列名字符串常量（导入） | `IMPORT_` | `IMPORT_RAND`, `IMPORT_ICF` |
| 输出列序列表 | `OUTPUT_COLS` | `OUTPUT_COLS = [VAR_SUBJ, …]` |

- 禁止用裸名 `df` 作最终结果表
- 禁止用全大写无前缀变量名存 DataFrame（`RAND` → `df_rand`）

### 八步操作模型 + 步骤标记

脚本主体按八步模型组织。每步起始处用 `# ── N 步骤名 ──` 标记：

| 序号 | 步骤名 | 说明 |
|---|---|---|
| 1 | 读取 | `load_sheet` / `load_rand` 调用 |
| 2 | 归一化 | 日期 parse、类型转换、多表 concat、去重 |
| 3 | 筛选 | 布尔过滤、组内选行、去重留首/末 |
| 4 | 变形 | melt / pivot / groupby / crosstab |
| 5 | 派生 | 日期差、`np.where`、多选拼接、regex |
| 6 | 连接 | `.merge()` / `pd.concat()` |
| 7 | 格式化 | 选列、列序、`strftime`、`%` 格式化 |
| 8 | 输出 | `save_table_to_docx_threeline` / `export_to_excel_with_format` |

- 步骤可重复、可交错（如 3→6→5→7→8），非每步必选
- 不需要的步骤直接跳过，不写空标记

### Pandas 操作风格

**链式 merge：**
```python
df_out = (df_out.merge(df_icf, on=[VAR_SUBJ], how="left")
               .merge(df_end_info, on=[VAR_SUBJ], how="left")
               .merge(df_rand, on=[VAR_SUBJ], how="left")
        )
```

**日期格式化**（步骤 7 集中执行）：
```python
df_out[VAR_STUDY_START] = df_out[VAR_STUDY_START].dt.strftime("%Y-%m-%d")
```

**日期计算**（结果列名带单位后缀）：
```python
df_out[VAR_STUDY_DAYS] = (df_out[VAR_STUDY_END] - df_out[VAR_STUDY_START]).dt.days + 1
```

**rename 映射**（集中在一个调用中）：
```python
df_out = df_out.rename(columns={
    VAR_SUBJ:          VAR_SCREEN_NO,
    VAR_ICF_SIGN_DATE: VAR_STUDY_START,
})
```

### 输出约定

**三线表 docx：**
```python
notes = ["脚注1", "脚注2"]
save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表X 标题.docx',
    '表X 标题',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
```

**Excel 清单：**
```python
export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/表X 标题.xlsx",
    "表X 标题",
    f"表X 标题（{n}例）",
)
```

- 文件路径用 f-string 拼接 `output_path`，不硬编码绝对路径
- 表格输出到 `output_path/table/`，清单输出到 `output_path/listing/`

### 禁止事项

- 不写 `# %%` / `# %% [markdown]` Jupyter cell 标记
- 不直接调用 `pd.read_excel(raw_path, …)` — 走 loader
- 不用裸 `df` 作最终表名
- 不用全大写无前缀变量名存 DataFrame
- 不在脚本顶部 `%run ../../env.py`

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

