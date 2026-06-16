---
name: write-script
description: 根据用户需求编写数据核查脚本。当用户要求写新脚本、新清单、新表格、新增数据核查程序、写 Python 分析脚本、或口述/示例一个输出结果需要实现时触发。
---

# write-script

根据用户需求，查询元数据，编写符合项目规范的 Python 数据核查脚本。

## 工作流程

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

| 命令 | 用途 | 示例 |
|------|------|------|
| `summary` | 元数据概览 | `python .claude/skills/write-script/scripts/query_metadata.py summary` |
| `forms` | 列出所有表单 | `python .claude/skills/write-script/scripts/query_metadata.py forms` |
| `fields <表单名>` | 查看表单字段 | `python .claude/skills/write-script/scripts/query_metadata.py fields "不良事件（AE）记录表"` |
| `search <关键字>` | 搜索字段 | `python .claude/skills/write-script/scripts/query_metadata.py search "知情同意"` |
| `codelist <名称>` | 查看编码表 | `python .claude/skills/write-script/scripts/query_metadata.py codelist CL.YN1` |
| `codelists` | 列出所有编码表 | `python .claude/skills/write-script/scripts/query_metadata.py codelists` |
| `visits` | 访视与表单关系 | `python .claude/skills/write-script/scripts/query_metadata.py visits` |
| `find-field <SAS名>` | 按 SAS 字段名查找 | `python .claude/skills/write-script/scripts/query_metadata.py find-field DSSTDAT4` |
| `field-codelist <字段名>` | 根据字段名查编码表枚举值 | `python .claude/skills/write-script/scripts/query_metadata.py field-codelist "受试者是否随机入组"` |

**查询策略：**
1. 先 `search` 需求中的关键字，定位候选字段
2. 再 `fields <表单名>` 确认字段详情（格式、编码表）
3. 涉及编码值时 `codelist <名称>` 查看枚举
4. 确认哪些字段的列名带 `_TXT` 后缀（EDC 中表示文本值，load_sheet 读取时需加 `_TXT`）

**注意：** EDC 的 sheet 名就是表单 OID（如 `DS_END`、`EC_ED`、`SV`），不是中文表单名。`formOID` 字段就是 `load_sheet` 的第一个参数。

### 3. 编写脚本

确认数据需求后，按以下规范编写。

---

## 脚本编码规范

### 文件头：路径引导 + 导入

```python
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, np, output_path, save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet
```

- `from env import …` 按需引入，只列脚本实际用到的对象
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

---

文件命名：`清单NN：标题.py` 或 `表格NN：标题.py`（NN 为两位数字序号）。

