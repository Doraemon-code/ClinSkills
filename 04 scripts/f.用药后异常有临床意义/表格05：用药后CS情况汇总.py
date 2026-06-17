import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_sheet, load_first_dose, load_completion, load_rand
from utils.output_format import save_table_to_docx_threeline, export_to_excel_twoheader

# ── 列名集中管理 ──

# 导入列名
IMPORT_BASE     = ["受试者", "受试者状态", "访视名称", "页面名称"]
IMPORT_SIG      = ["病史名称", "不良事件名称", "其他,请说明"]
VAR_BASELINE_LB = "筛选/基线期（D-15～D-1）"

# 中间列名
VAR_SUBJ        = "受试者"
VAR_STATUS      = "受试者状态"
VAR_VISIT       = "访视名称"
VAR_PAGE        = "页面名称"
VAR_ASSESS_DATE = "检查日期"
VAR_ITEM        = "检查项"
VAR_RESULT      = "结果"
VAR_CS          = "临床意义"
VAR_DESC        = "异常描述"
VAR_UNIT        = "单位"
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
VAR_DESC_PRE     = "异常描述_首次用药前"
VAR_DESC_POST    = "异常描述_首次用药后"
VAR_CS_DESC_POST = "异常有临床意义，请描述_首次用药后"
VAR_COMPLETED    = "是否完成试验"

OUTPUT_COLS_BASE = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]
OUTPUT_COLS_VS   = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]
OUTPUT_COLS_DESC = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE, VAR_DESC_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST, VAR_DESC_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]
OUTPUT_COLS_LB   = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE, VAR_DESC_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST, VAR_DESC_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]

PREFIX_MAP = {VAR_MH: "MH:", VAR_AE: "AE:", VAR_OTHER: "其他:"}

GROUP_COLS = [VAR_SUBJ, VAR_PAGE, VAR_ITEM]


# ── 辅助函数 ──

def _pick_pre_rows_default(g):
    """基线期 CS 则整体排除；否则保留全部。"""
    if (g[VAR_CS] == "异常有临床意义").any():
        return g.iloc[0:0]
    return g


def _pick_pre_rows_lb(g):
    """基线期 CS 则整组排除，否则保留基线期行。"""
    base = g[g[VAR_VISIT].eq(VAR_BASELINE_LB)]
    if not base.empty:
        if (base[VAR_CS] == "异常有临床意义").any():
            return g.iloc[0:0]
        return base
    return g.iloc[0:0]


def _build_desc(df, desc_cols):
    return df[desc_cols].apply(
        lambda row: ";".join(
            f"{PREFIX_MAP.get(col, col)}{str(val).replace('√', '帕金森病')}"
            for col, val in row.items()
            if pd.notna(val) and str(val).strip() != ""
        ),
        axis=1,
    )


