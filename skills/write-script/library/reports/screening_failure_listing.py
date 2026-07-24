# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 筛选失败受试者清单（xlsx）：取受试者状态为「筛选失败」者，将其勾选
#       的失败原因复选框 melt 成长表（一行一原因），关联知情同意签署日期后
#       输出清单，带 No. 序号列。
# @tags 筛选失败,失败原因,清单,melt,复选框,知情同意,DMR,xlsx,试验整体情况
# @config LISTING_NAME, FORM_RAND/FORM_ICF, IMPORT_STATUS/STATUS_FAIL_VAL,
#         IMPORT_ICF_DATE, REASON_COLS, CHECKED_VAL

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config import output_listing_dir
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols

# ── 系统列（读取用 EDC 专属名，输出 rename 为通用中文标签）──

VAR_SUBJ  = system_cols("subject")
_OUT_SUBJ = "筛选号"

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、状态/复选框取值均为项目特异，须据 query_metadata.py 探索替换。

LISTING_NAME = "筛选失败受试者清单"

FORM_RAND = "DS_RAND"   # 随机/入组汇总表单（含受试者状态 + 各失败原因复选框）
FORM_ICF  = "DS_ICF"    # 知情同意书表单

IMPORT_STATUS   = "受试者状态"              # 受试者状态（业务字段）
STATUS_FAIL_VAL = "筛选失败"                # 「筛选失败」状态的取值
IMPORT_ICF_DATE = "知情同意书签署日期"

# 各筛选失败原因复选框列（列名即报表原因文案；据元数据补全）
REASON_COLS = ['不符合入选标准', '符合排除标准', '撤回知情同意',
               '失访，尝试联系≥3次均未成功', '其他筛选失败原因']

# 复选框「勾选」的值：taimei5 码值列存 "1"（字符串）；其他 EDC 见 query_metadata.py
CHECKED_VAL = "1"

# ── 列名集中管理（中间 + 输出）──

VAR_REASON = "筛选失败原因"
VAR_RESULT = "结果"
OUTPUT_COLS = [_OUT_SUBJ, IMPORT_ICF_DATE, VAR_REASON]

# ── 1 读取 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_STATUS] + REASON_COLS)
df_icf  = load_sheet(FORM_ICF,  usecols=[VAR_SUBJ, IMPORT_ICF_DATE])

# ── 4 变形：失败原因复选框 → 长表 ──

df_fail = df_rand.melt(
    id_vars=[VAR_SUBJ, IMPORT_STATUS],
    value_vars=REASON_COLS,
    var_name=VAR_REASON,
    value_name=VAR_RESULT,
)

# ── 3 筛选：状态为筛选失败 且 该原因被勾选 ──

df_fail = df_fail[
    (df_fail[IMPORT_STATUS] == STATUS_FAIL_VAL)
    & (df_fail[VAR_RESULT].astype(str).str.strip() == CHECKED_VAL)
]

# ── 6 连接 ──

df_out = df_fail.merge(df_icf, on=[VAR_SUBJ], how="left")

# ── 7 格式化 ──

df_out = df_out.rename(columns={VAR_SUBJ: _OUT_SUBJ})
df_out = df_out[OUTPUT_COLS]

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

export_to_one_excel_with_format(
    df_out,
    f"{output_listing_dir}/{LISTING_NAME}.xlsx",
    LISTING_NAME,
    f"{LISTING_NAME}（{n}例）",
    add_title=True,
)
