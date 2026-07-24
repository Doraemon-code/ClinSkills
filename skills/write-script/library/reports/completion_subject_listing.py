# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 完成试验受试者清单（xlsx）：取受试者状态为「完成试验」者，汇总随机
#       信息、知情同意签署日期、给药首/末次与治疗天数、试验完成日期与试验
#       时长（研究结束日期-知情同意日期+1）。
# @tags 完成试验,给药,治疗天数,试验时长,知情同意,清单,DMR,xlsx,试验整体情况
# @config LISTING_NAME, FORM_RAND/FORM_END/FORM_EC/FORM_ICF,
#         IMPORT_STATUS/STATUS_FINISH_VAL, IMPORT_RAND_NO/IMPORT_RAND_TIME,
#         IMPORT_EC_START/IMPORT_EC_END, IMPORT_ICF_DATE,
#         IMPORT_COMPLETE_DATE/IMPORT_EARLY_EXIT

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_listing_dir
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、状态取值均为项目特异，须据 query_metadata.py 探索替换。

LISTING_NAME = "完成试验受试者清单"

FORM_RAND = "DS_RAND"   # 随机/入组汇总表单（含受试者状态、随机号/随机时间）
FORM_END  = "DS_END"    # 研究结束/试验总结表单
FORM_EC   = "EC_ED"     # 给药/暴露表单（每受试者可多条）
FORM_ICF  = "DS_ICF"    # 知情同意书表单

IMPORT_STATUS     = "受试者状态"   # 受试者状态（业务字段）
STATUS_FINISH_VAL = "完成试验"     # 「完成试验」对应的状态取值

IMPORT_RAND_NO   = "随机号"
IMPORT_RAND_TIME = "随机时间"

IMPORT_EC_START = "开始日期"
IMPORT_EC_END   = "结束日期"

IMPORT_ICF_DATE = "知情同意书签署日期"

IMPORT_COMPLETE_DATE = "试验完成日期"    # 完成者结束日期
IMPORT_EARLY_EXIT    = "提前退出日期"    # 提前退出者结束日期（完成者一般为空）

# ── 列名集中管理（中间 + 输出）──

VAR_STUDY_END  = "研究完成日期"
VAR_FIRST_DOSE = "首次用药日期"
VAR_LAST_DOSE  = "末次用药日期"
VAR_TREAT_DAYS = "治疗天数（天）"

VAR_SCREEN_NO  = "筛选号"
VAR_STUDY_DAYS = "试验时长（天）"
OUTPUT_COLS = [VAR_SCREEN_NO, IMPORT_RAND_NO, IMPORT_ICF_DATE, IMPORT_RAND_TIME,
               VAR_FIRST_DOSE, VAR_LAST_DOSE, VAR_TREAT_DAYS,
               IMPORT_COMPLETE_DATE, VAR_STUDY_DAYS]

# ── 1 读取 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_STATUS, IMPORT_RAND_TIME, IMPORT_RAND_NO])
df_end  = load_sheet(FORM_END,  usecols=[VAR_SUBJ, IMPORT_COMPLETE_DATE, IMPORT_EARLY_EXIT]).fillna("")
df_ec   = load_sheet(FORM_EC,   usecols=[VAR_SUBJ, IMPORT_EC_START, IMPORT_EC_END]).fillna("")
df_icf  = load_sheet(FORM_ICF,  usecols=[VAR_SUBJ, IMPORT_ICF_DATE])

# ── 3 筛选：完成试验 ──

df_rand = df_rand[df_rand[IMPORT_STATUS] == STATUS_FINISH_VAL]

# ── 2 归一化 ──

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

# 研究完成日期 = 试验完成日期（优先）或提前退出日期
df_end[VAR_STUDY_END] = np.where(
    df_end[IMPORT_COMPLETE_DATE].notna(),
    df_end[IMPORT_COMPLETE_DATE],
    df_end[IMPORT_EARLY_EXIT],
)

# ── 6 连接 ──

df_out = (df_rand.merge(df_ec_out, on=[VAR_SUBJ], how="left")
                .merge(df_icf,     on=[VAR_SUBJ], how="left")
                .merge(df_end,     on=[VAR_SUBJ], how="left")
          )

# ── 5 派生（续）：试验时长 = 研究完成日期 - 知情同意日期 + 1 ──

df_out[VAR_STUDY_END]  = pd.to_datetime(df_out[VAR_STUDY_END], errors="coerce")
df_out[IMPORT_ICF_DATE] = pd.to_datetime(df_out[IMPORT_ICF_DATE], errors="coerce")
df_out[VAR_STUDY_DAYS] = (df_out[VAR_STUDY_END] - df_out[IMPORT_ICF_DATE]).dt.days + 1

df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})

# ── 7 格式化 ──

df_out[VAR_FIRST_DOSE]  = df_out[VAR_FIRST_DOSE].dt.strftime("%Y-%m-%d")
df_out[VAR_LAST_DOSE]   = df_out[VAR_LAST_DOSE].dt.strftime("%Y-%m-%d")
df_out[IMPORT_ICF_DATE] = df_out[IMPORT_ICF_DATE].dt.strftime("%Y-%m-%d")
df_out[VAR_STUDY_END]   = df_out[VAR_STUDY_END].dt.strftime("%Y-%m-%d")

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