def _process_domain(df_raw, rename_map, pick_fn, output_cols,
                    date_col=None, extra_select=None,
                    extra_rename=None):
    """通用处理流程：归一化 → 筛选 → 分组 → 给药前/后 → 合并 → 格式化。"""
    df_raw = df_raw.rename(columns=rename_map)
    if date_col:
        df_raw[date_col] = pd.to_datetime(df_raw[date_col], errors="coerce")

    df_all = df_raw[
        (df_raw[VAR_STATUS] != "筛选失败") & df_raw[VAR_CS].notna()
    ].copy()

    df_all = (
        df_all.merge(load_first_dose().rename(columns={"首次用药日期": VAR_FIRST_DOSE}),
                     on=[VAR_SUBJ], how="left")
              .merge(load_completion(), on=[VAR_SUBJ], how="left")
              .merge(load_rand(cols=[VAR_SUBJ, "随机号"]), on=[VAR_SUBJ], how="left")
    )

    assess = date_col or VAR_ASSESS_DATE
    df_all[VAR_GROUP] = np.where(
        df_all[assess] <= df_all[VAR_FIRST_DOSE],
        "给药前检查", "给药后检查",
    )

    # 给药前
    df_pre = df_all[df_all[VAR_GROUP] == "给药前检查"]
    df_pre = df_pre.sort_values(by=[VAR_SUBJ, VAR_PAGE, VAR_ITEM, VAR_FIRST_DOSE])

    df_pre_gcols = df_pre[GROUP_COLS].copy()
    df_pre = df_pre.groupby(GROUP_COLS, group_keys=False).apply(pick_fn)
    df_pre = df_pre.join(df_pre_gcols).reset_index(drop=True)

    # 给药后：异常有临床意义
    df_post = df_all[
        (df_all[VAR_GROUP] == "给药后检查") & (df_all[VAR_CS] == "异常有临床意义")
    ].copy()
    df_post[VAR_CS_DESC] = _build_desc(df_post, [VAR_MH, VAR_AE, VAR_OTHER])

    select_cols = [VAR_SUBJ, VAR_VISIT, VAR_PAGE, assess,
                   VAR_ITEM, VAR_RESULT, VAR_CS, VAR_CS_DESC]
    if extra_select:
        select_cols.extend(extra_select)
    df_post = df_post[select_cols]

    # 合并
    df_merge = df_pre.merge(df_post, on=[VAR_SUBJ, VAR_PAGE, VAR_ITEM], how="left")
    df_merge = df_merge[~(df_merge[f"{VAR_RESULT}_x"].isna()
                          | df_merge[f"{VAR_RESULT}_y"].isna())]

    # 格式化列名
    rename_final = {
        f"{VAR_VISIT}_x":       VAR_VISIT_PRE,
        f"{VAR_VISIT}_y":       VAR_VISIT_POST,
        f"{VAR_RESULT}_x":      VAR_RESULT_PRE,
        f"{VAR_RESULT}_y":      VAR_RESULT_POST,
        f"{assess}_x":          VAR_DATE_PRE,
        f"{assess}_y":          VAR_DATE_POST,
        f"{VAR_CS}_x":          VAR_CS_PRE,
        f"{VAR_CS}_y":          VAR_CS_POST,
        VAR_CS_DESC:            VAR_CS_DESC_POST,
        VAR_PAGE:               VAR_FORM,
        VAR_SUBJ:               VAR_SCREEN_NO,
    }
    if extra_rename:
        rename_final.update(extra_rename)
    df_merge = df_merge.rename(columns=rename_final)

    df_merge[VAR_DATE_PRE]  = df_merge[VAR_DATE_PRE].dt.strftime("%Y-%m-%d")
    df_merge[VAR_DATE_POST] = df_merge[VAR_DATE_POST].dt.strftime("%Y-%m-%d")

    df_merge = df_merge[output_cols]
    df_merge.insert(0, "No.", range(1, len(df_merge) + 1))
    return df_merge


# ── 辅助：VS 宽表 → 长表 ──

def _melt_vs(df_raw):
    rename_map = {
        "异常，请描述.1": "异常，请描述_HR",
        "不良事件名称.1": "不良事件名称_HR",
        "病史名称.1":     "病史名称_HR",
        "其他,请说明.1":  "其他,请说明_HR",
        "异常，请描述.2": "异常，请描述_RESP",
        "不良事件名称.2": "不良事件名称_RESP",
        "病史名称.2":     "病史名称_RESP",
        "其他,请说明.2":  "其他,请说明_RESP",
        "异常，请描述.3": "异常，请描述_BP",
        "不良事件名称.3": "不良事件名称_BP",
        "病史名称.3":     "病史名称_BP",
        "其他,请说明.3":  "其他,请说明_BP",
    }
    df_raw = df_raw.rename(columns=rename_map)

    id_cols = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_PAGE, "检查日期"]
    groups = [
        ("体温",         "体温",     "体温-临床评估_TXT",         "异常，请描述",      "不良事件名称",     "病史名称",     "其他,请说明"),
        ("心率",         "HR",       "心率-临床评估_TXT",         "异常，请描述_HR",   "不良事件名称_HR",  "病史名称_HR",  "其他,请说明_HR"),
        ("呼吸",         "呼吸",     "呼吸-临床评估_TXT",         "异常，请描述_RESP", "不良事件名称_RESP","病史名称_RESP", "其他,请说明_RESP"),
        ("收缩压/舒张压", "收缩压",   "收缩压/舒张压-临床评估_TXT", "异常，请描述_BP",   "不良事件名称_BP",  "病史名称_BP",  "其他,请说明_BP"),
    ]

    parts = []
    for item_name, val_col, cs_col, desc_col, ae_col, mh_col, other_col in groups:
        part = df_raw[id_cols].copy()
        part[VAR_ITEM]   = item_name
        part[VAR_RESULT] = df_raw[val_col]
        part[VAR_CS]     = df_raw[cs_col]
        part[VAR_AE]     = df_raw[ae_col]
        part[VAR_MH]     = df_raw[mh_col]
        part[VAR_OTHER]  = df_raw[other_col]
        parts.append(part)

    df_long = pd.concat(parts, ignore_index=True)
    df_long = df_long[df_long[VAR_RESULT].notna() & (df_long[VAR_RESULT].astype(str).str.strip() != "")]
    return df_long


