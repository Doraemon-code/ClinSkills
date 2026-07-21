# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 主表筛选特定类型的记录后，核查目标表是否有关联记录：
#       ① 主表包含药物/治疗类记录时，目标表至少应有一条通过行号关联的记录
#       ② 目标表开始日期是否早于主表开始日期（时序异常）
#       输出全部记录并标记异常（正常/异常）。
#       典型场景：AE 药物治疗 → CM 应有关联合并用药记录。
# @tags 关联行号,一致性,交叉表,CM,AE,过滤,异常标记,全量输出
# @config MAIN_FORM/MAIN_FILTER_COL/MAIN_FILTER_INCLUDE/MAIN_FILTER_EXCLUDE,
#         MAIN_IMPORT/MAIN_TERM/MAIN_STDAT/MAIN_ENDAT/MAIN_OUTCOME,
#         LINK_FORM/LINK_IMPORT/LINK_COL/LINK_REASON_COL/LINK_REASON_VAL,
#         LINK_STDAT/LINK_ENDAT/LINK_ONGO, OUTPUT_COLS

import sys, re
from pathlib import Path
from datetime import date

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols
from utils.date_compare import compare_dates

# ── 系统列（读取用 EDC 专属名，输出 rename 为通用中文标签）──

_SYS = system_cols()
_SU = _SYS["subject"]
_RO = _SYS["row"]

_OUT_SUBJ = "筛选号"
_OUT_ROW  = "行号"

# ── 项目配置（按本项目元数据调整；仅业务字段）──

CHECK_NAME = "AE药物治疗与CM记录一致性核查"

# ---------- 主表（如 AE）----------
MAIN_FORM   = "AE"
MAIN_IMPORT = [
    _SU,
    _RO,
    "不良事件名称(AETERM)",
    "开始日期(AESTDAT)",
    "转归日期(AEENDAT)",
    "转归(AEOUT)",
    "对不良事件采取的措施(AEACNOTH)",
]
MAIN_FILTER_COL     = "对不良事件采取的措施(AEACNOTH)"   # 筛选依据列
MAIN_FILTER_INCLUDE = "药物治疗"                         # 必须包含的关键词
MAIN_FILTER_EXCLUDE = "非药物治疗"                       # 排除的关键词（子串误匹配）
MAIN_TERM     = "不良事件名称(AETERM)"
MAIN_STDAT    = "开始日期(AESTDAT)"
MAIN_ENDAT    = "转归日期(AEENDAT)"
MAIN_OUTCOME  = "转归(AEOUT)"

# ---------- 关联表（如 CM）----------
LINK_FORM   = "CM"
LINK_IMPORT = [
    _SU,
    _RO,
    "药物名称(通用名)(CMTRT)",
    "给药原因(CMINDC)",
    "关联的不良事件(CMAENO)",
    "开始日期(CMSTDAT)",
    "是否持续(CMONGO)",
    "结束日期(CMENDAT)",
]
LINK_COL         = "关联的不良事件(CMAENO)"   # 关联字段，含行号引用
LINK_REASON_COL  = "给药原因(CMINDC)"         # 可选：按原因筛选关联表（None=不筛选）
LINK_REASON_VAL  = "不良事件"                 # 可选：保留的原因值（None=不筛选）
LINK_STDAT       = "开始日期(CMSTDAT)"
LINK_ENDAT       = "结束日期(CMENDAT)"
LINK_ONGO        = "是否持续(CMONGO)"         # None=无 ongoing 列

# ---------- 输出列 ----------
OUTPUT_COLS = [c for c in [
    _OUT_SUBJ,
    _OUT_ROW,
    MAIN_TERM,
    MAIN_STDAT,
    MAIN_ENDAT,
    MAIN_OUTCOME,
    MAIN_FILTER_COL,
    "关联记录行号",
    LINK_STDAT,
    LINK_ENDAT,
    LINK_ONGO,
    "核查结果",
    "异常标记",
] if c]

# ── 1 读取 ──

df_main = load_sheet(MAIN_FORM, usecols=MAIN_IMPORT)
df_link = load_sheet(LINK_FORM, usecols=LINK_IMPORT)

# ── 2 归一化 ──

df_link[LINK_COL] = df_link[LINK_COL].astype(str).str.strip()
if LINK_REASON_COL:
    df_link[LINK_REASON_COL] = df_link[LINK_REASON_COL].astype(str).str.strip()

# ── 3 筛选主表 ──

mask = df_main[MAIN_FILTER_COL].astype(str).str.contains(MAIN_FILTER_INCLUDE, na=False)
if MAIN_FILTER_EXCLUDE:
    mask = mask & ~df_main[MAIN_FILTER_COL].astype(str).str.contains(MAIN_FILTER_EXCLUDE, na=False)
df_main = df_main[mask].copy()
print(f"{MAIN_FORM} 筛选后记录数: {len(df_main)}")

# ── 4 筛选关联表 ──

if LINK_REASON_COL and LINK_REASON_VAL:
    df_link = df_link[df_link[LINK_REASON_COL] == LINK_REASON_VAL].copy()
