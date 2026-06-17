import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_sheet, load_first_dose, load_completion, load_rand
from utils.output_format import export_to_excel_twoheader

# ── 列名集中管理 ──

# 导入列名
VAR_SUBJ   = "受试者"
VAR_STATUS = "受试者状态"
VAR_VISIT  = "访视名称"
VAR_PAGE   = "页面名称"
IMPORT_BASE = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_PAGE]
IMPORT_LB   = IMPORT_BASE + ["采样日期", "项目.1", "测定值", "临床评估_TXT",
                             "异常，请描述_TXT", "病史名称", "不良事件名称", "其他,请说明",
                             "下限", "上限", "单位"]

# 中间列名
VAR_ASSESS_DATE = "采样日期"
VAR_ITEM        = "项目"
VAR_RESULT      = "测定值"
VAR_CS          = "临床评估"
VAR_DESC        = "异常描述"
VAR_FIRST_DOSE  = "首次用药日期"
VAR_GROUP       = "分组"
VAR_MH          = "病史名称"
VAR_AE          = "不良事件名称"
VAR_OTHER       = "其他,请说明"
VAR_CS_DESC     = "异常有临床意义，请描述"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_RAND_NO      = "随机号"
VAR_FORM         = "表单名称"
VAR_VISIT_PRE    = "访视名称_首次用药前"
VAR_VISIT_POST   = "访视名称_首次用药后"
VAR_DATE_PRE     = "检查日期_首次用药前"
VAR_DATE_POST    = "检查日期_首次用药后"
VAR_RESULT_PRE   = "检查结果_首次用药前"
VAR_RESULT_POST  = "检查结果_首次用药后"
VAR_CS_PRE       = "临床意义_首次用药前"
VAR_CS_POST      = "临床意义_首次用药后"
VAR_CS_DESC_POST = "异常有临床意义，请描述_首次用药后"
VAR_COMPLETED    = "是否完成试验"

OUTPUT_COLS = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM,
    "正常值范围下限", "正常值范围上限", "单位",
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]

_RENAME_MAP = {
    "采样日期":       VAR_ASSESS_DATE,
    "项目.1":         VAR_ITEM,
    "临床评估_TXT":   VAR_CS,
    "异常，请描述_TXT": VAR_DESC,
    "测定值":         VAR_RESULT,
    "下限":           "正常值范围下限",
    "上限":           "正常值范围上限",
}
PREFIX_MAP = {VAR_MH: "MH:", VAR_AE: "AE:", VAR_OTHER: "其他:"}

# ── 1 读取 ──
df_hem   = load_sheet("LB_HEM",   cols=IMPORT_LB)
df_chem  = load_sheet("LB_CHEM",  cols=IMPORT_LB)
df_uri   = load_sheet("LB_URI",   cols=IMPORT_LB)
df_hcg1  = load_sheet("LB_HCG1",  cols=IMPORT_LB)
df_hcg2  = load_sheet("LB_HCG2",  cols=IMPORT_LB)

# ── 2 归一化 ──
for _df in [df_hem, df_chem, df_uri, df_hcg1, df_hcg2]:
    _df.rename(columns=_RENAME_MAP, inplace=True)

df_lb = pd.concat([df_hem, df_chem, df_uri, df_hcg1, df_hcg2], ignore_index=True)
df_lb[VAR_ASSESS_DATE] = pd.to_datetime(df_lb[VAR_ASSESS_DATE], errors="coerce")

# ── 3 筛选：排除筛选失败 + 有临床评估 ──
df_all = df_lb[
    (df_lb[VAR_STATUS] != "筛选失败") & df_lb[VAR_CS].notna()
].copy()

# ── 6 连接：首次用药日期、完成状态、随机号 ──
df_all = (
    df_all.merge(load_first_dose().rename(columns={"首次用药日期": VAR_FIRST_DOSE}),
                 on=[VAR_SUBJ], how="left")
          .merge(load_completion(), on=[VAR_SUBJ], how="left")
          .merge(load_rand(cols=["受试者", "随机号"]), on=[VAR_SUBJ], how="left")
)

# ── 5 派生：给药前/后分组 ──
df_all[VAR_GROUP] = np.where(
    df_all[VAR_ASSESS_DATE] <= df_all[VAR_FIRST_DOSE],
    "给药前检查", "给药后检查",
)

# ── 3 筛选：给药前 — 基线期有 CS 则整组排除，否则取筛选期非 CS ──
df_pre = df_all[df_all[VAR_GROUP] == "给药前检查"]
df_pre = df_pre.sort_values(by=[VAR_SUBJ, VAR_PAGE, VAR_ITEM, VAR_FIRST_DOSE])

