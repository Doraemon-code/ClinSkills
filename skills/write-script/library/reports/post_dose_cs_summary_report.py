# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 用药后CS情况汇总：合并多个检查域（生命体征/体格检查/心电图/
#       实验室检查）的用药后异常有临床意义记录，输出汇总 xlsx 清单 +
#       docx 三线表（按检查类别统计例数/例次）。
# @tags 用药后,临床意义,CS,汇总,多域合并,双层表头,DMR
# @config REPORT_NAME, DOMAINS, FORM_EC/FORM_RAND/FORM_END

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_listing_dir, output_table_dir
from utils.output_format import export_to_excel_twoheader, save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──

REPORT_NAME = "用药后检查异常有临床意义整体情况"

FORM_EC   = "EC_ED"
FORM_END  = "DS_END"
FORM_RAND = "DS_RAND"

IMPORT_DOSE_DATE = "开始日期"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"
IMPORT_RAND_NO   = "随机号"

CS_ABNORMAL_VAL = "异常有临床意义"
EXCLUDE_STATUS  = "筛选失败"
BASELINE_VISIT  = "筛选/基线期（D-15～D-1）"

# ── 列名集中管理 ──

VAR_STATUS     = "受试者状态"
VAR_VISIT      = "访视名称"
VAR_FORM       = "页面名称"
VAR_ASSESS_DATE = "评估日期"
VAR_ITEM       = "检查项"
VAR_RESULT     = "结果"
VAR_CS         = "临床意义"
VAR_DESC       = "异常描述"
VAR_FIRST_DOSE = "首次用药日期"
VAR_GROUP      = "分组"
VAR_MH         = "病史名称"
VAR_AE         = "不良事件名称"
VAR_OTHER      = "其他请说明"
VAR_CS_DESC    = "异常有临床意义，请描述"

VAR_SCREEN_NO    = "筛选号"
VAR_RAND_NO      = "随机号"
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

PREFIX_MAP = {VAR_MH: "MH:", VAR_AE: "AE:", VAR_OTHER: "其他:"}
GROUP_COLS = [VAR_SUBJ, VAR_FORM, VAR_ITEM]


# ── 辅助 ──

def _build_desc(df, desc_cols):
    return df[desc_cols].apply(
        lambda row: ";".join(
            f"{PREFIX_MAP.get(col, col)}{str(val)}"
            for col, val in row.items()
            if pd.notna(val) and str(val).strip() != ""
        ),
        axis=1,
    )


def _pick_pre_rows(g):
    if (g[VAR_CS] == CS_ABNORMAL_VAL).any():
        return g.iloc[0:0]
    return g


def _pick_pre_rows_lb(g):
    base = g[g[VAR_VISIT].eq(BASELINE_VISIT)]
    if not base.empty:
        if (base[VAR_CS] == CS_ABNORMAL_VAL).any():
            return g.iloc[0:0]
        return base
    return g.iloc[0:0]


def _process_domain(df_raw, rename_map, pick_fn, date_col=None,
                    extra_select=None, extra_rename=None):
    df_raw = df_raw.rename(columns=rename_map)
    if date_col:
        df_raw[date_col] = pd.to_datetime(df_raw[date_col], errors="coerce")

    df_all = df_raw[
        (df_raw[VAR_STATUS] != EXCLUDE_STATUS) & df_raw[VAR_CS].notna()
    ].copy()

    df_all = (
        df_all.merge(_df_first_dose, on=VAR_SUBJ, how="left")
              .merge(_df_completion, on=VAR_SUBJ, how="left")
              .merge(_df_rand,       on=VAR_SUBJ, how="left")
    )

    assess = date_col or VAR_ASSESS_DATE
    df_all[VAR_GROUP] = np.where(
        df_all[assess] <= df_all[VAR_FIRST_DOSE],
        "给药前检查", "给药后检查",
    )

    df_pre = df_all[df_all[VAR_GROUP] == "给药前检查"]
    df_pre = df_pre.sort_values(by=[VAR_SUBJ, VAR_FORM, VAR_ITEM, VAR_FIRST_DOSE])
    df_pre_gcols = df_pre[GROUP_COLS].copy()
    df_pre = df_pre.groupby(GROUP_COLS, group_keys=False).apply(pick_fn)
    df_pre = df_pre.join(df_pre_gcols).reset_index(drop=True)

    df_post = df_all[
        (df_all[VAR_GROUP] == "给药后检查") & (df_all[VAR_CS] == CS_ABNORMAL_VAL)
    ].copy()
    desc_cols = [VAR_MH, VAR_AE, VAR_OTHER]
    existing_desc = [c for c in desc_cols if c in df_post.columns]
    if existing_desc:
        df_post[VAR_CS_DESC] = _build_desc(df_post, existing_desc)

    select_cols = [VAR_SUBJ, VAR_VISIT, VAR_FORM, assess,
                   VAR_ITEM, VAR_RESULT, VAR_CS, VAR_CS_DESC]
    if extra_select:
        select_cols.extend(extra_select)
    df_post = df_post[select_cols]

    df_merge = df_pre.merge(df_post, on=[VAR_SUBJ, VAR_FORM, VAR_ITEM], how="left")
    df_merge = df_merge[
        ~(df_merge[f"{VAR_RESULT}_x"].isna() | df_merge[f"{VAR_RESULT}_y"].isna())
    ]

    rename_final = {
        f"{VAR_VISIT}_x":  VAR_VISIT_PRE,
        f"{VAR_VISIT}_y":  VAR_VISIT_POST,
        f"{VAR_RESULT}_x": VAR_RESULT_PRE,
        f"{VAR_RESULT}_y": VAR_RESULT_POST,
        f"{assess}_x":     VAR_DATE_PRE,
        f"{assess}_y":     VAR_DATE_POST,
        f"{VAR_CS}_x":     VAR_CS_PRE,
        f"{VAR_CS}_y":     VAR_CS_POST,
        VAR_CS_DESC:       VAR_CS_DESC_POST,
        VAR_FORM:          "表单名称",
        VAR_SUBJ:          VAR_SCREEN_NO,
    }
    if extra_rename:
        rename_final.update(extra_rename)
    df_merge = df_merge.rename(columns=rename_final)
    df_merge[VAR_DATE_PRE]  = df_merge[VAR_DATE_PRE].dt.strftime("%Y-%m-%d")
    df_merge[VAR_DATE_POST] = df_merge[VAR_DATE_POST].dt.strftime("%Y-%m-%d")
    return df_merge


