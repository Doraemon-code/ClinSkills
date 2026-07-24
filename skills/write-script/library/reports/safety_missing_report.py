# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 安全性评价指标缺失三线表：逐表单检查安全性评价指标（gate="是" 但
#       结果列为空，或 gate="否" 整表缺失），支持水平宽表 melt 和垂直长表
#       两种格式，排除计划外访视后输出缺失清单。
# @tags 安全性,缺失,gate,表单缺失,melt,计划外访视,DMR,三线表
# @config REPORT_NAME, SAFETY_FORMS, FORM_RAND/FORM_END,
#         IMPORT_RAND_NO/IMPORT_COMPLETED

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

VAR_SUBJ = system_cols("subject")    # 受试者列

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID、字段名、gate 值与结果列为项目特异。

REPORT_NAME = "安全性评价指标缺失"

FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"

IMPORT_RAND_NO   = "随机号"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"   # 解码列；后缀随 EDC

# 安全性评价表单定义
# horizontal（水平格式）：每项一列，需 melt；{sheet: (gate列, None, [结果列列表])}
# vertical（垂直格式）：每行一项，有项目列+结果列；{sheet: (gate列, 项目列, [结果列])}
SAFETY_FORMS = {
    "horizontal": {
        "VS": {"gate": "是否检查_TXT", "results": ["体温", "HR", "呼吸", "收缩压"]},
        "EG": {"gate": "是否检查_TXT", "results": ["心率", "QT", "QTC"]},
    },
    "vertical": {
        "PE":      {"gate": "是否检查_TXT", "item_col": "项目_TXT", "result_col": "临床评估_TXT"},
        "LB_HEM":  {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_URI":  {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_HCG1": {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_HCG2": {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_MIC":  {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_UACR": {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_ESR":  {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_CRP":  {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
        "LB_CHEM": {"gate": "是否检查_TXT", "item_col": "项目.1",   "result_col": "测定值"},
    },
}

# ── 列名集中管理 ──

IMPORT_SYSTEM = [VAR_SUBJ, "受试者状态", "访视名称", "页面名称"]
VAR_GATE      = "是否评估"
VAR_ITEM      = "缺失项"
VAR_RESULT    = "结果"

VAR_STATUS = "受试者状态"
VAR_VISIT  = "访视名称"
VAR_FORM   = "页面名称"

VAR_SCREEN_NO = "筛选号"
VAR_RAND_NO   = "随机号"
VAR_FORM_NAME = "表单名称"
VAR_COMPLETED = "是否完成试验"

OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_VISIT, VAR_FORM_NAME, VAR_ITEM, VAR_COMPLETED]

# ── 辅助 ──

def _check_horizontal(sheet, gate_col, result_cols):
    """检查水平格式表单（每项一列）的缺失项。"""
    cols = IMPORT_SYSTEM + [gate_col] + result_cols
    df_f = load_sheet(sheet, usecols=cols)
    df_f = df_f.rename(columns={gate_col: VAR_GATE})

    parts = []

    df_done = df_f[df_f[VAR_GATE] == "是"].copy()
    if len(df_done) > 0:
        df_melt = df_done.melt(
            id_vars=IMPORT_SYSTEM + [VAR_GATE],
            value_vars=result_cols,
            var_name=VAR_ITEM,
            value_name=VAR_RESULT,
        )
        df_missing = df_melt[df_melt[VAR_RESULT].isna()]
        parts.append(df_missing[IMPORT_SYSTEM + [VAR_ITEM]])

    df_skip = df_f[df_f[VAR_GATE] == "否"].copy()
    if len(df_skip) > 0:
        df_skip[VAR_ITEM] = df_skip[VAR_FORM]
        parts.append(df_skip[IMPORT_SYSTEM + [VAR_ITEM]].drop_duplicates())

    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _check_vertical(sheet, gate_col, item_col, result_col):
    """检查垂直格式表单（每行一项）的缺失项。"""
    cols = IMPORT_SYSTEM + [gate_col, item_col, result_col]
    df_f = load_sheet(sheet, usecols=cols)
    df_f = df_f.rename(columns={gate_col: VAR_GATE, item_col: VAR_ITEM, result_col: VAR_RESULT})

    parts = []

    df_done = df_f[df_f[VAR_GATE] == "是"].copy()
    if len(df_done) > 0:
        df_missing = df_done[df_done[VAR_RESULT].isna()]
        parts.append(df_missing[IMPORT_SYSTEM + [VAR_ITEM]])

    df_skip = df_f[df_f[VAR_GATE] == "否"].copy()
    if len(df_skip) > 0:
        df_skip[VAR_ITEM] = df_skip[VAR_FORM]
        parts.append(df_skip[IMPORT_SYSTEM + [VAR_ITEM]].drop_duplicates())

    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ── 1 读取 ──

missing_parts = []

for sheet, cfg in SAFETY_FORMS["horizontal"].items():
    df_m = _check_horizontal(sheet, cfg["gate"], cfg["results"])
    if len(df_m) > 0:
        missing_parts.append(df_m)

for sheet, cfg in SAFETY_FORMS["vertical"].items():
    df_m = _check_vertical(sheet, cfg["gate"], cfg["item_col"], cfg["result_col"])
    if len(df_m) > 0:
        missing_parts.append(df_m)

# ── 2 归一化 ──

if not missing_parts:
    print("无缺失数据")
    exit()

df_missing = pd.concat(missing_parts, ignore_index=True)

# ── 3 筛选 ──

df_missing = df_missing[df_missing[VAR_STATUS] != "筛选失败"]
if VAR_VISIT in df_missing.columns:
    df_missing = df_missing[~df_missing[VAR_VISIT].astype(str).str.contains("计划外")]

# ── 6 连接 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_RAND_NO])

df_end = load_sheet(FORM_END, usecols=[VAR_SUBJ, IMPORT_COMPLETED])
df_end = df_end.rename(columns={IMPORT_COMPLETED: VAR_COMPLETED})

df_out = (
    df_missing.merge(df_rand, on=VAR_SUBJ, how="left")
              .merge(df_end, on=VAR_SUBJ, how="left")
)

# ── 7 格式化 ──

df_out[VAR_RAND_NO] = df_out[VAR_RAND_NO].apply(
    lambda x: str(x) if pd.notna(x) and x != "" else ""
)

_RENAME_MAP = {
    VAR_SUBJ: VAR_SCREEN_NO,
    VAR_FORM: VAR_FORM_NAME,
}
df_out = df_out.rename(columns=_RENAME_MAP)
df_out = df_out[OUTPUT_COLS].fillna("")
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

notes = [
    "确认受试者访视缺失，该访视相关检查缺失不在此处重复罗列；",
    "整个表单缺失时，缺失项为表单名称。",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=False,
)