GROUP_COLS = [VAR_SUBJ, VAR_PAGE, VAR_ITEM]

VAR_BASELINE = "筛选/基线期（D-15～D-1）"

def _pick_pre_rows(g):
    """基线期 CS 则整组排除，否则保留基线期行。"""
    base = g[g[VAR_VISIT].eq(VAR_BASELINE)]
    if not base.empty:
        if (base[VAR_CS] == "异常有临床意义").any():
            return g.iloc[0:0]
        return base
    return g.iloc[0:0]

df_pre_group_cols = df_pre[GROUP_COLS].copy()
df_pre = (
    df_pre.groupby(GROUP_COLS, group_keys=False)
          .apply(_pick_pre_rows)
)
df_pre = df_pre.join(df_pre_group_cols).reset_index(drop=True)

# ── 5 派生：给药后 — 异常有临床意义描述文本 ──
df_post = df_all[
    (df_all[VAR_GROUP] == "给药后检查") & (df_all[VAR_CS] == "异常有临床意义")
].copy()

desc_cols = [VAR_MH, VAR_AE, VAR_OTHER]
df_post[VAR_CS_DESC] = df_post[desc_cols].apply(
    lambda row: ";".join(
        f"{PREFIX_MAP.get(col, col)}{str(val).replace('√', '帕金森病')}"
        for col, val in row.items()
        if pd.notna(val) and str(val).strip() != ""
    ),
    axis=1,
)

df_post = df_post[[VAR_SUBJ, VAR_VISIT, VAR_PAGE, VAR_ASSESS_DATE,
                   VAR_ITEM, VAR_RESULT, VAR_CS, VAR_DESC, VAR_CS_DESC]]

# ── 6 连接：用药前 + 用药后 ──
df_merge = df_pre.merge(df_post, on=[VAR_SUBJ, VAR_PAGE, VAR_ITEM], how="left")
df_merge = df_merge[~(df_merge[f"{VAR_RESULT}_x"].isna() | df_merge[f"{VAR_RESULT}_y"].isna())]

# ── 7 格式化 ──
df_merge = df_merge.rename(columns={
    f"{VAR_VISIT}_x":       VAR_VISIT_PRE,
    f"{VAR_VISIT}_y":       VAR_VISIT_POST,
    f"{VAR_RESULT}_x":      VAR_RESULT_PRE,
    f"{VAR_RESULT}_y":      VAR_RESULT_POST,
    f"{VAR_ASSESS_DATE}_x": VAR_DATE_PRE,
    f"{VAR_ASSESS_DATE}_y": VAR_DATE_POST,
    f"{VAR_CS}_x":          VAR_CS_PRE,
    f"{VAR_CS}_y":          VAR_CS_POST,
    VAR_CS_DESC:            VAR_CS_DESC_POST,
    VAR_PAGE:               VAR_FORM,
    VAR_SUBJ:               VAR_SCREEN_NO,
})

df_merge[VAR_DATE_PRE]  = df_merge[VAR_DATE_PRE].dt.strftime("%Y-%m-%d")
df_merge[VAR_DATE_POST] = df_merge[VAR_DATE_POST].dt.strftime("%Y-%m-%d")

df_merge = df_merge[OUTPUT_COLS]
df_merge.insert(0, "No.", range(1, len(df_merge) + 1))

# ── 8 输出 ──
file_name = f"{output_path}/listing/表39-1 实验室检查用药后检查异常有临床意义清单.xlsx"
export_to_excel_twoheader(
    df_merge, file_name, "表39-1 用药后检查异常有临床意义清单",
    title="表 39-1 用药后检查异常有临床意义清单",
    fixed_cols=['No.', '筛选号', '随机号', '表单名称', '检查项', '正常值范围下限', '正常值范围上限', '单位'],
    header_groups=[
        {'label': '首次用药前', 'children': ['访视名称', '检查日期', '检查结果', '临床意义']},
        {'label': '首次用药后', 'children': ['访视名称', '检查日期', '检查结果', '临床意义', '异常有临床意义，请描述']},
    ],
    trailing_cols=['是否完成试验'],
    col_widths=[(0, 0, 5), (1, 2, 8), (3, 4, 12), (5, 6, 16), (7, 7, 5), (7, 15, 18), (16, 16, 30), (17, 17, 14)],
    subject_col='筛选号',
)
