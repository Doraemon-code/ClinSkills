# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 其他指标缺失清单（xlsx）：检查非核心指标表单的缺失情况——
#       gate="是" 但结果为空、gate="否" 整表未做、以及特殊业务规则
#       （如药物回收"否"时需填原因）。melt 为长表后输出 xlsx 清单。
# @tags 缺失,其他指标,gate,melt,xlsx,清单
# @config LISTING_NAME, OTHER_FORMS, FORM_RAND/FORM_END,
#         IMPORT_RAND_NO/IMPORT_COMPLETED, SPECIAL_RULES

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_listing_dir
from utils.output_format import export_to_excel_with_format
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")    # 受试者列

# ── 项目配置（按本项目元数据调整；仅业务字段）──

LISTING_NAME = "其他指标缺失清单"

FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"

IMPORT_RAND_NO   = "随机号"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"

# 其他指标表单定义
# 每项：(sheet_oid, gate_col, [结果列列表], extra_import_cols)
# gate="是" 但结果列为 NaN → 缺失项（SPECIAL_RULES 中的列除外）
# gate="否" → 整表未做
OTHER_FORMS = [
    ("VS_HW",  "是否进行身高体重检查_TXT", ["身高", "体重", "BMI"], []),
    ("DA_DD1", "是否发放_TXT",             ["发药日期", "受试者首次用药时间", "发药量"], []),
    ("DA_DR1", "是否回收_TXT",             ["如否，请注明未回收原因", "回收日期", "回收药量",
                                             "损坏或遗失药量", "实际服用药量（暴露量）"], []),
]

# 特殊规则：排除的缺失判定条件
# (表单页面名, 缺失项名, gate值) — gate="是"时该字段为空不算缺失
SPECIAL_RULES = [
    ("试验药物回收记录", "如否，请注明未回收原因", "是"),
]

# ── 列名集中管理 ──

VAR_STATUS = "受试者状态"
VAR_VISIT  = "访视名称"
VAR_FORM   = "页面名称"
VAR_GATE   = "是否评估"
VAR_ITEM   = "项目"
VAR_RESULT = "结果"
VAR_RAND_NO = IMPORT_RAND_NO
VAR_COMPLETED = IMPORT_COMPLETED

VAR_OUT_SUBJ    = "筛选号"
VAR_OUT_RAND    = "随机号"
VAR_OUT_VISIT   = "访视名称"
VAR_OUT_FORM    = "表单名称"
VAR_OUT_ITEM    = "缺失项"
VAR_OUT_COMPLETE = "是否完成试验"

OUTPUT_COLS = [
    VAR_OUT_SUBJ, VAR_OUT_RAND, VAR_OUT_VISIT,
    VAR_OUT_FORM, VAR_OUT_ITEM, VAR_OUT_COMPLETE,
]

ID_COLS = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM]


def _melt_form(df, gate_col, result_cols):
    """将宽表 melt 为长表，统一列名。"""
    df = df.melt(
        id_vars=ID_COLS + [gate_col],
        value_vars=result_cols,
        var_name=VAR_ITEM,
        value_name=VAR_RESULT,
    )
    return df.rename(columns={gate_col: VAR_GATE})


# ── 1 读取 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_RAND_NO])
df_end = load_sheet(FORM_END, usecols=[VAR_SUBJ, IMPORT_COMPLETED])
df_end = df_end.rename(columns={IMPORT_COMPLETED: VAR_COMPLETED})

all_parts = []
for sheet, gate_col, result_cols, extra_cols in OTHER_FORMS:
    df_raw = load_sheet(sheet, usecols=ID_COLS + [gate_col] + result_cols + extra_cols)
    df_raw = df_raw.replace("", np.nan)
    all_parts.append(_melt_form(df_raw, gate_col, result_cols))

df_all = pd.concat(all_parts, ignore_index=True)

# ── 3 筛选 ──

special_set = {(r, i, g) for r, i, g in SPECIAL_RULES}

# 3a: 进行了评估但结果为空（排除特殊规则）
mask_missing = (
    (df_all[VAR_GATE] == "是")
    & (df_all[VAR_RESULT].isna())
    & ~(
        df_all.apply(
            lambda row: (row[VAR_FORM], row[VAR_ITEM], row[VAR_GATE]) in special_set,
            axis=1,
        )
    )
)
df_missing = df_all[mask_missing].copy()

# 3b: 未进行评估（整个表单未做）
df_not_done = df_all[df_all[VAR_GATE] == "否"].copy()
df_not_done[VAR_ITEM] = df_not_done[VAR_FORM]
df_not_done = df_not_done.drop_duplicates(
    subset=[VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM, VAR_ITEM]
)

# ── 4-6 连接 ──

df_out = pd.concat([df_missing, df_not_done], ignore_index=True)
df_out = df_out[~df_out[VAR_VISIT].astype(str).str.contains("计划外访视", na=False)]

df_out = (
    df_out.merge(df_rand, on=VAR_SUBJ, how="left")
          .merge(df_end, on=VAR_SUBJ, how="left")
)

# ── 7 格式化 ──

df_out = df_out.rename(columns={
    VAR_SUBJ:      VAR_OUT_SUBJ,
    VAR_RAND_NO:   VAR_OUT_RAND,
    VAR_VISIT:     VAR_OUT_VISIT,
    VAR_FORM:      VAR_OUT_FORM,
    VAR_ITEM:      VAR_OUT_ITEM,
    VAR_COMPLETED: VAR_OUT_COMPLETE,
})
df_out = df_out[OUTPUT_COLS]
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

export_to_excel_with_format(
    df_out,
    f"{output_listing_dir}/{LISTING_NAME}.xlsx",
    LISTING_NAME,
    LISTING_NAME,
)
