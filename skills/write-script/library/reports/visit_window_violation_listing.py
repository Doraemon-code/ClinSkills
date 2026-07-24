# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 访视超窗清单（xlsx）：从 SV 访视表单读取访视日期，与时间窗
#       Excel 按类别+访视名称匹配，计算上下限并判定超窗，输出 xlsx 清单。
# @tags 超窗,访视,时间窗,SV,xlsx,清单
# @config LISTING_NAME, FORM_SV/FORM_RAND/FORM_END, TIMEWIN_PATH,
#         TIMEWIN_SHEET, IMPORT_* 列名

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import timewin_path, output_table_dir
from utils.output_format import export_to_excel_with_format
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──

LISTING_NAME = "访视超窗清单"

FORM_SV   = "SV"
FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"

TIMEWIN_SHEET   = "时间窗"
TIMEWIN_CAT_COL  = "类别"
TIMEWIN_VISIT_COL = "访视名称"
TIMEWIN_LOWER_COL = "时间窗下限"
TIMEWIN_UPPER_COL = "时间窗上限"

# 类别标记（用于匹配时间窗）
WINDOW_CATEGORY = "其他指标超窗"

# 随机日期列名
IMPORT_RAND_TIME = "随机时间"
IMPORT_RAND_NO   = "随机号"

# 访视日期列名
IMPORT_VISIT_DATE = "访视日期"

# 完成状态
IMPORT_COMPLETED = "受试者是否完成试验_TXT"

# 排除的受试者状态值
EXCLUDE_STATUS = "筛选失败"

# 筛选期访视名称（这些访视的时间窗计算方向需反转）
SCREENING_VISITS = ["筛选期（V1，D-15~-13）"]

# ── 列名集中管理 ──

IMPORT_SV   = [VAR_SUBJ, "受试者状态", "访视名称", "页面名称", IMPORT_VISIT_DATE]
IMPORT_RAND = [VAR_SUBJ, IMPORT_RAND_TIME]
IMPORT_END  = [VAR_SUBJ, "页面名称", IMPORT_COMPLETED]

VAR_STATUS    = "受试者状态"
VAR_VISIT     = "访视名称"
VAR_FORM      = "页面名称"
VAR_EVAL_DATE = "评估日期"
VAR_RAND_TIME = IMPORT_RAND_TIME
VAR_TW_UPPER  = TIMEWIN_UPPER_COL
VAR_TW_LOWER  = TIMEWIN_LOWER_COL
VAR_UPPER     = "上限"
VAR_LOWER     = "下限"
VAR_OVERDUE   = "超窗"
VAR_OVER_DAYS = "超窗时间（天）"
VAR_PLAN_TW   = "计划时间窗"
VAR_CAT       = "类别"

VAR_SCREEN_NO  = "筛选号"
VAR_RAND_NO    = "随机号"
VAR_FIRST_DOSE = "首次用药日期"
VAR_COMPLETED  = "是否完成试验"

OUTPUT_COLS = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_VISIT, "表单名称",
    "发生日期", VAR_FIRST_DOSE, VAR_PLAN_TW,
    VAR_OVER_DAYS, VAR_COMPLETED,
]

# ── 1 读取 ──

df_tw = pd.read_excel(
    timewin_path, sheet_name=TIMEWIN_SHEET,
    usecols=[TIMEWIN_CAT_COL, TIMEWIN_VISIT_COL, TIMEWIN_LOWER_COL, TIMEWIN_UPPER_COL],
)
df_tw[VAR_TW_LOWER] = df_tw[VAR_TW_LOWER].astype("Int32")
df_tw[VAR_TW_UPPER] = df_tw[VAR_TW_UPPER].astype("Int32")

df_sv = load_sheet(FORM_SV, IMPORT_SV + [IMPORT_VISIT_DATE])
df_sv = df_sv.rename(columns={IMPORT_VISIT_DATE: VAR_EVAL_DATE})

# ── 2 归一化 ──

df = df_sv.sort_values(by=[VAR_SUBJ, VAR_VISIT, VAR_FORM, VAR_EVAL_DATE])
df = df.drop_duplicates()

# ── 3 筛选 ──

df = df[df[VAR_STATUS] != EXCLUDE_STATUS]
df[VAR_CAT] = WINDOW_CATEGORY

# ── 6 连接（时间窗 + 随机时间）──

df_rand = load_sheet(FORM_RAND, usecols=IMPORT_RAND)