# ── 1 读取 & 处理：生命体征 -> VS ──

def process_vs():
    # VS 宽表有重复列名，load_sheet usecols 无法处理，故读全量再 melt
    df_raw = load_sheet("VS", cols=None)
    df_long = _melt_vs(df_raw)
    return _process_domain(
        df_long, rename_map={}, pick_fn=_pick_pre_rows_default,
        output_cols=OUTPUT_COLS_VS,
        date_col="检查日期",
    )


df_vs = process_vs()

# ── 1 读取 & 处理：体格检查 -> PE ──

def process_pe():
    IMPORT_PE = IMPORT_BASE + ["检查日期", "项目_TXT", "临床评估_TXT",
                               "异常，请描述_TXT", "其他,请说明"] + IMPORT_SIG
    df_raw = load_sheet("PE", cols=IMPORT_PE)
    rename_map = {
        "检查日期":         VAR_ASSESS_DATE,
        "项目_TXT":         VAR_ITEM,
        "临床评估_TXT":     VAR_CS,
        "异常，请描述_TXT": VAR_DESC,
        "其他,请说明":      VAR_OTHER,
    }
    df_raw = df_raw.rename(columns=rename_map)
    df_raw[VAR_RESULT] = df_raw[VAR_CS]
    return _process_domain(
        df_raw, rename_map={}, pick_fn=_pick_pre_rows_default,
        output_cols=OUTPUT_COLS_DESC,
        date_col=VAR_ASSESS_DATE,
        extra_select=[VAR_DESC],
        extra_rename={
            f"{VAR_DESC}_x": VAR_DESC_PRE,
            f"{VAR_DESC}_y": VAR_DESC_POST,
        },
    )


df_pe = process_pe()

# ── 1 读取 & 处理：12导联心电图 -> EG ──

def process_eg():
    IMPORT_EG = IMPORT_BASE + ["检查日期", "临床评估_TXT",
                               "如异常请详述", "其他,请说明"] + IMPORT_SIG
    df_raw = load_sheet("EG", cols=IMPORT_EG)
    rename_map = {
        "检查日期":     VAR_ASSESS_DATE,
        "临床评估_TXT": VAR_CS,
        "如异常请详述": VAR_DESC,
        "其他,请说明":  VAR_OTHER,
    }
    df_raw = df_raw.rename(columns=rename_map)
    df_raw[VAR_ITEM]   = df_raw[VAR_PAGE]
    df_raw[VAR_RESULT] = df_raw[VAR_CS]
    return _process_domain(
        df_raw, rename_map={}, pick_fn=_pick_pre_rows_default,
        output_cols=OUTPUT_COLS_DESC,
        date_col=VAR_ASSESS_DATE,
        extra_select=[VAR_DESC],
        extra_rename={
            f"{VAR_DESC}_x": VAR_DESC_PRE,
            f"{VAR_DESC}_y": VAR_DESC_POST,
        },
    )


