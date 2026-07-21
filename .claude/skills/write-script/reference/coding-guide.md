# 脚本编码规范

本文件是 write-script skill 的编码参考。SKILL.md 在"编写脚本"步骤中引用本文件。

> **维护说明**：`review-checklist.md` 是本文件的「可机器执行」检查表版本（供 `python-reviewer` Agent 使用）。
> 修改本文件中的任何规则后，**必须同步更新 `review-checklist.md`**；反之亦然。
> 文件路径：`.claude/skills/write-script/reference/review-checklist.md`

---

## 文件头：路径引导 + 导入

```python
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.output_format import save_table_to_docx_threeline, export_to_one_excel_with_format
from utils.loaders import load_sheet
```

- `pd`、`np` 直接 import，不经过任何中间模块
- `output_path` 等路径变量从 `config.py` 导入
- 报表函数从 `utils.output_format` 按需导入（`save_table_to_docx_threeline`、`export_to_one_excel_with_format`）
- 数据读取统一走 `utils/loaders.py` 的 `load_sheet`，不直接调用 `pd.read_excel`
- 禁止使用 `# %%` Jupyter cell 标记

## 系统列（6 个定位角色）

EDC 导出的 rawdata 中，系统列不在 FormField 元数据里，列名随 EDC 类型而变——有的用**字段标签**（描述，语言随项目，常见中文也可能英文），有的用 **SAS 变量名**（缩写）：clinflash / taimei5 / taimei6 用字段标签，cmis 用 SAS 变量名；均以 `SYSTEM_COLUMNS` 注册表为准。**禁止在脚本主体硬编码系统列字面量**——一律经 `utils.loaders.system_cols()` 取值。

6 个角色可完全定位 EDC 中的每一个数据点，同一 EDC 跨研究固定：

| 角色 | 含义 | clinflash | taimei5 | taimei6（中文） | taimei6（英文） | cmis |
|---|---|---|---|---|---|---|
| `center` | 中心编号 | 试验中心编号 | 中心编号 | 中心编号 | Site ID | SITEID |
| `subject` | 筛选号 | 受试者编号 | 受试者 | 受试者编号 | Subject ID | SUBJID |
| `visit_name` | 访视名称 | 数据节 | 访视名称 | 表单集名称 | Formset Name | VISIT |
| `visit_seq` | 访视序号 | Instance顺序号 | 访视号 | 表单集记录号 | Formset Repeat No. | VISITNUM |
| `form_name` | 表单名称 | 数据页 | 页面名称 | 表单名称 | Form Name | FORMNAME |
| `row` | 字段行号 | 行号 | 记录号 | 字段记录号 | Item Repeat No. | TOPICSEQ |

> taimei5 / taimei6 列名均已按实际导出核实（第 1 行字段标签、第 2 行 SAS 变量名被跳过）；两者同属太美、表头结构一致，但字段标签不完全相同（如 subject：taimei5 `受试者` / taimei6 中文 `受试者编号`；visit_name：taimei5 `访视名称` / taimei6 中文 `表单集名称`），一律以 `SYSTEM_COLUMNS` 注册表为准。
> taimei6 同时登记中/英两套系统列；`system_cols()` 按 `FormField.json` 的 `itemName` 语言自动选用（`HEADER_LANGUAGE`：`zh` / `en`）。
> **同步约定**：本表是 `utils/loaders.py` 的 `SYSTEM_COLUMNS` 的文档副本，权威以注册表为准；改动任一处（增删 EDC / 改列名）必须同步另一处。

```python
from utils.loaders import load_sheet, system_cols

VAR_SUBJ    = system_cols("subject")   # 按 EDC 取值，如 clinflash→受试者编号 / taimei5→受试者 / cmis→SUBJID
VAR_ROW     = system_cols("row")
VAR_VISIT   = system_cols("visit_name")
```

`system_cols()` 按 `EDC_TYPE` 从 `utils/loaders.py` 的 `SYSTEM_COLUMNS` 注册表取值。未登记的 EDC 抛清晰错误，按提示在注册表补一行即可。输出表如需通用中文表头，将读取的 EDC 专属列名 rename 为通用标签（如 `受试者`→`筛选号`）。

