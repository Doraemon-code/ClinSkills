import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_rand, load_sheet, load_sc_demographics
from utils.output_format import export_to_excel_with_format

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ["受试者", "随机号"]
IMPORT_DM   = ["受试者", "性别_TXT", "出生日期", "年龄", "民族_TXT", "其他民族"]
IMPORT_SC   = ["受试者", "婚育情况_TXT", "其他婚育情况"]

# 中间列名
VAR_SUBJ        = "受试者"
VAR_ETHNIC      = "民族"
VAR_OTHER_ETH   = "其他民族"
VAR_MARRY       = "婚育情况"
VAR_MARRY_RAW   = "婚育情况_TXT"
VAR_OTHER_MARRY = "其他婚育情况"

# 输出列名
VAR_SCREEN_NO = "筛选号"
VAR_AGE       = "年龄（岁）"

OUTPUT_COLS = [
    "筛选号", "随机号", "性别", "出生日期", VAR_AGE,
    VAR_ETHNIC, VAR_MARRY,
]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_dm   = load_sheet("DM", cols=IMPORT_DM)
df_sc   = load_sc_demographics(cols=IMPORT_SC)

# ── 6 连接 ──

df_out = (df_dm.merge(df_sc,   on=VAR_SUBJ, how="left")
               .merge(df_rand, on=VAR_SUBJ, how="left"))

# ── 7 格式化 ──

# 去掉 _TXT 后缀
df_out.columns = [col.replace("_TXT", "") for col in df_out.columns]

# 民族：有"其他民族"时优先取之
df_out[VAR_ETHNIC] = np.where(
    df_out[VAR_OTHER_ETH].notna(),
    df_out[VAR_OTHER_ETH],
    df_out[VAR_ETHNIC],
)
df_out = df_out.drop(columns=[VAR_OTHER_ETH])

# 婚育情况：有"其他婚育情况"时优先取之
df_out[VAR_MARRY] = np.where(
    df_out[VAR_OTHER_MARRY].notna(),
    df_out[VAR_OTHER_MARRY],
    df_out[VAR_MARRY],
)
df_out = df_out.drop(columns=[VAR_OTHER_MARRY])

# 重命名
df_out = df_out.rename(columns={
    VAR_SUBJ: VAR_SCREEN_NO,
    "年龄":   VAR_AGE,
})

# 选列 + 序号
df_out = df_out[OUTPUT_COLS].copy()
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

n = len(df_out)
export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/表43 人口学资料清单.xlsx",
    "表43 人口学资料清单",
    f"表43 人口学资料清单（{n}例）",
)
