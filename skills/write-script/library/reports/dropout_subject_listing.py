# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 退出试验受试者清单（三线表 docx）：取受试者状态为「中止退出」者，
#       汇总随机信息、研究起止与试验时长、给药首/末次与治疗天数、末次已完成
#       的计划内访视、是否进行提前退出访视、是否提前终止治疗、提前退出原因，
#       并预留用药后安全性/疗效性评估占位列（人工填写）。
# @tags 退出试验,中止退出,访视,提前退出,治疗天数,试验时长,占位列,DMR,三线表,试验整体情况
# @config LISTING_NAME, FORM_RAND/FORM_ICF/FORM_SV/FORM_END/FORM_INTED/FORM_EC,
#         IMPORT_STATUS/STATUS_DROPOUT_VAL, IMPORT_VISIT_OID/EXCLUDE_VISIT_OIDS/EXIT_VISIT_OID,
#         IMPORT_VISIT_DATE, IMPORT_ICF_DATE, IMPORT_RAND_NO/IMPORT_RAND_TIME,
#         IMPORT_EC_START/IMPORT_EC_END, IMPORT_COMPLETE_DATE/IMPORT_EARLY_EXIT,
#         IMPORT_EXIT_REASON/IMPORT_TERMINATE, SAFETY_PLACEHOLDER/EFFICACY_PLACEHOLDER

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ       = system_cols("subject")
VAR_VISIT_NAME = system_cols("visit_name")   # 访视名称

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、状态/访视 OID 取值均为项目特异，须据 query_metadata.py 探索替换。

LISTING_NAME = "退出试验受试者清单"

FORM_RAND  = "DS_RAND"    # 随机/入组汇总表单（含受试者状态、随机号/随机时间）
FORM_ICF   = "DS_ICF"     # 知情同意书表单
FORM_SV    = "SV"         # 访视表单
FORM_END   = "DS_END"     # 研究结束/试验总结表单
FORM_INTED = "DS_INTED"   # 永久终止试验干预表单
FORM_EC    = "EC_ED"      # 给药/暴露表单（每受试者可多条）

IMPORT_STATUS      = "受试者状态"    # 受试者状态（业务字段）
STATUS_DROPOUT_VAL = "中止退出"      # 「退出试验」对应的状态取值

# 访视设计（项目特异：访视 OID 及其含义随方案而定，据元数据/方案替换）
IMPORT_VISIT_OID    = "访视OID"
EXCLUDE_VISIT_OIDS  = ["V90", "V80"]   # 计划外/提前退出访视——统计「末次计划内访视」时排除
EXIT_VISIT_OID      = "V80"            # 提前退出访视 OID
IMPORT_VISIT_DATE   = "访视日期"

IMPORT_ICF_DATE = "知情同意书签署日期"

IMPORT_RAND_NO   = "随机号"
IMPORT_RAND_TIME = "随机时间"

IMPORT_EC_START = "开始日期"
IMPORT_EC_END   = "结束日期"

IMPORT_COMPLETE_DATE = "试验完成日期"    # 完成者结束日期
IMPORT_EARLY_EXIT    = "提前退出日期"    # 提前退出者结束日期

IMPORT_EXIT_REASON = "受试者退出试验原因_TXT"        # 退出原因（解码列）
IMPORT_TERMINATE   = "受试者是否永久终止试验干预_TXT"  # 是否永久终止（解码列）

# 占位列（人工填写，非数据派生）
SAFETY_PLACEHOLDER   = "有/无"
EFFICACY_PLACEHOLDER = "有/无"

# ── 列名集中管理（中间 + 输出）──

VAR_STUDY_END = "研究结束日期"
VAR_FIRST_DOSE = "首次用药日期"
VAR_LAST_DOSE  = "末次用药日期"
VAR_TREAT_DAYS = "治疗天数（天）"