## 列名集中管理

导入之后、逻辑之前，用 `# ── 列名集中管理 ──` 引出声明区：

**列名类型规则：脚本读取用「字段标签」还是「SAS 变量名」，由 `CLAUDE.md` 的表头约定决定（clinflash/taimei5/taimei6 用字段标签，cmis 用 SAS 变量名）；标签语言随项目（中文或英文）。`IMPORT_*`（EDC 导出的实际列名）与中间 `VAR_*` 全程与之一致；只有最终输出结果表的列名（输出 `VAR_*` + `OUTPUT_COLS`）必须 rename 为中文报表表头。即「内部按 EDC 实际列名、输出中文」。**

> **clinflash 示例**（字段标签）：`IMPORT_SV = ["受试者编号", "访视日期(VISDAT)"]`，`VAR_SUBJ = "受试者编号"`
> **cmis 示例**（SAS 变量名）：`IMPORT_SV = ["SUBJID", "VISDAT"]`，`VAR_SUBJ = "SUBJID"`

```python
# ── 列名集中管理 ──

# 导入列名（load_sheet 的 usecols）—— 按 CLAUDE.md 约定（clinflash/taimei5/taimei6 用字段标签 / cmis 用 SAS 名）
# clinflash: IMPORT_SV  = ["受试者编号", "访视日期(VISDAT)"]
# cmis:     IMPORT_SV  = ["SUBJID", "VISDAT"]
IMPORT_SV  = ["受试者编号", "访视日期(VISDAT)"]
IMPORT_ICF = ["受试者编号", "知情同意书签署日期(DSSTDAT)"]

# 中间列名（归一化 / 筛选 / 派生阶段产生或引用）—— 与 IMPORT 同类型（标签或 SAS 名）
VAR_SUBJ          = "受试者编号"
VAR_ICF_SIGN_DATE = "知情同意书签署日期(DSSTDAT)"

# 输出列名（rename 映射目标 + 最终列序）—— 中文：还原为中文表头
VAR_SCREEN_NO     = "筛选号"
VAR_STUDY_START   = "知情同意书签署日期"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_STUDY_START]
```

**三区职责边界：**
- `IMPORT_*`（EDC 实际列名：标签或 SAS 名）：只出现在 `load_sheet` / `load_rand` 的 `cols` 参数中
- `VAR_*`（中间，与 IMPORT 同）：出现在归一化、筛选、派生、连接步骤的逻辑中
- `VAR_*`（输出，中文）+ `OUTPUT_COLS`：只出现在 rename 映射和最终选列中；输出表禁止保留 SAS 名或英文列名

## 编码字段与解码后缀

EDC 导出的 Excel 中，带编码表的字段有两列：
- **码值列**（如 `临床评估`）：存储编码值（如 1=正常, 2=异常无临床意义, 99=其他）
- **解码列**（加后缀，如 `临床评估_TXT`）：存储显示文本

**规则：脚本中必须使用解码列，不使用码值列。** 后缀/列名格式因 EDC 系统而异，由 `query_metadata.py fields` 的输出自动给出（系统感知：clinflash 用 `{itemName}({fieldOID})` 列名含解码值、taimei5/6 → `_TXT`、cmis → `_DEC`）。

判断依据——`query_metadata.py` 的 `fields` 输出中，带编码表的字段（格式为 `下拉框`、`水平单选框`、`垂直单选框`、`多选框`、`动态多选搜索框` 等）都需要读解码列。`hasOther` 标记的字段尤其重要：用户选"其他"时码值列为编码（如 99），实际文本只在解码列中。

**「其他」选项与自由文本补充字段：「其他」选项总是伴随一个自由文本补充字段（如 `若其他，请详述`），记录用户填写的具体值。核查/输出时，当主选项为「其他」，必须读取该补充字段的值进行判断，不可仅凭主选项列下结论。** 这一规则适用于所有含 `hasOther` 标记的编码字段。