df_eg = process_eg()

# ── 1 读取 & 处理：实验室检查 -> LB ──

def process_lb():
    IMPORT_LB = IMPORT_BASE + ["采样日期", "项目", "测定值", "临床评估_TXT",
                               "异常，请描述_TXT", "病史名称", "不良事件名称",
                               "其他,请说明"]
    sheets = ["LB_HEM", "LB_URI", "LB_HCG1", "LB_HCG2", "LB_CHEM",
              "LB_LFT", "LB_RFT", "LB_ELECT", "LB_FBG"]
    parts = []
    for s in sheets:
        try:
            parts.append(load_sheet(s, cols=IMPORT_LB))
        except ValueError:
            pass
    df_raw = pd.concat(parts, ignore_index=True)

    rename_map = {
        "项目":             VAR_ITEM,
        "测定值":           VAR_RESULT,
        "临床评估_TXT":     VAR_CS,
        "异常，请描述_TXT": VAR_DESC,
    }
    df_raw = df_raw.rename(columns=rename_map)
    return _process_domain(
        df_raw, rename_map={}, pick_fn=_pick_pre_rows_lb,
        output_cols=OUTPUT_COLS_LB,
        date_col="采样日期",
        extra_select=[VAR_DESC],
        extra_rename={
            f"{VAR_DESC}_x":     VAR_DESC_PRE,
            f"{VAR_DESC}_y":     VAR_DESC_POST,
        },
    )


df_lb = process_lb()

# ── 6 连接：合并所有检查域 ──

df_combined = pd.concat([df_vs, df_pe, df_eg, df_lb], ignore_index=True)
df_combined["temp_id"] = (
    df_combined[VAR_SCREEN_NO].astype(str)
    + df_combined[VAR_FORM].astype(str)
    + df_combined[VAR_ITEM].astype(str)
    + "_" + df_combined[VAR_VISIT_POST].astype(str)
)

# ── 8 输出：完整清单 ──

file_name = f"{output_path}/listing/表27 用药后检查异常有临床意义清单.xlsx"
export_to_excel_twoheader(
    df_combined.drop(columns=["temp_id"]), file_name,
    "表27 用药后检查异常有临床意义清单",
    title="表 27 用药后检查异常有临床意义清单",
    fixed_cols=["No.", "筛选号", "随机号", "表单名称", "检查项"],
    header_groups=[
        {"label": "首次用药前",
         "children": ["访视名称", "检查日期", "检查结果", "临床意义", "异常描述"]},
        {"label": "首次用药后",
         "children": ["访视名称", "检查日期", "检查结果", "临床意义", "异常描述",
                      "异常有临床意义，请描述"]},
    ],
    trailing_cols=["是否完成试验"],
    col_widths=[(0, 0, 5), (1, 2, 8), (3, 4, 12), (5, 6, 16),
                (7, 7, 5), (7, 14, 18), (15, 15, 30), (16, 16, 14)],
    subject_col="筛选号",
)

# ── 8 输出：汇总表 ──

summary = df_combined.groupby(VAR_FORM).agg(
    例数=(VAR_SCREEN_NO, "nunique"),
    例次=("temp_id", "nunique"),
).reset_index()

summary = summary.rename(columns={VAR_FORM: "检查类别"})
summary = summary.sort_values("检查类别").reset_index(drop=True)

total = pd.DataFrame({
    "检查类别": ["合计"],
    "例数":     [df_combined[VAR_SCREEN_NO].nunique()],
    "例次":     [df_combined["temp_id"].nunique()],
})
summary = pd.concat([summary, total], ignore_index=True)

notes = ['注：用药后检查异常有临床意义详细清单见附件：“用药后检查异常有临床意义清单”。']
save_table_to_docx_threeline(
    summary,
    f"{output_path}/table/表27 用药后检查异常有临床意义整体情况.docx",
    "表27 用药后检查异常有临床意义整体情况",
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
)

print(f"清单：{file_name}")
print(f"汇总：{output_path}/table/表27 用药后检查异常有临床意义整体情况.docx")