VAR_SCREEN_NO       = "筛选号"
VAR_RAND_NO         = "随机号"
VAR_RAND_TIME       = "随机时间"
VAR_STUDY_START     = "研究开始日期"
VAR_STUDY_DAYS      = "试验时长（天）"
VAR_LAST_VISIT      = "末次已完成的计划内访视"
VAR_EXIT_VISIT      = "是否进行提前退出访视"
VAR_TERMINATE_OUT   = "是否提前终止治疗"
VAR_EXIT_REASON_OUT = "提前退出原因"
VAR_SAFETY          = "用药后安全性指标评估情况"
VAR_EFFICACY        = "用药后疗效性指标评估情况"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_STUDY_START, VAR_RAND_TIME,
               VAR_FIRST_DOSE, VAR_LAST_DOSE, VAR_TREAT_DAYS,
               VAR_TERMINATE_OUT, VAR_STUDY_END, VAR_STUDY_DAYS,
               VAR_LAST_VISIT, VAR_EXIT_VISIT, VAR_SAFETY, VAR_EFFICACY,
               VAR_EXIT_REASON_OUT]

# ── 1 读取 ──

df_rand    = load_sheet(FORM_RAND,  usecols=[VAR_SUBJ, IMPORT_STATUS, IMPORT_RAND_TIME, IMPORT_RAND_NO])
df_icf     = load_sheet(FORM_ICF,   usecols=[VAR_SUBJ, IMPORT_ICF_DATE])
df_sv      = load_sheet(FORM_SV,    usecols=[VAR_SUBJ, IMPORT_VISIT_OID, VAR_VISIT_NAME, IMPORT_VISIT_DATE])
df_sv_exit = load_sheet(FORM_SV,    usecols=[VAR_SUBJ, IMPORT_VISIT_OID, IMPORT_VISIT_DATE])
df_end     = load_sheet(FORM_END,   usecols=[VAR_SUBJ, IMPORT_EXIT_REASON, IMPORT_COMPLETE_DATE, IMPORT_EARLY_EXIT])
df_inted   = load_sheet(FORM_INTED, usecols=[VAR_SUBJ, IMPORT_TERMINATE])
df_ec      = load_sheet(FORM_EC,    usecols=[VAR_SUBJ, IMPORT_EC_START, IMPORT_EC_END]).fillna("")

# ── 3 筛选 ──

df_out = df_rand[df_rand[IMPORT_STATUS] == STATUS_DROPOUT_VAL].copy()

df_sv = df_sv[~df_sv[IMPORT_VISIT_OID].isin(EXCLUDE_VISIT_OIDS)]

df_sv_exit = df_sv_exit[df_sv_exit[IMPORT_VISIT_OID] == EXIT_VISIT_OID]
df_sv_exit[VAR_EXIT_VISIT] = "是"
df_sv_exit = df_sv_exit[[VAR_SUBJ, VAR_EXIT_VISIT]].drop_duplicates(subset=[VAR_SUBJ])

# ── 2 归一化 ──

df_icf = df_icf.rename(columns={IMPORT_ICF_DATE: VAR_STUDY_START})

df_sv[IMPORT_VISIT_DATE] = pd.to_datetime(df_sv[IMPORT_VISIT_DATE], errors="coerce")
idx = df_sv.groupby(VAR_SUBJ)[IMPORT_VISIT_DATE].idxmax()
df_sv = df_sv.loc[idx, [VAR_SUBJ, VAR_VISIT_NAME, IMPORT_VISIT_DATE]]
df_sv = df_sv.rename(columns={VAR_VISIT_NAME: VAR_LAST_VISIT})

df_end[VAR_STUDY_END] = np.where(
    df_end[IMPORT_COMPLETE_DATE].notna(),
    df_end[IMPORT_COMPLETE_DATE],
    df_end[IMPORT_EARLY_EXIT],
)

