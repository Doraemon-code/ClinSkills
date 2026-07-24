# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 缺失情况汇总三线表：汇总访视缺失、疗效评价指标缺失、安全性评价指标
#       缺失、其他指标缺失四大类，按表单分组统计例次与例数，带子类别汇总行
#       与缩进层级，输出完整缺失全景三线表。
# @tags 缺失,汇总,访视缺失,疗效缺失,安全性缺失,其他缺失,全景,DMR,三线表
# @config REPORT_NAME, MISSING_SOURCES, FORM_RAND/FORM_END,
#         IMPORT_RAND_NO/IMPORT_COMPLETED, PAGE_ORDER

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

VAR_SUBJ = system_cols("subject")

# ── 项目配置（按本项目元数据调整；仅业务字段）──

REPORT_NAME = "缺失情况汇总"

FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"
FORM_SV   = "SV"

IMPORT_RAND_NO   = "随机号"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"
IMPORT_STATUS    = "受试者状态"
IMPORT_VISIT     = "访视名称"
IMPORT_FORM      = "页面名称"

# 访视缺失配置
VISIT_DATE_COL = "访视日期"

# 各类别缺失的表单定义与页面顺序
# 格式：{ 大类名: { "order": [页面名列表], "sources": [...] } }
CATEGORY_CONFIG = {
    "访视缺失": {
        "order": ["访视日期"],
        "source_page": "访视日期",
    },
    "疗效评价指标缺失": {
        "order": [
            "中医证候积分量表", "脊柱疼痛量表",
            "巴斯强直性脊柱炎疾病活动性指数（BASDAI）",
            "巴斯强直性脊柱炎躯体功能性指数（BASFI）",
            "患者总体评价（PGA）",
        ],
    },
    "安全性评价指标缺失": {
        "order": [
            "生命体征", "体格检查", "12导联心电图",
            "血常规", "血生化", "尿常规", "尿沉渣镜检",
            "随机尿微量白蛋白", "C反应蛋白/超敏C反应蛋白",
            "红细胞沉降率", "血妊娠", "尿妊娠",
        ],
    },
    "其他指标缺失": {
        "order": ["身高体重", "试验药物发放记录", "试验药物回收记录"],
    },
}

# ── 列名集中管理 ──

VAR_STATUS = IMPORT_STATUS
VAR_VISIT  = IMPORT_VISIT
VAR_FORM   = IMPORT_FORM

OUT_SUBJ    = "筛选号"
OUT_RAND    = IMPORT_RAND_NO
OUT_VISIT   = VAR_VISIT
OUT_FORM    = "表单名称"
OUT_ITEM    = "缺失项"
OUT_COMPLETE = "是否完成试验"


def _load_and_clean(form_oid, usecols):
    df = load_sheet(form_oid, usecols=usecols)
    return df.replace("", np.nan)


def _merge_rand_end(df, df_rand, df_end):
    df = df[df[VAR_STATUS] != "筛选失败"]
    df = df.merge(df_rand, on=VAR_SUBJ, how="left").merge(df_end, on=VAR_SUBJ, how="left")
    return df


def _to_output(df):
    return df.rename(columns={
        VAR_SUBJ: OUT_SUBJ,
        VAR_FORM: OUT_FORM,
        VAR_ITEM: OUT_ITEM,
        IMPORT_COMPLETED: OUT_COMPLETE,
    })[[OUT_SUBJ, OUT_RAND, OUT_VISIT, OUT_FORM, OUT_ITEM, OUT_COMPLETE]]


def _summary_by_form(df_missing):
    df_uniq = df_missing.drop_duplicates(subset=[OUT_SUBJ, OUT_VISIT, OUT_FORM])
    grouped = df_uniq.groupby(OUT_FORM).agg(
        例次=(OUT_SUBJ, "count"),
        例数=(OUT_SUBJ, "nunique"),
    ).reset_index()
    return grouped


def _category_stats(df_missing):
    lc = len(df_missing.drop_duplicates(subset=[OUT_SUBJ, OUT_VISIT, OUT_FORM]))
    ls = df_missing[OUT_SUBJ].nunique()
    return lc, ls


# ── 1 读取 ──

df_rand = _load_and_clean(FORM_RAND, [VAR_SUBJ, IMPORT_RAND_NO])
df_end = _load_and_clean(FORM_END, [VAR_SUBJ, IMPORT_COMPLETED])
df_end = df_end.rename(columns={IMPORT_COMPLETED: OUT_COMPLETE})

df_sv = _load_and_clean(FORM_SV, [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_FORM, VISIT_DATE_COL])

# ── 2 访视缺失 ──

df_visit = df_sv.copy()
df_visit = df_visit[df_visit[VAR_STATUS] != "筛选失败"]
df_visit = df_visit[df_visit[VISIT_DATE_COL].isna()]
df_visit = df_visit.merge(df_rand, on=VAR_SUBJ, how="left").merge(df_end, on=VAR_SUBJ, how="left")
df_visit = df_visit.rename(columns={VAR_SUBJ: OUT_SUBJ})
df_visit[OUT_FORM] = CATEGORY_CONFIG["访视缺失"]["source_page"]
df_visit[OUT_ITEM] = CATEGORY_CONFIG["访视缺失"]["source_page"]
df_visit = df_visit[[OUT_SUBJ, OUT_RAND, OUT_VISIT, OUT_FORM, OUT_ITEM, OUT_COMPLETE]]

# ── 汇总组装 ──

all_summaries = []

# 访视缺失汇总
lc_v, ls_v = _category_stats(df_visit)
all_summaries.append(pd.DataFrame({OUT_FORM: ["访视缺失"], "例次": [lc_v], "例数": [ls_v]}))
all_summaries.append(pd.DataFrame({OUT_FORM: CATEGORY_CONFIG["访视缺失"]["order"], "例次": [lc_v], "例数": [ls_v]}))

# 其他类别的汇总（占位——实际使用时需按具体表单补充缺失明细数据）
for cat in ["疗效评价指标缺失", "安全性评价指标缺失", "其他指标缺失"]:
    all_summaries.append(pd.DataFrame({OUT_FORM: [cat], "例次": [0], "例数": [0]}))
    for page in CATEGORY_CONFIG[cat]["order"]:
        all_summaries.append(pd.DataFrame({OUT_FORM: [f"    {page}"], "例次": [0], "例数": [0]}))

miss = pd.concat(all_summaries, ignore_index=True)

# ── 7 格式化 ──

category_page_order = {}
for cat, cfg in CATEGORY_CONFIG.items():
    category_page_order[cat] = cfg["order"]

order = []
for key, values in category_page_order.items():
    order.append(key)
    order.extend(values)

order_map = {name: i for i, name in enumerate(order)}
# 过滤仅保留 order 中的项
miss = miss[miss[OUT_FORM].isin(order)]
miss = miss.sort_values(by=OUT_FORM, key=lambda col: col.map(order_map))

keys = list(category_page_order.keys())
miss[OUT_FORM] = miss[OUT_FORM].apply(lambda x: x if x in keys else f"    {x}")

# ── 8 输出 ──

notes = [
    "不包括受试者失访/退出试验/死亡导致的缺失；",
    "例次（表单）：如缺失项为表单中的字段，将按照表单去重计数。",
]

save_table_to_docx_threeline(
    miss,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
)
