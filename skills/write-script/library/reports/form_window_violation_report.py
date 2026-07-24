# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 表单级超窗清单三线表：从指定表单列表读取评估日期，与时间窗 Excel
#       按类别+访视名称匹配，计算上下限并判定超窗，去重后按访视分组输出
#       docx 三线表。
# @tags 超窗,时间窗,访视,按访视分组,DMR,三线表
# @config REPORT_NAME, SOURCE_SHEETS, TIMEWIN_PATH, FORM_RAND/FORM_END

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import timewin_path, output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID、字段名、时间窗配置均为项目特异。

REPORT_NAME = "表单级超窗清单"

FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"

# 时间窗 Excel 配置
TIMEWIN_SHEET   = "时间窗"
TIMEWIN_CAT_COL  = "类别"
TIMEWIN_VISIT_COL = "访视名称"
TIMEWIN_LOWER_COL = "时间窗下限"
TIMEWIN_UPPER_COL = "时间窗上限"

# 来源表单定义：[(sheet_oid, 日期列名), ...]
# 所有表单必须有统一的系统列（受试者、受试者状态、访视名称、页面名称）
SOURCE_SHEETS = [
    ("QS_TCM",  "评估日期"),
    ("QS_SPI",  "评估日期"),
    ("QS_DAI",  "评估日期"),
    ("QS_SFI",  "评估日期"),
    ("RS",      "评估日期"),
]

# SV 表单（用于去重，不需要则设为 None）
DEDUP_SV_SHEET = "SV"
DEDUP_SV_DATE  = "访视日期"

# 类别标记（用于匹配时间窗）
WINDOW_CATEGORY = "疗效评价指标超窗"

# 排除的受试者状态值
EXCLUDE_STATUS = "筛选失败"

# 筛选期访视名称（时间窗方向反转，不需要反转则留空）
SCREENING_VISITS = []

# ── 列名集中管理 ──

IMPORT_SYSTEM = [VAR_SUBJ, "受试者状态", "访视名称", "页面名称"]
IMPORT_RAND   = [VAR_SUBJ, "随机时间"]
IMPORT_RAND2  = [VAR_SUBJ, "受试者状态", "随机号"]
IMPORT_EC     = [VAR_SUBJ, "开始日期"]
IMPORT_END    = [VAR_SUBJ, "受试者是否完成试验_TXT"]

VAR_STATUS    = "受试者状态"
VAR_VISIT     = "访视名称"
VAR_FORM      = "页面名称"
VAR_EVAL_DATE = "评估日期"
VAR_RAND_TIME = "随机时间"
VAR_TW_UPPER  = TIMEWIN_UPPER_COL
VAR_TW_LOWER  = TIMEWIN_LOWER_COL
VAR_UPPER     = "上限"
VAR_LOWER     = "下限"
VAR_OVERDUE   = "超窗"
VAR_OVER_DAYS = "超窗时间（天）"
VAR_PLAN_TW   = "计划时间窗"
VAR_CAT       = "类别"
VAR_DOSE_DATE = "开始日期"
VAR_COMPLETED = "受试者是否完成试验_TXT"

VAR_SCREEN_NO  = "筛选号"
VAR_RAND_NO    = "随机号"
VAR_FORM_NAME  = "表单名称"
VAR_DATE       = "评估日期"
VAR_RAND_DATE  = "随机日期"
VAR_FIRST_DOSE = "首次用药日期"
VAR_COMPLETE   = "是否完成试验"

OUTPUT_COLS = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_VISIT, VAR_FORM_NAME,
    VAR_DATE, VAR_RAND_DATE, VAR_FIRST_DOSE, VAR_PLAN_TW,
    VAR_OVER_DAYS, VAR_COMPLETE,
]

NOTES = []

# ── 1 读取 ──

df_tw = pd.read_excel(
    timewin_path, sheet_name=TIMEWIN_SHEET,
    usecols=[TIMEWIN_CAT_COL, TIMEWIN_VISIT_COL, TIMEWIN_LOWER_COL, TIMEWIN_UPPER_COL],
)
df_tw[TIMEWIN_VISIT_COL] = df_tw[TIMEWIN_VISIT_COL].str.strip()
df_tw[VAR_TW_LOWER] = pd.to_numeric(
    df_tw[VAR_TW_LOWER].astype(str).str.replace("`", ""), errors="coerce"
)
df_tw[VAR_TW_UPPER] = pd.to_numeric(
    df_tw[VAR_TW_UPPER].astype(str).str.replace("`", ""), errors="coerce"
)
df_tw = df_tw.dropna(subset=[VAR_TW_LOWER, VAR_TW_UPPER])
df_tw[VAR_TW_LOWER] = df_tw[VAR_TW_LOWER].astype("Int32")
df_tw[VAR_TW_UPPER] = df_tw[VAR_TW_UPPER].astype("Int32")

