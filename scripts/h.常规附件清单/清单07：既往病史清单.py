import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_rand, load_sheet
from utils.output_format import export_to_excel_with_format

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ["受试者", "随机号"]
IMPORT_MH   = ["受试者", "疾病名称", "开始日期", "首次用药前，是否持续_TXT", "结束日期"]

# 中间列名
VAR_SUBJ    = "受试者"
VAR_DISEASE = "疾病名称"

# 输出列名
VAR_SCREEN_NO = "筛选号"
VAR_ONGOING   = "首次用药前，是否持续"

OUTPUT_COLS = [
    VAR_SCREEN_NO, "随机号", VAR_DISEASE, "开始日期", VAR_ONGOING, "结束日期",
]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_mh   = load_sheet("MH", cols=IMPORT_MH)

# ── 3 筛选 ──

# 仅保留填写了疾病名称的记录
df_out = df_mh[df_mh[VAR_DISEASE].notna()].copy()

# ── 6 连接 ──

df_out = df_out.merge(df_rand, on=VAR_SUBJ, how="left")

# ── 7 格式化 ──

# 去掉 _TXT 后缀
df_out.columns = [col.replace("_TXT", "") for col in df_out.columns]

# 重命名
df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})

# 选列 + 序号
df_out = df_out[OUTPUT_COLS].copy()
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

n = len(df_out)
export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/表46 既往病史清单.xlsx",
    "表46 既往病史清单",
    f"表46 既往病史清单（{n}例）",
)