# ── 1 读取：公共数据 ──

df_ec = load_sheet(FORM_EC, [VAR_SUBJ, IMPORT_DOSE_DATE])
df_ec[IMPORT_DOSE_DATE] = pd.to_datetime(df_ec[IMPORT_DOSE_DATE], errors="coerce")
df_ec = df_ec.sort_values(by=[VAR_SUBJ, IMPORT_DOSE_DATE]).dropna(subset=[IMPORT_DOSE_DATE])
_df_first_dose = df_ec.groupby(VAR_SUBJ)[IMPORT_DOSE_DATE].first().reset_index()
_df_first_dose = _df_first_dose.rename(columns={IMPORT_DOSE_DATE: VAR_FIRST_DOSE})

_df_completion = load_sheet(FORM_END, [VAR_SUBJ, IMPORT_COMPLETED])
_df_completion = _df_completion.rename(columns={IMPORT_COMPLETED: VAR_COMPLETED})

_df_rand = load_sheet(FORM_RAND, [VAR_SUBJ, IMPORT_RAND_NO])

# ── 读取 & 处理各领域 ──

IMPORT_BASE = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM]
IMPORT_SIG  = [VAR_MH, VAR_AE, VAR_OTHER]
all_dfs = []

# VS: 水平宽表 melt
df_vs_raw = load_sheet("VS", usecols=None)
df_vs_raw = df_vs_raw.rename(columns={
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
})
id_cols = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM, "检查日期"]
vs_groups = [
    ("体温",         "体温",     "体温-临床评估_TXT",         "异常，请描述",      "不良事件名称",     "病史名称",     "其他,请说明"),
    ("心率",         "HR",       "心率-临床评估_TXT",         "异常，请描述_HR",   "不良事件名称_HR",  "病史名称_HR",  "其他,请说明_HR"),
    ("呼吸",         "呼吸",     "呼吸-临床评估_TXT",         "异常，请描述_RESP", "不良事件名称_RESP","病史名称_RESP", "其他,请说明_RESP"),
    ("收缩压/舒张压", "收缩压",   "收缩压/舒张压-临床评估_TXT", "异常，请描述_BP",   "不良事件名称_BP",  "病史名称_BP",  "其他,请说明_BP"),
]
vs_parts = []
for item_name, val_col, cs_col, desc_col, ae_col, mh_col, other_col in vs_groups:
    part = df_vs_raw[id_cols].copy()
    part[VAR_ITEM]  = item_name
    part[VAR_RESULT] = df_vs_raw[val_col]
    part[VAR_CS]     = df_vs_raw[cs_col]
    part[VAR_AE]     = df_vs_raw[ae_col]
    part[VAR_MH]     = df_vs_raw[mh_col]
    part[VAR_OTHER]  = df_vs_raw[other_col]
    vs_parts.append(part)
df_vs = pd.concat(vs_parts, ignore_index=True)
df_vs = df_vs[df_vs[VAR_RESULT].notna() & (df_vs[VAR_RESULT].astype(str).str.strip() != "")]
df_vs = _process_domain(df_vs, rename_map={}, pick_fn=_pick_pre_rows, date_col="检查日期")
all_dfs.append(df_vs)

# PE: 体格检查
df_pe = load_sheet("PE", usecols=IMPORT_BASE + ["检查日期", "项目_TXT", "临床评估_TXT",
                                                 "异常，请描述_TXT", "其他,请说明"] + IMPORT_SIG)
