# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 超窗情况汇总三线表：汇总各类超窗（疗效/安全性/其他）的例次与例数，
#       按页面分组统计最小/最大超窗时间，按固定顺序输出带层级缩进的汇总表。
# @tags 超窗,汇总,疗效,安全性,其他,层级缩进,DMR,三线表
# @config REPORT_NAME, SOURCE_GROUPS, TIMEWIN_PATH, FORM_RAND, PAGE_ORDER

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import timewin_path, output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──

REPORT_NAME = "超窗情况汇总"

FORM_RAND = "DS_RAND"

TIMEWIN_SHEET   = "时间窗"
TIMEWIN_CAT_COL  = "类别"
TIMEWIN_VISIT_COL = "访视名称"
TIMEWIN_LOWER_COL = "时间窗下限"
TIMEWIN_UPPER_COL = "时间窗上限"

# 各类别表单来源定义
# { 类别标签: { "sources": [(sheet, date_col, page_name_or_None), ...],
#               "dedup_sv": bool  # 是否用 SV 去重 } }
SOURCE_GROUPS = {
    "疗效评价指标超窗": {
        "sources": [
            ("QS_TCM", "评估日期", None),
            ("QS_SPI", "评估日期", None),
            ("QS_DAI", "评估日期", None),
            ("QS_SFI", "评估日期", None),
            ("RS",     "评估日期", None),
        ],
        "dedup_sv": False,
    },
    "安全性评价指标超窗": {
        "sources": [
            ("VS",      "检查日期", None),
            ("PE",      "检查日期", None),
            ("EG",      "检查日期", None),
            ("LB_HCG1", "采样日期", None),
            ("LB_HCG2", "采样日期", None),
            ("LB_CRP",  "采样日期", None),
            ("LB_ESR",  "采样日期", None),
            ("LB_HEM",  "采样日期", None),
            ("LB_URI",  "采样日期", None),
            ("LB_MIC",  "采样日期", None),
            ("LB_UACR", "采样日期", None),
            ("LB_CHEM", "采样日期", None),
        ],
        "dedup_sv": True,
    },
    "其他指标超窗": {
        "sources": [
            ("SV",      "访视日期", None),
            ("VS_HW",   "检查日期", None),
            ("DA_DD1",  "发药日期", "试验药物发放记录（发药日期）"),
            ("DA_DD1",  "受试者首次用药时间", "试验药物发放记录（受试者首次用药时间）"),
            ("DA_DR1",  "回收日期", None),
        ],
        "dedup_sv": False,
    },
}

# 汇总输出页面顺序（含缩进）
PAGE_ORDER = {
    "疗效评价指标超窗": [
        "中医证候积分量表", "脊柱疼痛量表",
        "巴斯强直性脊柱炎疾病活动性指数（BASDAI）",
        "巴斯强直性脊柱炎躯体功能性指数（BASFI）",
        "患者总体评价（PGA）",
    ],
    "安全性评价指标超窗": [
        "生命体征", "体格检查", "血妊娠", "尿妊娠",
        "C反应蛋白/超敏C反应蛋白", "红细胞沉降率",
        "血常规", "尿常规", "尿沉渣镜检",
        "随机尿微量白蛋白", "血生化", "12导联心电图",
    ],
    "其他指标超窗": [
        "访视日期", "身高体重",
        "试验药物发放记录（发药日期）",
        "试验药物发放记录（受试者首次用药时间）",
        "试验药物回收记录",
    ],
}

# ── 列名集中管理 ──

IMPORT_SYSTEM = [VAR_SUBJ, "受试者状态", "访视名称", "页面名称"]
IMPORT_TW     = [TIMEWIN_CAT_COL, TIMEWIN_VISIT_COL, TIMEWIN_LOWER_COL, TIMEWIN_UPPER_COL]
IMPORT_RAND   = [VAR_SUBJ, "随机时间"]

VAR_STATUS    = "受试者状态"
VAR_VISIT     = "访视名称"
VAR_FORM      = "页面名称"
VAR_EVAL_DATE = "评估日期"
VAR_RAND_TIME = "随机时间"
VAR_TW_UPPER  = TIMEWIN_UPPER_COL
VAR_TW_LOWER  = TIMEWIN_LOWER_COL
VAR_UPPER     = "上限"
VAR_LOWER     = "下限"
VAR_OVERDUE   = "超窗"
VAR_OVER_DAYS = "超窗时间（天）"
VAR_CAT       = "类别"

EXCLUDE_STATUS = "筛选失败"


def compute_overdue(sources):
    """加载并计算超窗，返回超窗记录。"""
    dfs_all = []
    for sheet, date_col, category, page_name in sources:
        df_s = load_sheet(sheet, IMPORT_SYSTEM + [date_col])
        if date_col != VAR_EVAL_DATE:
            df_s = df_s.rename(columns={date_col: VAR_EVAL_DATE})
        if page_name is not None:
            df_s[VAR_FORM] = page_name
        df_s[VAR_CAT] = category
        dfs_all.append(df_s)

    df = pd.concat(dfs_all)
    df = df[df[VAR_STATUS] != EXCLUDE_STATUS]
    df = df.drop_duplicates()
    df = df.dropna(subset=[VAR_EVAL_DATE])
    if len(df) == 0:
        return df

    df = (
        df.merge(df_tw, on=[VAR_CAT, VAR_VISIT], how="left")
          .merge(df_rand, on=VAR_SUBJ, how="left")
    )

    df[VAR_RAND_TIME] = pd.to_datetime(df[VAR_RAND_TIME], errors="coerce")
    df[VAR_EVAL_DATE] = pd.to_datetime(df[VAR_EVAL_DATE], errors="coerce")
    df[VAR_TW_UPPER]  = pd.to_numeric(df[VAR_TW_UPPER], errors="coerce")
    df[VAR_TW_LOWER]  = pd.to_numeric(df[VAR_TW_LOWER], errors="coerce")

    df[VAR_UPPER] = df[VAR_RAND_TIME] + pd.to_timedelta(df[VAR_TW_UPPER], unit="D")
    df[VAR_LOWER] = df[VAR_RAND_TIME] + pd.to_timedelta(df[VAR_TW_LOWER], unit="D")

    df[VAR_OVERDUE] = np.where(
        (df[VAR_EVAL_DATE] > df[VAR_UPPER]) | (df[VAR_EVAL_DATE] < df[VAR_LOWER]),
        "超窗", "未超窗",
    )
    return df[df[VAR_OVERDUE] == "超窗"]


