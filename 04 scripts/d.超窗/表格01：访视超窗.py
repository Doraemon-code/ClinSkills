import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import raw_path, timewin_path, output_path
from utils.output_format import export_to_excel_with_format
from utils.loaders import load_sheet, load_first_dose, load_rand

# ── 列名集中管理 ──

# 导入列名
IMPORT_SV   = ['受试者', '受试者状态', '访视名称', '页面名称', '访视日期']
IMPORT_RAND = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_END  = ['受试者', '页面名称', '是否完成试验_TXT']
IMPORT_EC   = ['受试者', '服药日期']

# 中间列名
VAR_SUBJ      = "受试者"
VAR_STATUS    = "受试者状态"
VAR_VISIT     = "访视名称"
VAR_FORM      = "页面名称"
VAR_EVAL_DATE = "评估日期"
VAR_RAND_TIME = "随机时间"
VAR_TW_UPPER  = "时间窗上限"
VAR_TW_LOWER  = "时间窗下限"
VAR_UPPER     = "上限"
VAR_LOWER     = "下限"
VAR_OVERDUE   = "超窗"
VAR_OVER_DAYS = "超窗时间（天）"
VAR_PLAN_TW   = "计划时间窗"
VAR_CAT       = "类别"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_RAND_NO      = "随机号"
VAR_FIRST_DOSE   = "首次用药日期"
VAR_COMPLETED    = "是否完成试验"
OUTPUT_COLS = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_VISIT, "表单名称",
    "发生日期", VAR_FIRST_DOSE, VAR_PLAN_TW,
    VAR_OVER_DAYS, VAR_COMPLETED,
]

# ── 1 读取 ──

# 时间窗
df_tw = pd.read_excel(timewin_path, sheet_name="时间窗",
                       usecols=["类别", "访视名称", "时间窗下限", "时间窗上限"])
df_tw[VAR_TW_LOWER] = df_tw[VAR_TW_LOWER].astype("Int32")
df_tw[VAR_TW_UPPER] = df_tw[VAR_TW_UPPER].astype("Int32")

# 访视数据
df_sv = load_sheet("SV", IMPORT_SV + [VAR_EVAL_DATE])
df_sv = df_sv.rename(columns={"访视日期": VAR_EVAL_DATE})

# ── 2 归一化 ──

df = df_sv.sort_values(by=[VAR_SUBJ, VAR_VISIT, VAR_FORM, VAR_EVAL_DATE])
df = df.drop_duplicates()

# ── 3 筛选 ──

df = df[df[VAR_STATUS] != "筛选失败"]
df[VAR_CAT] = "其他指标超窗"

# ── 6 连接（时间窗 + 随机时间） ──

df_rand = load_rand(cols=[VAR_SUBJ, VAR_RAND_TIME])

df = (df.merge(df_tw, on=[VAR_CAT, "访视名称"], how="left")
        .merge(df_rand, on=VAR_SUBJ, how="left")
     )

# ── 5 派生（计算上下限 + 判断超窗） ──

df[VAR_RAND_TIME] = pd.to_datetime(df[VAR_RAND_TIME], errors='coerce')
df[VAR_EVAL_DATE] = pd.to_datetime(df[VAR_EVAL_DATE], errors='coerce')
df[VAR_TW_UPPER]  = pd.to_numeric(df[VAR_TW_UPPER], errors='coerce')
df[VAR_TW_LOWER]  = pd.to_numeric(df[VAR_TW_LOWER], errors='coerce')

condition = df[VAR_VISIT] == "筛选期（V1，D-15~-13）"

df.loc[~condition, VAR_UPPER] = df.loc[~condition, VAR_RAND_TIME] + pd.to_timedelta(df.loc[~condition, VAR_TW_UPPER], unit='D')
df.loc[~condition, VAR_LOWER] = df.loc[~condition, VAR_RAND_TIME] + pd.to_timedelta(df.loc[~condition, VAR_TW_LOWER], unit='D')

df.loc[condition, VAR_UPPER] = df.loc[condition, VAR_RAND_TIME] - pd.to_timedelta(df.loc[condition, VAR_TW_UPPER], unit='D')
df.loc[condition, VAR_LOWER] = df.loc[condition, VAR_RAND_TIME] - pd.to_timedelta(df.loc[condition, VAR_TW_LOWER], unit='D')

df[VAR_OVERDUE] = np.where(
    (df[VAR_EVAL_DATE] > df[VAR_UPPER]) | (df[VAR_EVAL_DATE] < df[VAR_LOWER]),
    "超窗", "未超窗"
)
df = df[df[VAR_OVERDUE] == "超窗"]

# ── 构建输出表 ──

visit = df.copy()
visit[VAR_OVER_DAYS] = np.where(
    visit[VAR_EVAL_DATE] > visit[VAR_UPPER],
    (visit[VAR_EVAL_DATE] - visit[VAR_UPPER]).dt.days,
    (visit[VAR_EVAL_DATE] - visit[VAR_LOWER]).dt.days
)
visit[VAR_PLAN_TW] = visit[VAR_LOWER].astype(str) + "-" + visit[VAR_UPPER].astype(str)

# ── 6 连接（完成状态 + 首次用药 + 随机号） ──

df_end = load_sheet("DS_END", IMPORT_END)
df_ec  = load_first_dose()

df_rand2 = load_rand(cols=[VAR_SUBJ, VAR_STATUS, VAR_RAND_NO])
df_rand2 = df_rand2[df_rand2[VAR_STATUS] != "筛选失败"]

visit = (visit.merge(df_end,   on=VAR_SUBJ, how="left")
              .merge(df_ec,    on=VAR_SUBJ, how="left")
              .merge(df_rand2, on=VAR_SUBJ, how="left")
         )

# ── 7 格式化 ──

visit = visit[OUTPUT_COLS]
visit.insert(0, "No.", range(1, len(visit) + 1))

visit[VAR_EVAL_DATE]   = visit[VAR_EVAL_DATE].dt.strftime('%Y-%m-%d')
visit[VAR_FIRST_DOSE]  = visit[VAR_FIRST_DOSE].dt.strftime('%Y-%m-%d')
visit = visit.reindex(visit[VAR_OVER_DAYS].abs().sort_values(ascending=False).index)

visit = visit.rename(columns={
    VAR_SUBJ:       VAR_SCREEN_NO,
    VAR_FORM:       "表单名称",
    VAR_EVAL_DATE:  "发生日期",
    VAR_COMPLETED:  "是否完成试验",
})

# ── 8 输出 ──

lc = len(visit)
ls = len(visit.drop_duplicates(subset=[VAR_SCREEN_NO]))

export_to_excel_with_format(
    visit,
    f"{output_path}/listing/访视超窗清单.xlsx",
    "访视超窗清单",
    f"访视超窗清单（{lc}例次{ls}例）",
)