df_rand = load_sheet(FORM_RAND, usecols=IMPORT_RAND)

dfs_source = []
for sheet_name, date_col in SOURCE_SHEETS:
    df_s = load_sheet(sheet_name, IMPORT_SYSTEM + [date_col])
    if date_col != VAR_EVAL_DATE:
        df_s = df_s.rename(columns={date_col: VAR_EVAL_DATE})
    dfs_source.append(df_s)

# SV 去重数据
df_dedup = None
if DEDUP_SV_SHEET:
    df_dedup = load_sheet(DEDUP_SV_SHEET, IMPORT_SYSTEM + [DEDUP_SV_DATE])

# ── 2 归一化 ──

df_main = (
    pd.concat(dfs_source)
      .sort_values(by=[VAR_SUBJ, VAR_VISIT, VAR_FORM, VAR_EVAL_DATE])
      .drop_duplicates()
)

# ── 3 筛选 ──

df_main = df_main[df_main[VAR_STATUS] != EXCLUDE_STATUS]
df_main[VAR_CAT] = WINDOW_CATEGORY

# ── 6 连接（时间窗 + 随机时间）──

df = (
    df_main.merge(df_tw, on=[VAR_CAT, VAR_VISIT], how="left")
           .merge(df_rand, on=VAR_SUBJ, how="left")
)

# ── 5 派生（计算上下限 + 判断超窗）──

df[VAR_RAND_TIME] = pd.to_datetime(df[VAR_RAND_TIME], errors="coerce")
df[VAR_EVAL_DATE] = pd.to_datetime(df[VAR_EVAL_DATE], errors="coerce")
df[VAR_TW_UPPER]  = pd.to_numeric(df[VAR_TW_UPPER], errors="coerce")
df[VAR_TW_LOWER]  = pd.to_numeric(df[VAR_TW_LOWER], errors="coerce")

df[VAR_UPPER] = df[VAR_RAND_TIME] + pd.to_timedelta(df[VAR_TW_UPPER], unit="D")
df[VAR_LOWER] = df[VAR_RAND_TIME] + pd.to_timedelta(df[VAR_TW_LOWER], unit="D")

# 筛选期时间窗反转
for sv in SCREENING_VISITS:
    mask = df[VAR_VISIT] == sv
    df.loc[mask, VAR_UPPER] = df.loc[mask, VAR_RAND_TIME] - pd.to_timedelta(
        df.loc[mask, VAR_TW_UPPER], unit="D"
    )
    df.loc[mask, VAR_LOWER] = df.loc[mask, VAR_RAND_TIME] - pd.to_timedelta(
        df.loc[mask, VAR_TW_LOWER], unit="D"
    )

df[VAR_OVERDUE] = np.where(
    (df[VAR_EVAL_DATE] > df[VAR_UPPER]) | (df[VAR_EVAL_DATE] < df[VAR_LOWER]),
    "超窗", "未超窗",
)
df = df[df[VAR_OVERDUE] == "超窗"]

# ── SV 去重 ──

if df_dedup is not None:
    df_dedup = df_dedup.sort_values(by=[VAR_SUBJ, VAR_VISIT, VAR_FORM, DEDUP_SV_DATE])
    df_dedup = df_dedup.drop_duplicates()
    df_dedup = df_dedup[df_dedup[VAR_STATUS] != EXCLUDE_STATUS]
    df_dedup[VAR_CAT] = "其他指标超窗"

    df_sv_tw = (
        df_dedup.merge(df_tw, on=[VAR_CAT, VAR_VISIT], how="left")
                .merge(df_rand, on=VAR_SUBJ, how="left")
    )
    df_sv_tw[VAR_RAND_TIME] = pd.to_datetime(df_sv_tw[VAR_RAND_TIME], errors="coerce")
    df_sv_tw[DEDUP_SV_DATE] = pd.to_datetime(df_sv_tw[DEDUP_SV_DATE], errors="coerce")
    df_sv_tw[VAR_TW_UPPER]  = pd.to_numeric(df_sv_tw[VAR_TW_UPPER], errors="coerce")
    df_sv_tw[VAR_TW_LOWER]  = pd.to_numeric(df_sv_tw[VAR_TW_LOWER], errors="coerce")
    df_sv_tw[VAR_UPPER] = df_sv_tw[VAR_RAND_TIME] + pd.to_timedelta(df_sv_tw[VAR_TW_UPPER], unit="D")
    df_sv_tw[VAR_LOWER] = df_sv_tw[VAR_RAND_TIME] + pd.to_timedelta(df_sv_tw[VAR_TW_LOWER], unit="D")
    df_sv_tw[VAR_OVERDUE] = np.where(
        (df_sv_tw[DEDUP_SV_DATE] > df_sv_tw[VAR_UPPER])
        | (df_sv_tw[DEDUP_SV_DATE] < df_sv_tw[VAR_LOWER]),
        "超窗", "未超窗",
    )
    df_sv_tw = df_sv_tw[df_sv_tw[VAR_OVERDUE] == "超窗"]

    visit_drop = df_sv_tw[[VAR_SUBJ, VAR_VISIT, VAR_OVERDUE, DEDUP_SV_DATE]].rename(columns={
        VAR_OVERDUE: "访视超窗",
        DEDUP_SV_DATE: "访视日期",
    })
    df = df.merge(visit_drop, on=[VAR_SUBJ, VAR_VISIT], how="left")
    df = df[(df["访视超窗"].isna()) | (df["访视日期"] != df[VAR_EVAL_DATE])]

