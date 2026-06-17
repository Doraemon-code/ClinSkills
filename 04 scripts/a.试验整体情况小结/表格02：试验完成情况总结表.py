import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ['中心编号', '研究中心', '受试者', '受试者是否随机入组_TXT']
IMPORT_END  = ['受试者', '页面名称', '受试者是否完成试验_TXT']

# 中间列名
VAR_SUBJ       = "受试者"
VAR_CENTER_NO  = "中心编号"
VAR_CENTER     = "研究中心"
VAR_RAND_STATUS = "受试者是否随机入组_TXT"
VAR_COMPLETE   = "受试者是否完成试验_TXT"
VAR_CENTER_FULL = "研究中心全称"
VAR_CATEGORY   = "类别"

# 输出列名
VAR_TOTAL      = "筛选总人数"
VAR_FAIL       = "筛选失败人数"
VAR_ENROLL     = "随机入组人数"
VAR_DROPOUT    = "退出试验人数"
VAR_FINISH     = "完成试验人数"
VAR_FAIL_RATE  = "筛败率"
VAR_ENROLL_RATE = "入组率"
VAR_DROP_RATE  = "脱落率"
OUTPUT_COLS = [VAR_CENTER, VAR_TOTAL, VAR_FAIL, VAR_FAIL_RATE,
               VAR_ENROLL, VAR_ENROLL_RATE, VAR_DROPOUT, VAR_DROP_RATE, VAR_FINISH]

# ── 1 读取 ──

df_end  = load_sheet("DS_END", IMPORT_END)
df_rand = load_rand(cols=IMPORT_RAND).fillna("")

# ── 2 归一化 ──

df_rand[VAR_CENTER_FULL] = df_rand[VAR_CENTER_NO] + "-" + df_rand[VAR_CENTER]

# ── 6 连接 ──

df_out = df_rand.merge(df_end, on=[VAR_SUBJ], how="left")

# ── 5 派生 ──

def classify_subject_status(row):
    """根据是否随机入组、是否完成试验，判定受试者类别。"""
    if row[VAR_RAND_STATUS] == "否":
        return "筛选失败"
    elif row[VAR_RAND_STATUS] == "是":
        return "完成试验" if row[VAR_COMPLETE] == "是" else "退出试验"
    return "未知"

df_out[VAR_CATEGORY] = df_out.apply(classify_subject_status, axis=1)
df_out = df_out.drop(columns=[VAR_CENTER_NO, VAR_SUBJ, VAR_RAND_STATUS, VAR_COMPLETE])

# ── 4 变形 ──

ct = pd.crosstab(df_out[VAR_CENTER_FULL], df_out[VAR_CATEGORY])

n_fail     = ct.get("筛选失败", pd.Series(0, index=ct.index))
n_complete = ct.get("完成试验", pd.Series(0, index=ct.index))
n_dropout  = ct.get("退出试验", pd.Series(0, index=ct.index))

summary = pd.DataFrame({
    VAR_TOTAL:   ct.sum(axis=1),
    VAR_FAIL:    n_fail,
    VAR_ENROLL:  n_complete + n_dropout,
    VAR_DROPOUT: n_dropout,
    VAR_FINISH:  n_complete,
}, index=ct.index)

summary[VAR_FAIL_RATE]   = summary[VAR_FAIL] / summary[VAR_TOTAL] * 100
summary[VAR_ENROLL_RATE] = summary[VAR_ENROLL] / summary[VAR_TOTAL] * 100
summary[VAR_DROP_RATE]   = summary[VAR_DROPOUT] / summary[VAR_ENROLL] * 100
summary[VAR_DROP_RATE]   = summary[VAR_DROP_RATE].replace([np.inf, -np.inf], np.nan)

# 合计行
total = summary[[VAR_TOTAL, VAR_FAIL, VAR_ENROLL, VAR_DROPOUT, VAR_FINISH]].sum()
total[VAR_FAIL_RATE]   = total[VAR_FAIL] / total[VAR_TOTAL] * 100
total[VAR_ENROLL_RATE] = total[VAR_ENROLL] / total[VAR_TOTAL] * 100
total[VAR_DROP_RATE]   = (
    total[VAR_DROPOUT] / total[VAR_ENROLL] * 100
    if total[VAR_ENROLL] != 0 else np.nan
)

summary.loc["合计"] = total

# ── 7 格式化 ──

count_cols = [VAR_TOTAL, VAR_FAIL, VAR_ENROLL, VAR_DROPOUT, VAR_FINISH]
summary[count_cols] = summary[count_cols].fillna(0).astype(int)

for col in [VAR_FAIL_RATE, VAR_ENROLL_RATE, VAR_DROP_RATE]:
    summary[col] = summary[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")

summary = summary.reset_index().rename(columns={VAR_CENTER_FULL: VAR_CENTER})
summary = summary[OUTPUT_COLS]

# ── 8 输出 ──

notes = [
    "筛败率%=筛选失败人数/筛选总人数*100%",
    "入组率%=随机入组人数/筛选总人数*100%",
    "脱落率%=退出试验人数/随机入组人数*100%",
]

save_table_to_docx_threeline(
    summary,
    f'{output_path}/table/表2 试验完成情况总结表.docx',
    '表2 试验完成情况总结表',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