**「是否有XXX」门控字段：EDC 许多表单以「是否有XXX」（是/否）开头。当选「否」时，该表单的后续字段均为合理空值（受试者不具备该条件，无需填写），核查「未填写」等问题前必须排除这些记录，否则会产生大量误报。** 例如 CM 的 `CMYN`、PR 的 `PRYN`、EC 的 `ECYN`、MH 的 `MHYN` 等。

`IMPORT_*` 中写 `query_metadata.py fields` 标注的脚本列名，`_RENAME_MAP` 中映射为语义名：

```python
# clinflash: IMPORT_* 写 {itemName}({fieldOID}) 列名（含解码值）
IMPORT_PE = ["临床评估(MIPERF)", "异常，请描述(MIDESC)"]

# _RENAME_MAP 去掉括号后缀
_RENAME_MAP = {
    "临床评估(MIPERF)":    VAR_CS,     # "临床意义"
    "异常，请描述(MIDESC)": VAR_DESC,   # "异常描述"
}
```

**CheckBox（复选框）跨系统差异——务必以 `query_metadata.py` 输出为准，不要硬套 "1" 或 "Y"：**

- **taimei5**：复选框只有**码值列、无解码列**，码值列直接存勾选值（通常 `"1"`=勾选，`"0"`/空=未选）。`fields` 标作 `勾选=1 … ← 用此列(码值列,无解码)`，脚本直接判 `df[col] == "1"`，**不要加 `_TXT` 后缀**（解码列不存在，会 KeyError）。
- **taimei6**：已移除 CheckBox 控件，单选项字段是 `count==1` 的 codelist（码值 `"Y"`、解码 `"√"`），按普通编码字段走解码列。
- **cmis**：复选框自带 codelist，按普通编码字段走解码列。
- **clinflash**：`多选框` / `动态多选搜索框` 的解码值直接在 `{itemName}({fieldOID})` 列中，`fields` 标作 `← 用此列(含解码值)`，按普通编码字段处理即可。

## 变量命名前缀

| 类别 | 前缀 | 示例 |
|---|---|---|
| DataFrame | `df_` | `df_icf`, `df_end_info`, `df_out` |
| 列名字符串常量（中间） | `VAR_` | `VAR_SUBJ`, `VAR_STUDY_END` |
| 列名字符串常量（导入） | `IMPORT_` | `IMPORT_RAND`, `IMPORT_ICF` |
| 输出列序列表 | `OUTPUT_COLS` | `OUTPUT_COLS = [VAR_SUBJ, …]` |

- 禁止用裸名 `df` 作最终结果表
- 禁止用全大写无前缀变量名存 DataFrame（`RAND` → `df_rand`）

## 八步操作模型 + 步骤标记

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
| 8 | 输出 | `save_table_to_docx_threeline` / `export_to_one_excel_with_format` |

- 步骤可重复、可交错（如 3→6→5→7→8），非每步必选
- 不需要的步骤直接跳过，不写空标记

## Pandas 操作风格

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

## 输出约定

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
export_to_one_excel_with_format(
    df_out,
    f"{output_path}/listing/表X 标题.xlsx",
    "表X 标题",
    f"表X 标题（{n}例）",
    add_title=True,
)
```

- 文件路径用 f-string 拼接 `output_path`，不硬编码绝对路径
- 表格输出到 `output_path/table/`，清单输出到 `output_path/listing/`
- **docx 三线表命名**：`表格NN-标题.docx`，如 `表格01-知情同意书签署日期汇总.docx`
- **xlsx 清单命名**：`清单NN-标题.xlsx`，如 `清单01-筛选号与知情同意书签署日期矛盾核查.xlsx`
- NN 为两位数字序号，按脚本在章节内的编号递增
- **Excel sheet name 禁止使用全角冒号 `：`**，否则 Excel 打开时触发修复提示。用 `-` 替代

## 禁止事项

- 不写 `# %%` / `# %% [markdown]` Jupyter cell 标记
- 不直接调用 `pd.read_excel(raw_path, …)` — 走 loader
- 不用裸 `df` 作最终表名
- 不用全大写无前缀变量名存 DataFrame
- 不在脚本顶部 `%run ../../env.py`
