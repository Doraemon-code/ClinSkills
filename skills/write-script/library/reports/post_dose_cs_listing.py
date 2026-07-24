# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 用药后异常有临床意义清单（xlsx 双层表头）：读取检查表单数据，
#       以首次用药日期为界分用药前/后，筛选用药后异常有临床意义(CS)记录，
#       与用药前记录合并输出用药前后对比清单。支持水平宽表(melt)和垂直长表
#       两种数据格式。
# @tags 用药后,临床意义,CS,首次用药,双层表头,xlsx,清单,给药前后
# @config LISTING_NAME, DOMAIN_CONFIG, FORM_EC/FORM_RAND/FORM_END,
#         IMPORT_* 列名

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_listing_dir
from utils.output_format import export_to_excel_twoheader
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID、字段名、CS 解码值均为项目特异。

LISTING_NAME = "用药后检查异常有临床意义清单"

FORM_EC   = "EC_ED"      # 给药记录表单
FORM_END  = "DS_END"     # 研究结束表单
FORM_RAND = "DS_RAND"    # 随机表单

# 首次用药日期列名
IMPORT_DOSE_DATE = "开始日期"

# 完成状态与随机号列名
IMPORT_COMPLETED = "受试者是否完成试验_TXT"
IMPORT_RAND_NO   = "随机号"

# CS 异常值判断
CS_ABNORMAL_VAL = "异常有临床意义"

# 排除的受试者状态
EXCLUDE_STATUS = "筛选失败"

# ── 领域配置：定义检查域的数据读取与处理方式 ──
# type: "horizontal"（宽表，每项一列需 melt）或 "vertical"（长表，每行一项）
#
# horizontal 格式:
#   { "type": "horizontal", "sheet": "VS",
#     "system_cols": [受试者, 受试者状态, 访视名称, 页面名称],
#     "date_col": "检查日期",
#     "item_groups": [(输出项名, 结果列, 临床评估列, [描述列], [AE列, MH列, 其他列]), ...] }
#
# vertical 格式:
#   { "type": "vertical", "sheet": "PE",
#     "system_cols": [...], "date_col": "检查日期",
#     "item_col": "项目_TXT", "result_col": "结果列",
#     "cs_col": "临床评估_TXT", "desc_cols": ["异常，请描述_TXT"],
#     "sig_cols": ["病史名称", "不良事件名称", "其他,请说明"] }

DOMAIN_CONFIG = {
    "type": "horizontal",
    "sheet": "VS",
    "date_col": "检查日期",
    "item_groups": [
        ("体温",         "体温",     "体温-临床评估_TXT",         []),
        ("心率",         "HR",       "心率-临床评估_TXT",         []),
        ("呼吸",         "呼吸",     "呼吸-临床评估_TXT",         []),
        ("收缩压",       "收缩压",   "收缩压/舒张压-临床评估_TXT", []),
    ],
    "sig_cols": ["病史名称", "不良事件名称", "其他,请说明"],
}

# ── 列名集中管理 ──

VAR_STATUS    = "受试者状态"
VAR_VISIT     = "访视名称"
VAR_FORM      = "页面名称"
VAR_ASSESS_DATE = "评估日期"
VAR_ITEM      = "检查项"
VAR_RESULT    = "结果"
VAR_CS        = "临床意义"
VAR_DESC      = "异常描述"
VAR_FIRST_DOSE = "首次用药日期"
VAR_GROUP     = "分组"
VAR_MH        = "病史名称"
VAR_AE        = "不良事件名称"
VAR_OTHER     = "其他请说明"
VAR_CS_DESC   = "异常有临床意义，请描述"

VAR_SCREEN_NO   = "筛选号"
VAR_RAND_NO     = "随机号"
VAR_VISIT_PRE   = "访视名称_首次用药前"
VAR_VISIT_POST  = "访视名称_首次用药后"
VAR_DATE_PRE    = "检查日期_首次用药前"
VAR_DATE_POST   = "检查日期_首次用药后"
VAR_RESULT_PRE  = "检查结果_首次用药前"
VAR_RESULT_POST = "检查结果_首次用药后"
VAR_CS_PRE      = "临床意义_首次用药前"
VAR_CS_POST     = "临床意义_首次用药后"
VAR_DESC_PRE    = "异常描述_首次用药前"
VAR_DESC_POST   = "异常描述_首次用药后"
VAR_CS_DESC_POST = "异常有临床意义，请描述_首次用药后"
VAR_COMPLETED   = "是否完成试验"

PREFIX_MAP = {"病史名称": "MH:", "不良事件名称": "AE:", "其他请说明": "其他:"}

GROUP_COLS = [VAR_SUBJ, VAR_FORM, VAR_ITEM]


# ── 辅助：构建描述文本 ──

def _build_desc(df, desc_cols):
    return df[desc_cols].apply(
        lambda row: ";".join(
            f"{PREFIX_MAP.get(col, col)}{str(val)}"
            for col, val in row.items()
            if pd.notna(val) and str(val).strip() != ""
        ),
        axis=1,
    )


# ── 辅助：通用处理流程 ──

