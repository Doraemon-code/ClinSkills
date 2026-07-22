# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 两个表单按「关联行号」字段匹配后，核查时间窗口是否重合
#       （典型：CM 用药区间 vs AE/MH 发生区间）。源表或目标表「是否持续」
#       为「是」时，结束端折算为今天；结束日期缺失亦折算为今天。
#       日期支持 UK/UNK 部分日期（经 compare_dates 处理）。
# @tags 关联行号,时间重合,overlap,CM,AE,MH,ongoing,部分日期
# @config SRC_FORM/SRC_LINK_COL/SRC_REASON_*/SRC_STDAT/SRC_ENDAT/SRC_ONGO,
#         TGT_FORM/TGT_NAME/TGT_STDAT/TGT_ENDAT/TGT_ONGO, OUTPUT_COLS

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
_SYS_RENAME = {_SU: _OUT_SUBJ, _RO: _OUT_ROW}

# ── 项目配置（按本项目元数据调整；仅业务字段）──

CHECK_NAME = "CM用药时间与AE时间重合核查"

VAR_SUBJ    = _SU       # 读取名（clinflash→受试者编号 / taimei5→受试者 / taimei6→受试者编号）
VAR_ROW     = _RO       # 读取名（clinflash→行号 / taimei5→记录号 / taimei6→字段记录号）
VAR_TGT_ROW = "目标行号"
VAR_CHECK   = "核查结果"

# 源表（通常是 CM）
SRC_FORM   = "CM"
SRC_IMPORT = [
    VAR_SUBJ,
    VAR_ROW,
    "给药原因(CMINDC)",
    "关联的不良事件(CMAENO)",
    "开始日期(CMSTDAT)",
    "是否持续(CMONGO)",
    "结束日期(CMENDAT)",
]
SRC_LINK_COL   = "关联的不良事件(CMAENO)"
SRC_REASON_COL = "给药原因(CMINDC)"   # None = 不按原因筛选
SRC_REASON_VAL = "不良事件"            # None = 不按原因筛选
SRC_STDAT      = "开始日期(CMSTDAT)"
SRC_ENDAT      = "结束日期(CMENDAT)"
SRC_ONGO       = "是否持续(CMONGO)"    # None = 源表无 ongoing 列
SRC_LABEL      = "CM用药"

# 目标表（AE 或 MH）
TGT_FORM   = "AE"
TGT_IMPORT = [
    VAR_SUBJ,
    VAR_ROW,
    "不良事件名称(AETERM)",
    "开始日期(AESTDAT)",
    "转归日期(AEENDAT)",
]
TGT_NAME  = "不良事件名称(AETERM)"
TGT_STDAT = "开始日期(AESTDAT)"
TGT_ENDAT = "转归日期(AEENDAT)"
TGT_ONGO  = None                       # None = 目标表无 ongoing 列（MH 通常有）
TGT_LABEL = "AE"

# "是否持续"表示"持续中"的取值（跨 EDC 语言）——英文导出（taimei6 en 等）改为 "Y" / "√"
ONGO_YES_VAL = "是"

# 输出列序（可增减；None / 空串自动剔除）
OUTPUT_COLS = [c for c in [
    _OUT_SUBJ,
    _OUT_ROW,
    SRC_LINK_COL,
    VAR_TGT_ROW,
    TGT_NAME,
    SRC_STDAT,
    SRC_ENDAT,
    SRC_ONGO,
    TGT_STDAT,
    TGT_ENDAT,
    TGT_ONGO,
    VAR_CHECK,
] if c]

# ── 1 读取 ──

df_src = load_sheet(SRC_FORM, usecols=SRC_IMPORT)
df_tgt = load_sheet(TGT_FORM, usecols=TGT_IMPORT)

# ── 2 归一化 ──

df_src[SRC_LINK_COL] = df_src[SRC_LINK_COL].astype(str).str.strip()

# ── 3 筛选：按原因（如给药原因=不良事件）──

if SRC_REASON_COL and SRC_REASON_VAL:
    df_src = df_src[df_src[SRC_REASON_COL] == SRC_REASON_VAL].copy()
print(f"{SRC_FORM} 筛选后记录数: {len(df_src)}")

# ── 4 派生：从关联字段提取目标行号 ──

_PAT = re.compile(r"\((\d+)\)")

def parse_tgt_rows(s):
    if not s or s in ("nan", "None"):
        return []
    return [int(n) for n in _PAT.findall(s)]

df_src[VAR_TGT_ROW] = df_src[SRC_LINK_COL].apply(parse_tgt_rows)
df_src = df_src[df_src[VAR_TGT_ROW].apply(len) > 0].copy()
df_src = df_src.explode(VAR_TGT_ROW, ignore_index=True)
df_src[VAR_TGT_ROW] = df_src[VAR_TGT_ROW].astype(int)
print(f"可解析目标行号记录数: {len(df_src)}")

# ── 5 连接：按 受试者 + 行号 匹配目标表 ──

df_out = df_src.merge(
    df_tgt,
    left_on=[VAR_SUBJ, VAR_TGT_ROW],
    right_on=[VAR_SUBJ, VAR_ROW],
    how="left",
    suffixes=("", "_tgt"),
)
print(f"匹配后记录数: {len(df_out)}")

# ── 6 派生：时间窗口重合判断 ──

TODAY = date.today().isoformat()

def _end_eff(endat, ongo):
    if ongo is not None and str(ongo).strip() == ONGO_YES_VAL:
        return TODAY
    if pd.isna(endat) or str(endat).strip() in ("", "nan", "None"):
        return TODAY
    return endat

def check_overlap(row):
    src_st   = row[SRC_STDAT]
    src_end  = _end_eff(row[SRC_ENDAT], row[SRC_ONGO] if SRC_ONGO else None)
    tgt_st   = row[TGT_STDAT]
    tgt_end  = _end_eff(row[TGT_ENDAT], row[TGT_ONGO] if TGT_ONGO else None)

    cmp_src_end_vs_tgt_st = compare_dates(src_end, tgt_st, mode=1)
    cmp_tgt_end_vs_src_st = compare_dates(tgt_end, src_st, mode=1)

    if cmp_src_end_vs_tgt_st == 2 or cmp_tgt_end_vs_src_st == 2:
        return "无法判断"
    if cmp_src_end_vs_tgt_st == -1:
        return f"不重合：{SRC_LABEL}结束早于{TGT_LABEL}开始"
    if cmp_tgt_end_vs_src_st == -1:
        return f"不重合：{SRC_LABEL}开始晚于{TGT_LABEL}结束"
    return "重合"

df_out[VAR_CHECK] = df_out.apply(check_overlap, axis=1)

# ── 7 只保留不重合或无法判断的记录（需发质疑）──

df_out = df_out[df_out[VAR_CHECK] != "重合"].copy()

# ── 8 格式化 ──

df_out = df_out.rename(columns=_SYS_RENAME)
df_out = df_out[OUTPUT_COLS]

# ── 9 输出 ──

n = len(df_out)
title = CHECK_NAME
title_text = f"{title}（{n}条）"

export_to_one_excel_with_format(
    df_out,
    f"{output_path}/listing/{title}.xlsx",
    title,
    title_text,
    add_title=True,
)