# ── 5 派生（超窗时间 + 计划时间窗）──

df[VAR_OVER_DAYS] = np.where(
    df[VAR_EVAL_DATE] > df[VAR_UPPER],
    (df[VAR_EVAL_DATE] - df[VAR_UPPER]).dt.days,
    (df[VAR_EVAL_DATE] - df[VAR_LOWER]).dt.days,
)
df[VAR_PLAN_TW] = df[VAR_LOWER].astype(str) + "-" + df[VAR_UPPER].astype(str)

# ── 6 连接（完成状态 + 首次用药 + 随机号）──

df_end = load_sheet(FORM_END, IMPORT_END)

df_ec = load_sheet("EC_ED", IMPORT_EC)
df_ec[VAR_DOSE_DATE] = pd.to_datetime(df_ec[VAR_DOSE_DATE], errors="coerce")
df_ec = df_ec.sort_values(by=[VAR_SUBJ, VAR_DOSE_DATE]).dropna(subset=[VAR_DOSE_DATE])
df_fd = df_ec.groupby(VAR_SUBJ)[VAR_DOSE_DATE].first().reset_index()

df_rand2 = load_sheet(FORM_RAND, usecols=IMPORT_RAND2)
df_rand2 = df_rand2[df_rand2[VAR_STATUS] != EXCLUDE_STATUS].drop(columns=VAR_STATUS)

df_out = (
    df.merge(df_end,   on=VAR_SUBJ, how="left")
      .merge(df_fd,    on=VAR_SUBJ, how="left")
      .merge(df_rand2, on=VAR_SUBJ, how="left")
)

# ── 7 格式化 ──

df_out[VAR_EVAL_DATE] = df_out[VAR_EVAL_DATE].dt.strftime("%Y-%m-%d")
df_out[VAR_RAND_TIME] = df_out[VAR_RAND_TIME].dt.strftime("%Y-%m-%d")
df_out[VAR_DOSE_DATE] = df_out[VAR_DOSE_DATE].dt.strftime("%Y-%m-%d")
df_out[VAR_RAND_NO] = df_out[VAR_RAND_NO].apply(
    lambda x: str(x) if pd.notna(x) and x != "" else ""
)
df_out = df_out.reindex(df_out[VAR_OVER_DAYS].abs().sort_values(ascending=False).index)

_RENAME_MAP = {
    VAR_SUBJ:      VAR_SCREEN_NO,
    VAR_FORM:      VAR_FORM_NAME,
    VAR_EVAL_DATE: VAR_DATE,
    VAR_RAND_TIME: VAR_RAND_DATE,
    VAR_DOSE_DATE: VAR_FIRST_DOSE,
    VAR_COMPLETED: VAR_COMPLETE,
}
df_out = df_out.rename(columns=_RENAME_MAP)
df_out = df_out[OUTPUT_COLS].fillna("")

# ── 8 输出（按访视名称分组，每个访视一个 docx）──

table_no = 1
for visit_name, sub_df in df_out.groupby(VAR_VISIT, sort=False, dropna=False):
    visit_disp = "未知访视" if pd.isna(visit_name) else str(visit_name).replace("/", "_")

    lc = len(sub_df)
    ls = len(sub_df.drop_duplicates(subset=[VAR_SCREEN_NO]))
    sub_df.insert(0, "No.", range(1, len(sub_df) + 1))

    title = f"表{table_no} {REPORT_NAME}（{visit_disp}）（{lc}例次{ls}例）"

    save_table_to_docx_threeline(
        sub_df,
        f"{output_table_dir}/{REPORT_NAME}_{visit_disp}.docx",
        title,
        NOTES,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
    )
    table_no += 1
