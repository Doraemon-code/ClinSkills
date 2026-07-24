# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 因其他原因而提前终止治疗（报表）：取「永久终止试验干预」原因为
#       「其他」者，将原因与「其他」自由文本明细拼为终止原因，关联给药记录
#       算首/末次用药与治疗天数、关联完成情况，输出带 No. 序号的三线表。
#       （合并自项目中两版同名表——「表5」与「表10」——的核心逻辑。）
# @tags 提前终止,其他原因,自由文本,治疗天数,给药,DMR,三线表,试验整体情况
# @config REPORT_NAME, FORM_INTED/FORM_EC/FORM_END/FORM_RAND,
#         TERM_REASON_COL/TERM_REASON_OTHER_VAL/IMPORT_OTHER_DETAIL,
#         IMPORT_EC_START/IMPORT_EC_END, IMPORT_COMPLETED, IMPORT_RAND_NO

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

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、原因编码取值均为项目特异，须据 query_metadata.py 探索替换。

REPORT_NAME = "因其他原因而发生的提前终止治疗"

FORM_INTED = "DS_INTED"   # 永久终止试验干预表单
FORM_EC    = "EC_ED"      # 给药/暴露表单（每受试者可多条）
FORM_END   = "DS_END"     # 研究结束/试验总结表单
FORM_RAND  = "DS_RAND"    # 随机表单

# DS_INTED：永久终止原因（解码列）+「其他」取值 + 其他自由文本明细
TERM_REASON_COL       = "永久终止试验干预原因_TXT"
TERM_REASON_OTHER_VAL = "其他"                         # 「其他」的解码值
IMPORT_OTHER_DETAIL   = "其他永久终止试验干预的原因"    # 「其他」自由文本补充字段

# 给药字段
IMPORT_EC_START = "开始日期"
IMPORT_EC_END   = "结束日期"

# 完成情况（解码列；后缀随 EDC）
IMPORT_COMPLETED = "受试者是否完成试验_TXT"

# 随机字段
IMPORT_RAND_NO = "随机号"

# ── 列名集中管理（中间 + 输出）──

VAR_FIRST_DOSE = "首次用药日期"
VAR_LAST_DOSE  = "末次用药日期"
VAR_TREAT_DAYS = "治疗天数（天）"

VAR_SCREEN_NO       = "筛选号"
VAR_RAND_NO         = "随机号"
VAR_TERM_REASON_OUT = "提前终止治疗的原因"
VAR_COMPLETED       = "是否完成试验"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_FIRST_DOSE, VAR_LAST_DOSE,
               VAR_TREAT_DAYS, VAR_TERM_REASON_OUT, VAR_COMPLETED]

# ── 1 读取 ──

df_inted = load_sheet(FORM_INTED, usecols=[VAR_SUBJ, TERM_REASON_COL, IMPORT_OTHER_DETAIL]).fillna("")
df_ec    = load_sheet(FORM_EC,    usecols=[VAR_SUBJ, IMPORT_EC_START, IMPORT_EC_END]).fillna("")
df_end   = load_sheet(FORM_END,   usecols=[VAR_SUBJ, IMPORT_COMPLETED]).fillna("")
df_rand  = load_sheet(FORM_RAND,  usecols=[VAR_SUBJ, IMPORT_RAND_NO])

# ── 3 筛选：DS_INTED 原因为「其他」──

df_inted = df_inted[df_inted[TERM_REASON_COL] == TERM_REASON_OTHER_VAL]

# ── 5 派生：终止原因 = 原因 +「其他」明细 ──

df_inted[VAR_TERM_REASON_OUT] = df_inted.apply(
    lambda r: f"{r[TERM_REASON_COL]}：{r[IMPORT_OTHER_DETAIL]}"
              if r[IMPORT_OTHER_DETAIL] else r[TERM_REASON_COL],
    axis=1,
)

# ── 2 归一化 ──

df_ec[IMPORT_EC_START] = pd.to_datetime(df_ec[IMPORT_EC_START], errors="coerce")
df_ec[IMPORT_EC_END]   = pd.to_datetime(df_ec[IMPORT_EC_END], errors="coerce")

# 给药表每受试者可多条，聚合为最早开始 / 最晚结束
df_ec = (df_ec.groupby(VAR_SUBJ, dropna=False)
              .agg({IMPORT_EC_START: "min", IMPORT_EC_END: "max"})
              .reset_index()
        )

df_ec[VAR_TREAT_DAYS] = (df_ec[IMPORT_EC_END] - df_ec[IMPORT_EC_START]).dt.days + 1
df_ec[VAR_TREAT_DAYS] = df_ec[VAR_TREAT_DAYS].astype("Int64").astype("string").fillna("")
df_ec[VAR_FIRST_DOSE] = df_ec[IMPORT_EC_START].dt.strftime("%Y-%m-%d")
df_ec[VAR_LAST_DOSE]  = df_ec[IMPORT_EC_END].dt.strftime("%Y-%m-%d")

# ── 6 连接 ──

df_out = (df_inted.merge(df_rand, on=[VAR_SUBJ], how="left")
                  .merge(df_ec,   on=[VAR_SUBJ], how="left")
                  .merge(df_end,  on=[VAR_SUBJ], how="left")
          )

df_out = df_out.rename(columns={
    VAR_SUBJ:         VAR_SCREEN_NO,
    IMPORT_COMPLETED: VAR_COMPLETED,
})

# ── 7 格式化 ──

df_out = df_out[OUTPUT_COLS]
df_out = df_out.fillna("<NA>")

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

notes = [
    "治疗天数（天）= 试验药物末次用药日期 - 试验药物首次用药日期 + 1；",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
