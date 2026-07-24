# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 试验完成情况总结表（按中心汇总）：以随机/入组汇总表判定每位受试者
#       类别（筛选失败 / 完成试验 / 退出试验），按中心交叉汇总人数，计算
#       筛败率、入组率、脱落率，末尾附合计行。
# @tags 试验完成,中心汇总,筛败率,入组率,脱落率,crosstab,合计行,DMR,三线表,试验整体情况
# @config REPORT_NAME, FORM_END/FORM_RAND, IMPORT_CENTER_NAME,
#         IMPORT_RAND_STATUS/IMPORT_COMPLETED, RAND_YES/RAND_NO/COMPLETE_YES

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

VAR_SUBJ      = system_cols("subject")   # 受试者列
VAR_CENTER_NO = system_cols("center")    # 中心编号列（若随机数据为独立文件、列名不同，改为对应列）

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 表单 OID、字段名、是/否解码值均为项目特异，须据 query_metadata.py 探索替换。

REPORT_NAME = "试验完成情况总结表"

FORM_END  = "DS_END"    # 研究结束/试验总结表单（含是否完成试验）
FORM_RAND = "DS_RAND"   # 随机/入组汇总表单（含是否随机入组、研究中心；若为独立随机文件另行读取）

IMPORT_CENTER_NAME = "研究中心"                 # 中心名称（业务字段）
IMPORT_RAND_STATUS = "受试者是否随机入组_TXT"    # 是否随机入组（解码列；后缀随 EDC）
IMPORT_COMPLETED   = "受试者是否完成试验_TXT"    # 是否完成试验（解码列；后缀随 EDC）

# 是/否解码值（跨 EDC 语言：中文是/否，英文可能 Yes/No 等）
RAND_YES     = "是"
RAND_NO      = "否"
COMPLETE_YES = "是"

# ── 列名集中管理（中间 + 输出）──

VAR_CENTER_FULL = "研究中心全称"
VAR_CATEGORY    = "类别"

VAR_CENTER      = "研究中心"
VAR_TOTAL       = "筛选总人数"
VAR_FAIL        = "筛选失败人数"
VAR_ENROLL      = "随机入组人数"
VAR_DROPOUT     = "退出试验人数"
VAR_FINISH      = "完成试验人数"
VAR_FAIL_RATE   = "筛败率"
VAR_ENROLL_RATE = "入组率"
VAR_DROP_RATE   = "脱落率"
OUTPUT_COLS = [VAR_CENTER, VAR_TOTAL, VAR_FAIL, VAR_FAIL_RATE,
               VAR_ENROLL, VAR_ENROLL_RATE, VAR_DROPOUT, VAR_DROP_RATE, VAR_FINISH]

# ── 1 读取 ──

df_end  = load_sheet(FORM_END,  usecols=[VAR_SUBJ, IMPORT_COMPLETED])
df_rand = load_sheet(FORM_RAND, usecols=[VAR_CENTER_NO, IMPORT_CENTER_NAME, VAR_SUBJ, IMPORT_RAND_STATUS]).fillna("")

# ── 2 归一化 ──

df_rand[VAR_CENTER_FULL] = df_rand[VAR_CENTER_NO].astype(str) + "-" + df_rand[IMPORT_CENTER_NAME].astype(str)

# ── 6 连接 ──

df_out = df_rand.merge(df_end, on=[VAR_SUBJ], how="left")

# ── 5 派生：判定受试者类别 ──

def classify_subject_status(row):
    """根据是否随机入组、是否完成试验，判定受试者类别。"""
    if row[IMPORT_RAND_STATUS] == RAND_NO:
        return "筛选失败"
    elif row[IMPORT_RAND_STATUS] == RAND_YES:
        return "完成试验" if row[IMPORT_COMPLETED] == COMPLETE_YES else "退出试验"
    return "未知"

df_out[VAR_CATEGORY] = df_out.apply(classify_subject_status, axis=1)

# ── 4 变形：中心 × 类别 交叉表 ──

ct = pd.crosstab(df_out[VAR_CENTER_FULL], df_out[VAR_CATEGORY])

n_fail     = ct.get("筛选失败", pd.Series(0, index=ct.index)).astype("Int64")
n_complete = ct.get("完成试验", pd.Series(0, index=ct.index)).astype("Int64")
n_dropout  = ct.get("退出试验", pd.Series(0, index=ct.index)).astype("Int64")

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

# 按中心编号数值升序（索引为「中心编号-研究中心」，取前缀数字排序）
summary = summary.sort_index(key=lambda idx: idx.str.split("-", n=1).str[0].astype(int))

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
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
