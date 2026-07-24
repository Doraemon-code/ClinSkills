# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 因与试验用药品相关的不良事件而提前终止治疗（报表）：取「永久终止
#       试验干预」原因为 AE 相关者，关联给药记录算首/末次用药与治疗天数、
#       关联 AE（初始/后续措施命中「停药」类）取事件名称与关系、关联完成
#       情况，输出带 No. 序号的三线表。
# @tags 提前终止,永久停药,不良事件,治疗天数,给药,AE,DMR,三线表,试验整体情况
# @config REPORT_NAME, FORM_INTED/FORM_EC/FORM_END/FORM_AE/FORM_RAND,
#         TERM_REASON_COL/TERM_REASON_AE_VAL, IMPORT_EC_START/IMPORT_EC_END,
#         IMPORT_COMPLETED, IMPORT_AE_NAME/IMPORT_AE_MEASURE_COLS/IMPORT_AE_RELATION,
#         STOP_ACTIONS, IMPORT_RAND_NO

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
# 表单 OID、字段名、原因编码取值、措施取值均为项目特异，须据 query_metadata.py 探索替换。

REPORT_NAME = "因与试验用药品相关的不良事件而发生的提前终止治疗"

FORM_INTED = "DS_INTED"   # 永久终止试验干预表单
FORM_EC    = "EC_ED"      # 给药/暴露表单（每受试者可多条）
FORM_END   = "DS_END"     # 研究结束/试验总结表单
FORM_AE    = "AE"         # 不良事件表单
FORM_RAND  = "DS_RAND"    # 随机表单

# DS_INTED：永久终止原因（解码列）+ 命中「AE 相关」的取值
TERM_REASON_COL    = "永久终止试验干预原因_TXT"
TERM_REASON_AE_VAL = "试验期间受试者发生不良事件，研究者认为受试者需永久停止服用试验用药品"  # 据本项目原因编码表实际取值替换

# 给药字段
IMPORT_EC_START = "开始日期"
IMPORT_EC_END   = "结束日期"

# 完成情况（解码列；后缀随 EDC）
IMPORT_COMPLETED = "受试者是否完成试验_TXT"

# AE 字段
IMPORT_AE_NAME     = "不良事件名称"
IMPORT_AE_RELATION = "与试验药物的关系_TXT"                                  # 解码列
IMPORT_AE_MEASURE_COLS = ["对试验药物采取的初始措施_TXT", "对试验药物采取的措施-1_TXT"]  # 初始/后续措施解码列
STOP_ACTIONS = ["停止用药", "已结束用药"]                                    # 判定「停药」的措施取值

# 随机字段
IMPORT_RAND_NO = "随机号"

# ── 列名集中管理（中间 + 输出）──

VAR_FIRST_DOSE = "首次用药日期"
VAR_LAST_DOSE  = "末次用药日期"
VAR_TREAT_DAYS = "治疗天数（天）"

VAR_SCREEN_NO       = "筛选号"
VAR_RAND_NO         = "随机号"
VAR_RELATION_OUT    = "与试验用药品的关系"
VAR_TERM_REASON_OUT = "提前终止治疗的原因"
VAR_COMPLETED       = "是否完成试验"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_FIRST_DOSE, VAR_LAST_DOSE,
               VAR_TREAT_DAYS, IMPORT_AE_NAME, VAR_RELATION_OUT,
               VAR_TERM_REASON_OUT, VAR_COMPLETED]

# ── 1 读取 ──

df_inted = load_sheet(FORM_INTED, usecols=[VAR_SUBJ, TERM_REASON_COL])
df_ec    = load_sheet(FORM_EC,    usecols=[VAR_SUBJ, IMPORT_EC_START, IMPORT_EC_END]).fillna("")
df_end   = load_sheet(FORM_END,   usecols=[VAR_SUBJ, IMPORT_COMPLETED]).fillna("")
df_ae    = load_sheet(FORM_AE,    usecols=[VAR_SUBJ, IMPORT_AE_NAME, IMPORT_AE_RELATION] + IMPORT_AE_MEASURE_COLS)
df_rand  = load_sheet(FORM_RAND,  usecols=[VAR_SUBJ, IMPORT_RAND_NO])

# ── 3 筛选：DS_INTED 原因为 AE 相关 ──

df_inted = df_inted[df_inted[TERM_REASON_COL] == TERM_REASON_AE_VAL]

# ── 2 归一化 ──

df_ec[IMPORT_EC_START] = pd.to_datetime(df_ec[IMPORT_EC_START], errors="coerce")
df_ec[IMPORT_EC_END]   = pd.to_datetime(df_ec[IMPORT_EC_END], errors="coerce")

# 给药表每受试者可多条，聚合为最早开始 / 最晚结束
df_ec = (df_ec.groupby(VAR_SUBJ, dropna=False)
              .agg({IMPORT_EC_START: "min", IMPORT_EC_END: "max"})
              .reset_index()
        )

# AE：初始/后续措施任一命中「停药」类
df_ae = df_ae[
    df_ae[IMPORT_AE_MEASURE_COLS]
    .apply(lambda col: col.isin(STOP_ACTIONS))
    .any(axis=1)
]

# ── 5 派生：治疗天数 + 首末次用药 ──

df_ec[VAR_TREAT_DAYS] = (df_ec[IMPORT_EC_END] - df_ec[IMPORT_EC_START]).dt.days + 1
df_ec[VAR_TREAT_DAYS] = df_ec[VAR_TREAT_DAYS].astype("Int64").astype("string").fillna("")
df_ec[VAR_FIRST_DOSE] = df_ec[IMPORT_EC_START].dt.strftime("%Y-%m-%d")
df_ec[VAR_LAST_DOSE]  = df_ec[IMPORT_EC_END].dt.strftime("%Y-%m-%d")

# ── 6 连接 ──

df_out = (df_inted.merge(df_rand, on=[VAR_SUBJ], how="left")
                  .merge(df_ec,    on=[VAR_SUBJ], how="left")
                  .merge(df_end,   on=[VAR_SUBJ], how="left")
                  .merge(df_ae,    on=[VAR_SUBJ], how="left")
          )

df_out = df_out.rename(columns={
    VAR_SUBJ:           VAR_SCREEN_NO,
    IMPORT_AE_RELATION: VAR_RELATION_OUT,
    TERM_REASON_COL:    VAR_TERM_REASON_OUT,
    IMPORT_COMPLETED:   VAR_COMPLETED,
})

# ── 7 格式化 ──

df_out = df_out[OUTPUT_COLS]

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
