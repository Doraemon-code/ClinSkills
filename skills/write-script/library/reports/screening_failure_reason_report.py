# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 筛选失败原因分类：从随机/入组汇总表取筛选失败受试者，对若干「失败
#       原因」复选框列逐列计数（按例次），末尾附合计行。一名受试者可勾选
#       多项，故为例次统计而非人数。
# @tags 筛选失败,失败原因,复选框,例次,合计行,DMR,三线表,试验整体情况
# @config REPORT_NAME, FORM_RAND, IMPORT_RAND_STATUS, RAND_NO, REASON_COLS, CHECKED_VAL

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")   # 本表未直接输出，但读取时随表带出

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、复选框勾选值均为项目特异，须据 query_metadata.py 探索替换。

REPORT_NAME = "筛选失败原因分类"

FORM_RAND = "DS_RAND"   # 随机/入组汇总表单（含是否随机入组 + 各失败原因复选框）

IMPORT_RAND_STATUS = "受试者是否随机入组_TXT"   # 是否随机入组（解码列；后缀随 EDC）
RAND_NO = "否"                                  # 「否」的解码值（跨 EDC 语言）

# 各筛选失败原因复选框列（列名即报表原因文案；据元数据补全）
REASON_COLS = ['不符合入选标准', '符合排除标准', '撤回知情同意',
               '失访，尝试联系≥3次均未成功', '其他']

# 复选框「勾选」的值：taimei5 码值列存 "1"（字符串）；其他 EDC 见 query_metadata.py
CHECKED_VAL = "1"

# ── 列名集中管理（输出）──

VAR_REASON = "筛选失败原因"
VAR_COUNT  = "例次"
OUTPUT_COLS = [VAR_REASON, VAR_COUNT]

# ── 1 读取 ──

df_rand = load_sheet(FORM_RAND, usecols=[IMPORT_RAND_STATUS] + REASON_COLS)

# ── 3 筛选：只取筛选失败（未随机入组）──

df_fail = df_rand[df_rand[IMPORT_RAND_STATUS] == RAND_NO]

# ── 4 变形：逐原因计数（例次）──

df_out = pd.DataFrame({
    VAR_REASON: REASON_COLS,
    VAR_COUNT:  [(df_fail[col].astype(str).str.strip() == CHECKED_VAL).sum() for col in REASON_COLS],
})

# 合计行
df_out.loc[len(df_out)] = ["合计", df_out[VAR_COUNT].sum()]

# ── 7 格式化 ──

df_out[VAR_COUNT] = df_out[VAR_COUNT].astype(int)

# ── 8 输出 ──

notes = [
    "根据筛选失败原因，拆分信息按例次计算。",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