df = (
    df.merge(df_tw, on=[VAR_CAT, VAR_VISIT], how="left")
      .merge(df_rand, on=VAR_SUBJ, how="left")
)

# ── 5 派生（计算上下限 + 判断超窗）──

df[VAR_RAND_TIME] = pd.to_datetime(df[VAR_RAND_TIME], errors="coerce")
df[VAR_EVAL_DATE] = pd.to_datetime(df[VAR_EVAL_DATE], errors="coerce")
df[VAR_TW_UPPER]  = pd.to_numeric(df[VAR_TW_UPPER], errors="coerce")
df[VAR_TW_LOWER]  = pd.to_numeric(df[VAR_TW_LOWER], errors="coerce")

# 筛选期访视时间窗方向反转（负值 → 从随机日期往前算）
is_screening = df[VAR_VISIT].isin(SCREENING_VISITS)

df.loc[~is_screening, VAR_UPPER] = (
    df.loc[~is_screening, VAR_RAND_TIME]
    + pd.to_timedelta(df.loc[~is_screening, VAR_TW_UPPER], unit="D")
)
df.loc[~is_screening, VAR_LOWER] = (
    df.loc[~is_screening, VAR_RAND_TIME]
    + pd.to_timedelta(df.loc[~is_screening, VAR_TW_LOWER], unit="D")
)

df.loc[is_screening, VAR_UPPER] = (
    df.loc[is_screening, VAR_RAND_TIME]
    - pd.to_timedelta(df.loc[is_screening, VAR_TW_UPPER], unit="D")
)
df.loc[is_screening, VAR_LOWER] = (
    df.loc[is_screening, VAR_RAND_TIME]
    - pd.to_timedelta(df.loc[is_screening, VAR_TW_LOWER], unit="D")
)

df[VAR_OVERDUE] = np.where(
    (df[VAR_EVAL_DATE] > df[VAR_UPPER]) | (df[VAR_EVAL_DATE] < df[VAR_LOWER]),
    "超窗", "未超窗",
)
df = df[df[VAR_OVERDUE] == "超窗"]

# ── 5 派生（超窗天数 + 计划时间窗）──

df[VAR_OVER_DAYS] = np.where(
    df[VAR_EVAL_DATE] > df[VAR_UPPER],
    (df[VAR_EVAL_DATE] - df[VAR_UPPER]).dt.days,
    (df[VAR_EVAL_DATE] - df[VAR_LOWER]).dt.days,
)
df[VAR_PLAN_TW] = df[VAR_LOWER].astype(str) + "-" + df[VAR_UPPER].astype(str)

# ── 6 连接（完成状态 + 首次用药 + 随机号）──

df_end = load_sheet(FORM_END, IMPORT_END).drop(columns=["页面名称"])

df_ec = load_sheet("EC_ED", [VAR_SUBJ, "开始日期"])
df_ec["开始日期"] = pd.to_datetime(df_ec["开始日期"], errors="coerce")
df_ec = df_ec.sort_values(by=[VAR_SUBJ, "开始日期"]).dropna(subset=["开始日期"])
df_fd = df_ec.groupby(VAR_SUBJ)["开始日期"].first().reset_index()

df_rand2 = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, "受试者状态", IMPORT_RAND_NO])
df_rand2 = df_rand2[df_rand2["受试者状态"] != EXCLUDE_STATUS].drop(columns=["受试者状态"])

df = (
    df.merge(df_end,   on=VAR_SUBJ, how="left")
      .merge(df_fd,    on=VAR_SUBJ, how="left")
      .merge(df_rand2, on=VAR_SUBJ, how="left")
)

# 去掉 _TXT 后缀
df.columns = [col.replace("_TXT", "") for col in df.columns]

# ── 7 格式化 ──

df = df.rename(columns={
    VAR_SUBJ:      VAR_SCREEN_NO,
    VAR_FORM:      "表单名称",
    VAR_EVAL_DATE: "发生日期",
    "开始日期":    VAR_FIRST_DOSE,
    "受试者是否完成试验": VAR_COMPLETED,
})

df = df[OUTPUT_COLS]

# ── 8 输出 ──

lc = len(df)
ls = len(df.drop_duplicates(subset=[VAR_SCREEN_NO]))

export_to_excel_with_format(
    df,
    f"{output_table_dir}/{LISTING_NAME}.xlsx",
    "访视超窗清单",
    f"访视超窗清单（{lc}例次{ls}例）",
)