# ── 1 读取 ──

df_tw = pd.read_excel(timewin_path, sheet_name=TIMEWIN_SHEET, usecols=IMPORT_TW)
df_tw[TIMEWIN_VISIT_COL] = df_tw[TIMEWIN_VISIT_COL].str.strip()
df_tw[VAR_TW_LOWER] = pd.to_numeric(
    df_tw[VAR_TW_LOWER].astype(str).str.replace("`", ""), errors="coerce"
)
df_tw[VAR_TW_UPPER] = pd.to_numeric(
    df_tw[VAR_TW_UPPER].astype(str).str.replace("`", ""), errors="coerce"
)
df_tw = df_tw.dropna(subset=[VAR_TW_LOWER, VAR_TW_UPPER])
df_tw[VAR_TW_LOWER] = df_tw[VAR_TW_LOWER].astype("Int32")
df_tw[VAR_TW_UPPER] = df_tw[VAR_TW_UPPER].astype("Int32")

df_rand = load_sheet(FORM_RAND, usecols=IMPORT_RAND)

# ── 2~6 计算各类超窗 ──

# 访视超窗（SV 单独处理用于去重）
visit_sources = [("SV", "访视日期", "其他指标超窗", "访视日期")]
df_visit = compute_overdue(visit_sources)

all_parts = []
for cat, cfg in SOURCE_GROUPS.items():
    df_cat = compute_overdue(cfg["sources"])

    # SV 去重
    if cfg.get("dedup_sv") and len(df_visit) > 0 and len(df_cat) > 0:
        vd = df_visit[[VAR_SUBJ, VAR_VISIT, VAR_EVAL_DATE]].rename(
            columns={VAR_EVAL_DATE: "访视日期"})
        df_cat = df_cat.merge(vd, on=[VAR_SUBJ, VAR_VISIT], how="left")
        df_cat = df_cat[
            df_cat["访视日期"].isna() | (df_cat["访视日期"] != df_cat[VAR_EVAL_DATE])
        ]
        df_cat = df_cat.drop(columns="访视日期", errors="ignore")

    all_parts.append(df_cat)

df_all = pd.concat(all_parts, ignore_index=True)

# ── 5 派生超窗时间 ──

df_all[VAR_OVER_DAYS] = np.where(
    df_all[VAR_EVAL_DATE] > df_all[VAR_UPPER],
    (df_all[VAR_EVAL_DATE] - df_all[VAR_UPPER]).dt.days,
    (df_all[VAR_LOWER] - df_all[VAR_EVAL_DATE]).dt.days,
)

# ── 4 变形：分组汇总 ──

page_stats = df_all.groupby([VAR_CAT, VAR_FORM]).agg(
    例次=(VAR_SUBJ, "count"),
    例数=(VAR_SUBJ, "nunique"),
    最小超窗时间=(VAR_OVER_DAYS, "min"),
    最大超窗时间=(VAR_OVER_DAYS, "max"),
).reset_index()

category_stats = df_all.groupby(VAR_CAT).agg(
    例次=(VAR_SUBJ, "count"),
    例数=(VAR_SUBJ, "nunique"),
    最小超窗时间=(VAR_OVER_DAYS, "min"),
    最大超窗时间=(VAR_OVER_DAYS, "max"),
).reset_index()

# ── 7 格式化 ──

result_rows = []
for category, page_list in PAGE_ORDER.items():
    cat_row = category_stats[category_stats[VAR_CAT] == category]
    if len(cat_row) == 0:
        continue
    cat_row = cat_row.iloc[0]
    result_rows.append({
        "未遵循研究方案时间窗子类别": category,
        "例次": cat_row["例次"],
        "例数": cat_row["例数"],
        "最小超窗时间（天）": cat_row["最小超窗时间"],
        "最大超窗时间（天）": cat_row["最大超窗时间"],
    })

    pages = page_stats[page_stats[VAR_CAT] == category]
    for page_name in page_list:
        page_row = pages[pages[VAR_FORM] == page_name]
        if len(page_row) > 0:
            page_row = page_row.iloc[0]
            result_rows.append({
                "未遵循研究方案时间窗子类别": f"        {page_row[VAR_FORM]}",
                "例次": page_row["例次"],
                "例数": page_row["例数"],
                "最小超窗时间（天）": page_row["最小超窗时间"],
                "最大超窗时间（天）": page_row["最大超窗时间"],
            })

df_out = pd.DataFrame(result_rows)[[
    "未遵循研究方案时间窗子类别", "例次", "例数",
    "最小超窗时间（天）", "最大超窗时间（天）",
]]
df_out["最小超窗时间（天）"] = df_out["最小超窗时间（天）"].astype("Int32")
df_out["最大超窗时间（天）"] = df_out["最大超窗时间（天）"].astype("Int32")

# ── 8 输出 ──

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    [],
    row_height_cm=0.6,
    auto_width=True,
    include_notes=False,
)
