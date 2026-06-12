---
path: "**/*.py"
---

# scripts/ 脚本编码规范

## 1. 文件头：路径引导 + 导入

每个脚本第一行为路径引导，随后从 `env` 和 `utils` 导入。禁止使用 `# %%` Jupyter cell 标记。

```python
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, np, output_path, save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet
```

- `from env import …` 按需引入，只列脚本实际用到的对象
- 数据读取统一走 `utils/loaders.py` 的 `load_sheet` / `load_rand`，不直接调用 `pd.read_excel(raw_path, …)`
- `# %run env.py` 是 Jupyter 旧模式，新脚本不用

---

## 2. 列名集中管理

脚本导入之后、逻辑之前，用 `# ── 列名集中管理 ──` 引出一个声明区，分三小节：

```python
# ── 列名集中管理 ──

# 导入列名（load_sheet / load_rand 的 usecols）
IMPORT_RAND  = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_ICF   = ['受试者', '知情同意书签署日期', '知情同意书签署时间']

# 中间列名（归一化 / 筛选 / 派生阶段产生或引用）
VAR_SUBJ          = "受试者"
VAR_ICF_SIGN_DATE = "知情同意书签署日期"
VAR_SIGN_DT       = "签署日期时间"

# 输出列名（rename 映射目标 + 最终列序）
VAR_SCREEN_NO     = "筛选号"
VAR_STUDY_START   = "研究开始日期"
OUTPUT_COLS = [VAR_SUBJ, VAR_SCREEN_NO, ...]
```

**三区职责边界**：
- `IMPORT_*`：只出现在 `load_sheet` / `load_rand` 的 `cols` 参数中
- `VAR_*`（中间）：出现在归一化、筛选、派生、连接步骤的逻辑中
- `VAR_*`（输出）+ `OUTPUT_COLS`：只出现在 rename 映射和最终选列中

---

## 3. 变量命名前缀

| 类别 | 前缀 | 示例 |
|---|---|---|
| DataFrame | `df_` | `df_icf`, `df_end_info`, `df_out` |
| 列名字符串常量（中间） | `VAR_` | `VAR_SUBJ`, `VAR_STUDY_END` |
| 列名字符串常量（导入） | `IMPORT_` | `IMPORT_RAND`, `IMPORT_ICF` |
| 输出列序列表 | `OUTPUT_COLS` | `OUTPUT_COLS = [VAR_SUBJ, …]` |

- 禁止用裸名 `df` 作最终结果表；中间临时 `df_first` / `df_last` 可接受
- 禁止用全大写无前缀变量名存 DataFrame（如 `RAND = load_rand(…)` → 改为 `df_rand = load_rand(…)`）

---

## 4. 八步操作模型 + 步骤标记

脚本主体按八步模型组织。每步起始处用注释标记，格式固定为：

```python
# ── N 步骤名 ──
```

可用的步骤序号与名称：

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

---

## 5. 数据读取约定

- 所有 Excel 读取通过 `load_sheet(sheet_name, cols)` 或 `load_rand(cols)` 完成
- `dtype=str` 由 loader 层统一处理，脚本不重复指定
- 日期/数值转换在步骤 2 归一化阶段统一做，读取阶段保持原始字符串

---

## 6. Pandas 操作风格

### 链式 merge
多个 `.merge()` 用括号包裹、换行对齐：

```python
df_out = (df_out.merge(df_icf, on=[VAR_SUBJ], how="left")
               .merge(df_end_info, on=[VAR_SUBJ], how="left")
               .merge(df_rand, on=[VAR_SUBJ], how="left")
        )
```

### 日期格式化
统一用 `strftime("%Y-%m-%d")`，在步骤 7 格式化阶段集中执行：

```python
df_out[VAR_STUDY_START] = df_out[VAR_STUDY_START].dt.strftime("%Y-%m-%d")
```

### 日期计算
结果列名带单位后缀：`"试验时长（天）"`、`"治疗天数（天）"`

```python
df_out[VAR_STUDY_DAYS] = (df_out[VAR_STUDY_END] - df_out[VAR_STUDY_START]).dt.days + 1
```

### rename 映射
集中在一个 `rename(columns={…})` 调用中完成，用中文列名常量作 key：

```python
df_out = df_out.rename(columns={
    VAR_SUBJ:          VAR_SCREEN_NO,
    VAR_ICF_SIGN_DATE: VAR_STUDY_START,
    VAR_CASE_TYPE:     VAR_SUBJ,
})
```

---

## 7. 输出约定

### 三线表 docx
```python
notes = ["脚注1", "脚注2"]

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表1 首末例受试者情况.docx',
    '表1 首末例受试者情况',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
```

### Excel 清单
```python
export_to_excel_with_format(
    df,
    f"{output_path}/listing/表34 完成试验受试者清单.xlsx",
    "表34 完成试验受试者清单",
    f"表34 完成试验受试者清单（{n}例）",
)
```

- 文件路径统一用 f-string 拼接 `output_path`，不硬编码绝对路径
- 表格输出到 `output_path/table/`，清单输出到 `output_path/listing/`

---

## 8. 不做的事情

- 不在脚本中写 `# %%` / `# %% [markdown]` Jupyter cell 标记
- 不在脚本中直接写 `pd.read_excel(raw_path, header=0, skiprows=[1], dtype=str)` — 走 loader
- 不用裸 `df` 作最终表名
- 不用全大写无前缀变量名存 DataFrame（`RAND` → `df_rand`）
- 不在脚本顶部 `%run ../../env.py`