print(f"{LINK_FORM} 筛选后记录数: {len(df_link)}")

# ── 5 派生：解析关联字段中的行号 ──

_LINK_PAT = re.compile(rf"{re.escape(MAIN_FORM)}\s+\((\d+)\)")  # 引用前缀随 MAIN_FORM（原硬编码 "AE"）

def parse_linked_rows(s):
    if not s or s in ("nan", "None", ""):
        return []
    return [int(n) for n in _LINK_PAT.findall(s)]

df_link["_linked_rows"] = df_link[LINK_COL].apply(parse_linked_rows)
df_link = df_link[df_link["_linked_rows"].apply(len) > 0].copy()
df_link = df_link.explode("_linked_rows", ignore_index=True)
df_link["_linked_rows"] = df_link["_linked_rows"].astype(int)
print(f"可解析关联行号记录数: {len(df_link)}")

# ── 6 连接：主表 ← 关联表 ──

df = df_main.merge(
    df_link,
    left_on=[_SU, _RO],
    right_on=[_SU, "_linked_rows"],
    how="left",
    suffixes=("", "_cm"),
)

# ── 7 派生：逐行核查 ──

TODAY = date.today().isoformat()
results = []

for _, row in df.iterrows():
    has_link = not pd.isna(row.get(LINK_COL))

    main_stdat = row[MAIN_STDAT]
    main_endat = row[MAIN_ENDAT]
    main_outcome = str(row[MAIN_OUTCOME]).strip() if not pd.isna(row[MAIN_OUTCOME]) else ""
    filter_val   = row[MAIN_FILTER_COL]

    # a. 无对应关联记录
    if not has_link:
        results.append({
            _OUT_SUBJ:       row[_SU],
            _OUT_ROW:        row[_RO],
            MAIN_TERM:       row[MAIN_TERM],
            MAIN_STDAT:      main_stdat,
            MAIN_ENDAT:      main_endat,
            MAIN_OUTCOME:    main_outcome,
            MAIN_FILTER_COL: filter_val,
            "关联记录行号": "",
            LINK_STDAT:      "",
            LINK_ENDAT:      "",
            LINK_ONGO:       "",
            "核查结果": "主表记录有目标特征，但无对应的关联表记录",
            "异常标记": "异常",
        })
        continue

    link_line  = row.get(f"{_RO}_cm", "")
    link_stdat = row[LINK_STDAT]
    link_endat = row[LINK_ENDAT]
    link_ongo  = str(row[LINK_ONGO]).strip() if LINK_ONGO and not pd.isna(row.get(LINK_ONGO)) else ""

    # b. 关联表开始日期早于主表开始日期
    cmp = compare_dates(link_stdat, main_stdat, mode=1)
    if cmp == -1:
        results.append({
            _OUT_SUBJ:       row[_SU],
            _OUT_ROW:        row[_RO],
            MAIN_TERM:       row[MAIN_TERM],
            MAIN_STDAT:      main_stdat,
            MAIN_ENDAT:      main_endat,
            MAIN_OUTCOME:    main_outcome,
            MAIN_FILTER_COL: filter_val,
            "关联记录行号": link_line,
            LINK_STDAT:      link_stdat,
            LINK_ENDAT:      link_endat,
            LINK_ONGO:       link_ongo,
            "核查结果": "关联表开始日期早于主表开始日期",
            "异常标记": "异常",
        })
    else:
        results.append({
            _OUT_SUBJ:       row[_SU],
            _OUT_ROW:        row[_RO],
            MAIN_TERM:       row[MAIN_TERM],
            MAIN_STDAT:      main_stdat,
            MAIN_ENDAT:      main_endat,
            MAIN_OUTCOME:    main_outcome,
            MAIN_FILTER_COL: filter_val,
            "关联记录行号": link_line,
            LINK_STDAT:      link_stdat,
            LINK_ENDAT:      link_endat,
            LINK_ONGO:       link_ongo,
            "核查结果": "正常",
            "异常标记": "正常",
        })

# ── 8 格式化 ──

df_out = pd.DataFrame(results, columns=OUTPUT_COLS) if results else pd.DataFrame(columns=OUTPUT_COLS)

n = len(df_out)
n_abnormal = (df_out["异常标记"] == "异常").sum()

# ── 9 输出 ──

title = CHECK_NAME
title_text = f"{title}（{n}条）"

print(f"\n=== 核查汇总 ===")
print(f"{MAIN_FORM} 筛选后总数: {len(df_main)}")
print(f"{LINK_FORM} 筛选后总数: {len(df_link)}")
print(f"总输出记录: {n} 条（异常 {n_abnormal} 条）")
if n_abnormal > 0:
    for k, v in df_out[df_out["异常标记"] == "异常"]["核查结果"].value_counts().items():
        print(f"  {k}: {v}")

export_to_one_excel_with_format(
    df_out,
    f"{output_path}/listing/{title}.xlsx",
    title,
    title_text,
    add_title=True,
)