def _process_domain(df_raw, date_col, has_desc=False):
    """通用处理：分组 → 给药前/后筛选 → 合并 → 格式化。"""
    df_raw[date_col] = pd.to_datetime(df_raw[date_col], errors="coerce")

    df_all = df_raw[
        (df_raw[VAR_STATUS] != EXCLUDE_STATUS) & df_raw[VAR_CS].notna()
    ].copy()

    df_all = (
        df_all.merge(_df_first_dose, on=VAR_SUBJ, how="left")
              .merge(_df_completion, on=VAR_SUBJ, how="left")
              .merge(_df_rand,       on=VAR_SUBJ, how="left")
    )

    assess = date_col
    df_all[VAR_GROUP] = np.where(
        df_all[assess] <= df_all[VAR_FIRST_DOSE],
        "给药前检查", "给药后检查",
    )

    # 给药前
    df_pre = df_all[df_all[VAR_GROUP] == "给药前检查"]
    df_pre = df_pre.sort_values(by=[VAR_SUBJ, VAR_FORM, VAR_ITEM, VAR_FIRST_DOSE])
    df_pre_gcols = df_pre[GROUP_COLS].copy()

    def _pick_pre(g):
        if (g[VAR_CS] == CS_ABNORMAL_VAL).any():
            return g.iloc[0:0]
        return g

    df_pre = df_pre.groupby(GROUP_COLS, group_keys=False).apply(_pick_pre)
    df_pre = df_pre.join(df_pre_gcols).reset_index(drop=True)

    # 给药后：异常有临床意义
    df_post = df_all[
        (df_all[VAR_GROUP] == "给药后检查") & (df_all[VAR_CS] == CS_ABNORMAL_VAL)
    ].copy()

    desc_cols = [VAR_MH, VAR_AE, VAR_OTHER]
    existing_desc = [c for c in desc_cols if c in df_post.columns]
    if existing_desc:
        df_post[VAR_CS_DESC] = _build_desc(df_post, existing_desc)

    select_cols = [VAR_SUBJ, VAR_VISIT, VAR_FORM, assess,
                   VAR_ITEM, VAR_RESULT, VAR_CS, VAR_CS_DESC]
    if has_desc and VAR_DESC in df_post.columns:
        select_cols.append(VAR_DESC)
    df_post = df_post[select_cols]

    # 合并
    df_merge = df_pre.merge(df_post, on=[VAR_SUBJ, VAR_FORM, VAR_ITEM], how="left")
    df_merge = df_merge[
        ~(df_merge[f"{VAR_RESULT}_x"].isna() | df_merge[f"{VAR_RESULT}_y"].isna())
    ]

    # 格式化列名
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
    if has_desc:
        rename_final[f"{VAR_DESC}_x"] = VAR_DESC_PRE
        rename_final[f"{VAR_DESC}_y"] = VAR_DESC_POST

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

# ── 1 读取 & 处理：领域数据 ──

cfg = DOMAIN_CONFIG
id_cols = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM]

if cfg["type"] == "horizontal":
    # 宽表：读取每个 item_group 对应的列
    df_raw = load_sheet(cfg["sheet"], usecols=None)

    parts = []
    for item_name, val_col, cs_col, desc_cols in cfg["item_groups"]:
        part = df_raw[id_cols + [cfg["date_col"]]].copy()
        part[VAR_ITEM] = item_name
        part[VAR_RESULT] = df_raw[val_col] if val_col in df_raw.columns else np.nan
        part[VAR_CS]     = df_raw[cs_col] if cs_col in df_raw.columns else np.nan
        for i, dc in enumerate(desc_cols):
            col_name = VAR_DESC if i == 0 else f"{VAR_DESC}_{i}"
            part[col_name] = df_raw[dc] if dc in df_raw.columns else np.nan
        if "sig_cols" in cfg:
            for sc in cfg["sig_cols"]:
                if sc in df_raw.columns:
                    part[sc] = df_raw[sc]
        parts.append(part)

    df_long = pd.concat(parts, ignore_index=True)
    df_long = df_long[df_long[VAR_RESULT].notna() & (df_long[VAR_RESULT].astype(str).str.strip() != "")]
    df_out = _process_domain(df_long, cfg["date_col"], has_desc=bool(desc_cols))

elif cfg["type"] == "vertical":
    usecols = id_cols + [cfg["date_col"], cfg["item_col"], cfg.get("result_col", ""),
                         cfg["cs_col"]] + cfg.get("desc_cols", []) + cfg.get("sig_cols", [])
    usecols = [c for c in usecols if c]
    df_raw = load_sheet(cfg["sheet"], usecols=usecols)
    rename_map = {
        cfg["date_col"]:   VAR_ASSESS_DATE,
        cfg["item_col"]:   VAR_ITEM,
        cfg["cs_col"]:     VAR_CS,
    }
    if cfg.get("result_col"):
        rename_map[cfg["result_col"]] = VAR_RESULT
    if cfg.get("desc_cols"):
        rename_map[cfg["desc_cols"][0]] = VAR_DESC
    if cfg.get("sig_cols"):
        for sc in cfg["sig_cols"]:
            if sc in rename_map:
                continue
    df_raw = df_raw.rename(columns=rename_map)
    if VAR_RESULT not in df_raw.columns:
        df_raw[VAR_RESULT] = df_raw[VAR_CS]
    has_desc = bool(cfg.get("desc_cols"))
    df_out = _process_domain(df_raw, cfg.get("date_col", VAR_ASSESS_DATE), has_desc=has_desc)


# ── 7 格式化：选取输出列 ──

base_cols = [
    VAR_SCREEN_NO, VAR_RAND_NO, "表单名称", VAR_ITEM,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST,
    VAR_CS_DESC_POST, VAR_COMPLETED,
]
desc_extra = [VAR_DESC_PRE, VAR_DESC_POST]
has_desc_out = VAR_DESC_PRE in df_out.columns

output_cols = base_cols[:4] + (desc_extra[:1] if has_desc_out else []) + base_cols[4:10] + (desc_extra[1:] if has_desc_out else []) + base_cols[10:]

# 确保所有列存在
output_cols = [c for c in output_cols if c in df_out.columns]
df_out = df_out[output_cols]
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

export_to_excel_twoheader(
    df_out,
    f"{output_listing_dir}/{LISTING_NAME}.xlsx",
    LISTING_NAME,
    title=LISTING_NAME,
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
