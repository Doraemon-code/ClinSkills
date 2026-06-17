import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_rand, load_sheet, load_completion
from utils.output_format import save_table_to_docx_threeline

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ["受试者", "随机号"]
IMPORT_SV   = ["受试者", "受试者状态", "访视名称", "页面名称", "访视OID", "访视日期"]

# 中间列名
VAR_SUBJ        = "受试者"
VAR_STATUS      = "受试者状态"
VAR_VISIT_NAME  = "访视名称"
VAR_VISIT_OID   = "访视OID"
VAR_PAGE        = "页面名称"
VAR_ASSESS_DATE = "评估日期"
VAR_DONE        = "是否进行"
VAR_RAND_NO     = "随机号"
VAR_COMPLETE    = "是否完成试验"

# 输出列名
VAR_SCREEN_NO = "筛选号"

# 透视后的访视列（来自 SV.访视名称 的取值，按访视OID 顺序）
VISIT_COLS = [
    "筛选/基线期（D-15～D-1）",      # V10
    "治疗期（用药后第4周末±3天）",   # V20
    "治疗期（用药后第8周末±3天）",   # V30
    "提前退出访视",                  # V80
]

OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, *VISIT_COLS, VAR_COMPLETE]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_end  = load_completion()
df_sv   = load_sheet("SV", cols=IMPORT_SV)

# ── 2 归一化 + 交叉表 ──

# 构建 受试者×访视 完整网格，确保未激活的访视也有行
df_cross = pd.MultiIndex.from_product(
    [df_sv[VAR_SUBJ].unique(), VISIT_COLS],
    names=[VAR_SUBJ, VAR_VISIT_NAME],
).to_frame(index=False)

# SV 只保留访视日期页 + 去重，每受试者×访视一行
df_sv = df_sv[df_sv[VAR_PAGE] == "访视日期"].copy()
df_sv = df_sv.rename(columns={"访视日期": VAR_ASSESS_DATE})
df_sv = df_sv.sort_values(by=[VAR_SUBJ, VAR_VISIT_NAME, VAR_ASSESS_DATE]).drop_duplicates(
    subset=[VAR_SUBJ, VAR_VISIT_NAME]
)

# ── 3a 筛选（剔除无效记录）──

df_sv = df_sv[(df_sv[VAR_STATUS] != "筛选失败") & (df_sv[VAR_VISIT_OID] != "V90")]

# 交叉表合并实际访视数据（left → 保留未激活的访视行）
df_sv = df_cross.merge(
    df_sv[[VAR_SUBJ, VAR_VISIT_NAME, VAR_STATUS, VAR_VISIT_OID, VAR_ASSESS_DATE]],
    on=[VAR_SUBJ, VAR_VISIT_NAME],
    how="left",
)

# ── 5 派生 ──

# 是否进行：无访视记录=未激活，有记录但无日期=否，有日期=是
df_sv[VAR_DONE] = np.where(
    df_sv[VAR_ASSESS_DATE].notna(), "是",
    np.where(df_sv[VAR_VISIT_OID].notna(), "否", "未激活"),
)

# ── 6 连接 ──

df_out = (df_sv.merge(df_rand, on=VAR_SUBJ, how="left")
               .merge(df_end,  on=VAR_SUBJ, how="left"))

# ── 3b 筛选（仅保留部分访视缺失的受试者）──

df_out = df_out.sort_values(by=[VAR_SUBJ, VAR_VISIT_OID])
df_out = df_out.groupby(VAR_SUBJ, group_keys=False).filter(
    lambda x: x[VAR_DONE].nunique() > 1
)

# ── 4 变形 ──

df_out = df_out.pivot(
    index=[VAR_SUBJ, VAR_RAND_NO, VAR_COMPLETE],
    columns=VAR_VISIT_NAME,
    values=VAR_DONE,
).reset_index()
df_out.columns.name = None
df_out = df_out.reindex(columns=[VAR_SUBJ, VAR_RAND_NO, VAR_COMPLETE, *VISIT_COLS])

# ── 7 格式化 ──

df_out = df_out.fillna("未激活")
df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})

df_out = df_out[OUTPUT_COLS].copy()
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

n = len(df_out.drop_duplicates(subset=[VAR_SCREEN_NO]))
notes = [
    "访视列：“是”代表进行本次访视，“否”代表已激活但未进行本次访视，“未激活”代表该访视未激活",
]
save_table_to_docx_threeline(
    df_out,
    f"{output_path}/table/表22 访视缺失清单.docx",
    f"表22 访视缺失清单（{n}例）",
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
)
