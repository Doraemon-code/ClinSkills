# 脚本编码规范

本文件是 write-script skill 的编码参考。SKILL.md 在"编写脚本"步骤中引用本文件。

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
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet
```

- `pd`、`np` 直接 import，不经过任何中间模块
- `output_path` 等路径变量从 `config.py` 导入
- 报表函数从 `utils.output_format` 按需导入（`save_table_to_docx_threeline`、`export_to_excel_with_format`）
- 数据读取统一走 `utils/loaders.py` 的 `load_sheet` / `load_rand`，不直接调用 `pd.read_excel`
- 禁止使用 `# %%` Jupyter cell 标记

## 列名集中管理

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

## 编码字段与解码后缀

EDC 导出的 Excel 中，带编码表的字段有两列：
- **码值列**（如 `临床评估`）：存储编码值（如 1=正常, 2=异常无临床意义, 99=其他）
- **解码列**（加后缀，如 `临床评估_TXT`）：存储显示文本

**规则：脚本中必须使用解码列，不使用码值列。** 后缀因 EDC 系统而异，由 `query_metadata.py fields` 的输出自动给出（系统感知，如太美5/太美6 → `_TXT`，赛美斯 → `_DEC`）。

判断依据——`query_metadata.py` 的 `fields` 输出中，带编码表的字段（格式为 `DropDownList`、`RadioButton`、`CheckBox` 等）都需要读解码列。`hasOther` 标记的字段尤其重要：用户选"其他"时码值列为编码（如 99），实际文本只在解码列中。

`IMPORT_*` 中写原始列名（含后缀），`_RENAME_MAP` 中去掉后缀映射为语义名：

```python
# IMPORT_* 写解码列名（含后缀）
IMPORT_PE = ["临床评估_TXT", "异常，请描述_TXT"]

# _RENAME_MAP 去掉后缀
_RENAME_MAP = {
    "临床评估_TXT":    VAR_CS,     # "临床意义"
    "异常，请描述_TXT": VAR_DESC,   # "异常描述"
}
```

**CheckBox（复选框）跨系统差异——务必以 `query_metadata.py` 输出为准，不要硬套 "1" 或 "Y"：**

- **taimei5**：复选框只有**码值列、无解码列**，码值列直接存勾选值（通常 `"1"`=勾选，`"0"`/空=未选）。`fields` 标作 `勾选=1 … ← 用此列(码值列,无解码)`，脚本直接判 `df[col] == "1"`，**不要加 `_TXT` 后缀**（解码列不存在，会 KeyError）。
- **taimei6**：已移除 CheckBox 控件，单选项字段是 `count==1` 的 codelist（码值 `"Y"`、解码 `"√"`），按普通编码字段走解码列。
- **cmis**：复选框自带 codelist，按普通编码字段走解码列。

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
| 8 | 输出 | `save_table_to_docx_threeline` / `export_to_excel_with_format` |

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
export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/表X 标题.xlsx",
    "表X 标题",
    f"表X 标题（{n}例）",
)
```

- 文件路径用 f-string 拼接 `output_path`，不硬编码绝对路径
- 表格输出到 `output_path/table/`，清单输出到 `output_path/listing/`

## 禁止事项

- 不写 `# %%` / `# %% [markdown]` Jupyter cell 标记
- 不直接调用 `pd.read_excel(raw_path, …)` — 走 loader
- 不用裸 `df` 作最终表名
- 不用全大写无前缀变量名存 DataFrame
- 不在脚本顶部 `%run ../../env.py`