df_pe = df_pe.rename(columns={
    "检查日期": VAR_ASSESS_DATE, "项目_TXT": VAR_ITEM,
    "临床评估_TXT": VAR_CS, "异常，请描述_TXT": VAR_DESC,
    "其他,请说明": VAR_OTHER,
})
df_pe[VAR_RESULT] = df_pe[VAR_CS]
df_pe = _process_domain(df_pe, rename_map={}, pick_fn=_pick_pre_rows,
                        date_col=VAR_ASSESS_DATE, extra_select=[VAR_DESC],
                        extra_rename={f"{VAR_DESC}_x": VAR_DESC_PRE, f"{VAR_DESC}_y": VAR_DESC_POST})
all_dfs.append(df_pe)

# EG: 心电图
df_eg = load_sheet("EG", usecols=IMPORT_BASE + ["检查日期", "临床评估_TXT",
                                                 "如异常请详述", "其他,请说明"] + IMPORT_SIG)
df_eg = df_eg.rename(columns={
    "检查日期": VAR_ASSESS_DATE, "临床评估_TXT": VAR_CS,
    "如异常请详述": VAR_DESC, "其他,请说明": VAR_OTHER,
})
df_eg[VAR_ITEM]   = df_eg[VAR_FORM]
df_eg[VAR_RESULT] = df_eg[VAR_CS]
df_eg = _process_domain(df_eg, rename_map={}, pick_fn=_pick_pre_rows,
                        date_col=VAR_ASSESS_DATE, extra_select=[VAR_DESC],
                        extra_rename={f"{VAR_DESC}_x": VAR_DESC_PRE, f"{VAR_DESC}_y": VAR_DESC_POST})
all_dfs.append(df_eg)

# LB: 实验室检查
LB_SHEETS = ["LB_HEM", "LB_URI", "LB_HCG1", "LB_HCG2", "LB_CHEM"]
lb_parts = []
for s in LB_SHEETS:
    try:
        lb_parts.append(load_sheet(s, usecols=IMPORT_BASE + ["采样日期", "项目.1", "测定值",
                                     "临床评估_TXT", "异常，请描述_TXT"] + IMPORT_SIG))
    except ValueError:
        pass
df_lb = pd.concat(lb_parts, ignore_index=True) if lb_parts else pd.DataFrame()
if len(df_lb) > 0:
    df_lb = df_lb.rename(columns={
        "采样日期": VAR_ASSESS_DATE, "项目.1": VAR_ITEM, "测定值": VAR_RESULT,
        "临床评估_TXT": VAR_CS, "异常，请描述_TXT": VAR_DESC,
    })
    df_lb = _process_domain(df_lb, rename_map={}, pick_fn=_pick_pre_rows_lb,
                            date_col=VAR_ASSESS_DATE, extra_select=[VAR_DESC],
                            extra_rename={f"{VAR_DESC}_x": VAR_DESC_PRE, f"{VAR_DESC}_y": VAR_DESC_POST})
    all_dfs.append(df_lb)

# ── 6 连接：合并所有域 ──

df_combined = pd.concat(all_dfs, ignore_index=True)
df_combined["temp_id"] = (
    df_combined[VAR_SCREEN_NO].astype(str)
    + df_combined["表单名称"].astype(str)
    + df_combined[VAR_ITEM].astype(str)
    + "_" + df_combined[VAR_VISIT_POST].astype(str)
)

# ── 8 输出：完整清单 ──

output_cols = [c for c in df_combined.columns if c != "temp_id"]
df_listing = df_combined[output_cols]
df_listing.insert(0, "No.", range(1, len(df_listing) + 1))

export_to_excel_twoheader(
    df_listing,
    f"{output_listing_dir}/{REPORT_NAME}.xlsx",
    REPORT_NAME,
    title=REPORT_NAME,
    fixed_cols=["No.", "筛选号", "随机号", "表单名称", "检查项"],
    header_groups=[
        {"label": "首次用药前",
         "children": [c for c in output_cols if c.endswith("_首次用药前")]},
        {"label": "首次用药后",
         "children": [c for c in output_cols if c.endswith("_首次用药后")]},
    ],
    trailing_cols=["是否完成试验"],
    subject_col="筛选号",
)

# ── 8 输出：汇总表 ──

summary = df_combined.groupby("表单名称").agg(
    例数=(VAR_SCREEN_NO, "nunique"),
    例次=("temp_id", "nunique"),
).reset_index()

summary = summary.rename(columns={"表单名称": "检查类别"})
summary = summary.sort_values("检查类别").reset_index(drop=True)

total = pd.DataFrame({
    "检查类别": ["合计"],
    "例数": [df_combined[VAR_SCREEN_NO].nunique()],
    "例次": [df_combined["temp_id"].nunique()],
})
summary = pd.concat([summary, total], ignore_index=True)

notes = ["注：用药后检查异常有临床意义详细清单见附件。"]
save_table_to_docx_threeline(
    summary,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
)