df_ec[IMPORT_EC_START] = pd.to_datetime(df_ec[IMPORT_EC_START], errors="coerce")
df_ec[IMPORT_EC_END]   = pd.to_datetime(df_ec[IMPORT_EC_END], errors="coerce")

# ── 5 派生：首末次用药 + 治疗天数 ──

df_ec1 = (df_ec.groupby(VAR_SUBJ, dropna=False)[IMPORT_EC_START]
               .agg(["min"]).rename(columns={"min": VAR_FIRST_DOSE}))
df_ec2 = (df_ec.groupby(VAR_SUBJ, dropna=False)[IMPORT_EC_END]
               .agg(["max"]).rename(columns={"max": VAR_LAST_DOSE}))
df_ec_out = df_ec1.merge(df_ec2, on=[VAR_SUBJ], how="inner")

df_ec_out[VAR_TREAT_DAYS] = (df_ec_out[VAR_LAST_DOSE] - df_ec_out[VAR_FIRST_DOSE]).dt.days + 1
df_ec_out[VAR_TREAT_DAYS] = df_ec_out[VAR_TREAT_DAYS].where(df_ec_out[VAR_TREAT_DAYS] > 0, np.nan)
df_ec_out = df_ec_out.reset_index()

# ── 6 连接 ──

df_out = (df_out.merge(df_ec_out, on=[VAR_SUBJ], how="left")
               .merge(df_sv,      on=[VAR_SUBJ], how="left")
               .merge(df_end,     on=[VAR_SUBJ], how="left")
               .merge(df_inted,   on=[VAR_SUBJ], how="left")
               .merge(df_icf,     on=[VAR_SUBJ], how="left")
               .merge(df_sv_exit, on=[VAR_SUBJ], how="left")
        )

df_out = df_out.rename(columns={
    IMPORT_EXIT_REASON: VAR_EXIT_REASON_OUT,
    VAR_SUBJ:           VAR_SCREEN_NO,
    IMPORT_TERMINATE:   VAR_TERMINATE_OUT,
    IMPORT_RAND_NO:     VAR_RAND_NO,
    IMPORT_RAND_TIME:   VAR_RAND_TIME,
})

# ── 5 派生（续）：试验时长 + 占位列 ──

df_out[VAR_STUDY_END]   = pd.to_datetime(df_out[VAR_STUDY_END], errors="coerce")
df_out[VAR_STUDY_START] = pd.to_datetime(df_out[VAR_STUDY_START], errors="coerce")
df_out[VAR_STUDY_DAYS]  = (df_out[VAR_STUDY_END] - df_out[VAR_STUDY_START]).dt.days + 1

df_out[VAR_SAFETY]   = SAFETY_PLACEHOLDER
df_out[VAR_EFFICACY] = EFFICACY_PLACEHOLDER

# ── 7 格式化 ──

df_out[VAR_STUDY_END]   = df_out[VAR_STUDY_END].dt.strftime("%Y-%m-%d")
df_out[VAR_STUDY_START] = df_out[VAR_STUDY_START].dt.strftime("%Y-%m-%d")
df_out[VAR_FIRST_DOSE]  = df_out[VAR_FIRST_DOSE].dt.strftime("%Y-%m-%d")
df_out[VAR_LAST_DOSE]   = df_out[VAR_LAST_DOSE].dt.strftime("%Y-%m-%d")

df_out = df_out[OUTPUT_COLS]
df_out = df_out.fillna("")

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──
# 注：首条脚注含项目特异描述（具体访视号/时间窗），据方案调整。
notes = [
    "提前退出：受试者未进行访视6（V6，D71±3）；",
    "治疗天数（天）=末次用药日期-首次用药日期+1；",
    "研究开始日期：最早一次知情同意书签署日期；",
    "研究结束日期：最晚一次访视完成日期；",
    "试验时长（天）=研究结束日期-研究开始日期+1。",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{LISTING_NAME}.docx",
    LISTING_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
