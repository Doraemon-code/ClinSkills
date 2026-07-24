# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 动态链接准确性核查：源表单的「关联 AE/MH」链接字段，解析其
#       「类型 (行号) 名称 日期」段后，与目标表实际记录核对——
#       ① 链接指向的行号是否存在（关联空行）
#       ② 链接显示的名称/日期与目标表实际值是否一致（关联未更新）
#       多记录以 $ 分隔。LINK_CONFIGS 按项目填写。
# @tags 动态链接,关联,行号解析,AE,MH,名称一致性,日期一致性
# @config LINK_CONFIGS

import sys, re
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_listing_dir
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols

# ── 系统列（读取用 EDC 专属名，输出 rename 为通用中文标签）──

_SYS = system_cols()
_SU = _SYS["subject"]
_RO = _SYS["row"]

_OUT_SUBJ = "筛选号"
_SYS_RENAME = {_SU: _OUT_SUBJ}

# ── 项目配置（按本项目元数据调整）──

CHECK_NAME = "动态链接准确性核查"

# (源表单OID, 链接列名, 目标表单OID, 目标名称列名, 目标日期列名)
LINK_CONFIGS = [
    ("CM",     "关联的不良事件(CMAENO)",     "AE", "不良事件名称(AETERM)", "开始日期(AESTDAT)"),
    ("CM",     "关联的既往及现病史(CMMHNO)",   "MH", "疾病名称(MHTERM)",   "开始日期(MHSTDAT)"),
    ("VS",     "关联的不良事件(VSAENO)",     "AE", "不良事件名称(AETERM)", "开始日期(AESTDAT)"),
    ("VS",     "关联的既往及现病史(VSMHNO)",   "MH", "疾病名称(MHTERM)",   "开始日期(MHSTDAT)"),
    ("PE",     "关联的不良事件(PEAENO)",     "AE", "不良事件名称(AETERM)", "开始日期(AESTDAT)"),
    ("PE",     "关联的既往及现病史(PEMHNO)",   "MH", "疾病名称(MHTERM)",   "开始日期(MHSTDAT)"),
    ("AE",     "若是，请选择最初的不良事件编号(AEGRPID)", "AE", "不良事件名称(AETERM)", "开始日期(AESTDAT)"),
]

# ── 列名 ──

VAR_SUBJ          = _SU       # 读取名（clinflash→受试者编号 / taimei5→受试者 / taimei6→受试者编号）
VAR_SRC_LINE      = "源表单行号"
VAR_SRC_FORM      = "源表单"
VAR_LINK_FIELD    = "链接字段"
VAR_LINK_VALUE    = "链接原始值"
VAR_TARGET_FORM   = "目标表单"
VAR_TARGET_RO    = "链接目标行号"
VAR_LINK_TEXT     = "链接显示名称"
VAR_TARGET_TEXT   = "目标表单实际名称"
VAR_LINK_DATE     = "链接显示日期"
VAR_TARGET_DATE   = "目标表单实际日期"
VAR_CHECK_TYPE    = "核查类型"
VAR_CHECK_DETAIL  = "核查结果"

OUTPUT_COLS_RAW = [
    VAR_SUBJ, VAR_SRC_FORM, VAR_SRC_LINE, VAR_LINK_FIELD, VAR_TARGET_FORM,
    VAR_TARGET_RO, VAR_LINK_VALUE, VAR_LINK_TEXT, VAR_LINK_DATE,
    VAR_TARGET_TEXT, VAR_TARGET_DATE, VAR_CHECK_TYPE, VAR_CHECK_DETAIL,
]
OUTPUT_COLS = [
    _OUT_SUBJ, VAR_SRC_FORM, VAR_SRC_LINE, VAR_LINK_FIELD, VAR_TARGET_FORM,
    VAR_TARGET_RO, VAR_LINK_VALUE, VAR_LINK_TEXT, VAR_LINK_DATE,
    VAR_TARGET_TEXT, VAR_TARGET_DATE, VAR_CHECK_TYPE, VAR_CHECK_DETAIL,
]

# ── 链接值解析：<目标表单> (行号) 名称 日期，多段以 $ 分隔 ──
# 前缀由 LINK_CONFIGS 的目标表单集合动态生成（勿写死），否则配了非 AE/MH 目标会静默漏检。
_TGT_FORMS = sorted({cfg[2] for cfg in LINK_CONFIGS}, key=len, reverse=True)
_LINK_SEG_PAT = re.compile(
    r"^(" + "|".join(re.escape(f) for f in _TGT_FORMS)
    + r")\s+\((\d+)\)\s+(.+)\s+(\d{4}-(?:\d{2}|UK|UNK)-(?:\d{2}|UK|UNK))$"
)

def parse_link_segments(link_value):
    if pd.isna(link_value):
        return []
    s = str(link_value).strip()
    if not s or s in ("nan", "None"):
        return []
    results = []
    for seg in s.split("$"):
        seg = seg.strip()
        m = _LINK_SEG_PAT.match(seg)
        if m:
            results.append((m.group(1), int(m.group(2)), m.group(3).strip(), m.group(4)))
    return results

# ── 1 按源表单分组链接配置 ──

_form_links = {}
for src_form, link_col, tgt_form, tgt_name_col, tgt_date_col in LINK_CONFIGS:
    _form_links.setdefault(src_form, []).append((link_col, tgt_form, tgt_name_col, tgt_date_col))

_target_cache = {}

def _get_target(form_oid, name_col, date_col):
    key = (form_oid, name_col, date_col)
    if key not in _target_cache:
        _target_cache[key] = load_sheet(form_oid, usecols=[VAR_SUBJ, _RO, name_col, date_col])
    return _target_cache[key]

_results = []
_summary = []

total_linked = 0
total_bad_row = 0
total_mismatch_name = 0
total_mismatch_date = 0

for src_form, link_configs in _form_links.items():
    import_cols = [VAR_SUBJ, _RO]
    for link_col, _, _, _ in link_configs:
        if link_col not in import_cols:
            import_cols.append(link_col)

    try:
        df_src = load_sheet(src_form, usecols=import_cols)
    except Exception as e:
        print(f"[跳过] {src_form}: {e}")
        continue

    n_total = len(df_src)

    # ── 2 归一化 ──
    for link_col, _, _, _ in link_configs:
        df_src[link_col] = df_src[link_col].astype(str).str.strip()
        df_src[link_col] = df_src[link_col].replace({"nan": "", "None": ""})

    for link_col, tgt_form, tgt_name_col, tgt_date_col in link_configs:
        print(f"  {src_form}.{link_col} → {tgt_form}")

        mask_empty = df_src[link_col].isin(["", "nan", "None"])
        n_empty = mask_empty.sum()
        n_filled = n_total - n_empty

        df_filled = df_src[~mask_empty].copy()
        df_target = _get_target(tgt_form, tgt_name_col, tgt_date_col)

        rows_parsed = []
        bad_parse_count = 0
        for _, src_row in df_filled.iterrows():
            segments = parse_link_segments(src_row[link_col])
            if not segments:
                bad_parse_count += 1
                _results.append({
                    VAR_SUBJ: src_row[VAR_SUBJ], VAR_SRC_FORM: src_form,
                    VAR_SRC_LINE: src_row[_RO], VAR_LINK_FIELD: link_col,
                    VAR_LINK_VALUE: src_row[link_col], VAR_TARGET_FORM: tgt_form,
                    VAR_TARGET_RO: "", VAR_LINK_TEXT: "", VAR_LINK_DATE: "",
                    VAR_TARGET_TEXT: "", VAR_TARGET_DATE: "",
                    VAR_CHECK_TYPE: "无法解析",
                    VAR_CHECK_DETAIL: "链接字段非空但格式异常，无法解析行号",
                })
                continue
            for seg_type, seg_row, seg_text, seg_date in segments:
                rows_parsed.append({
                    VAR_SUBJ: src_row[VAR_SUBJ], VAR_SRC_FORM: src_form,
                    VAR_SRC_LINE: src_row[_RO], VAR_LINK_FIELD: link_col,
                    VAR_LINK_VALUE: src_row[link_col], VAR_TARGET_FORM: tgt_form,
                    VAR_TARGET_RO: seg_row, VAR_LINK_TEXT: seg_text, VAR_LINK_DATE: seg_date,
                })

        if rows_parsed:
            df_parsed = pd.DataFrame(rows_parsed)
            total_linked += len(df_parsed)

            df_merged = df_parsed.merge(
                df_target,
                left_on=[VAR_SUBJ, VAR_TARGET_RO],
                right_on=[VAR_SUBJ, _RO],
                how="left",
                suffixes=("", "_tgt"),
            )

            mask_no_target = df_merged[tgt_name_col].isna()
            for _, r in df_merged[mask_no_target].iterrows():
                total_bad_row += 1
                _results.append({
                    VAR_SUBJ: r[VAR_SUBJ], VAR_SRC_FORM: r[VAR_SRC_FORM],
                    VAR_SRC_LINE: r[VAR_SRC_LINE], VAR_LINK_FIELD: r[VAR_LINK_FIELD],
                    VAR_LINK_VALUE: r[VAR_LINK_VALUE], VAR_TARGET_FORM: r[VAR_TARGET_FORM],
                    VAR_TARGET_RO: r[VAR_TARGET_RO], VAR_LINK_TEXT: r[VAR_LINK_TEXT],
                    VAR_LINK_DATE: r[VAR_LINK_DATE], VAR_TARGET_TEXT: "", VAR_TARGET_DATE: "",
                    VAR_CHECK_TYPE: "关联空行",
                    VAR_CHECK_DETAIL: "链接指向的行号在目标表单中不存在",
                })

            df_matched = df_merged[~mask_no_target]
            for _, r in df_matched.iterrows():
                actual_name = str(r[tgt_name_col]).strip()
                actual_date = str(r[tgt_date_col]).strip()
                link_name   = str(r[VAR_LINK_TEXT]).strip()
                link_date   = str(r[VAR_LINK_DATE]).strip()

                name_mismatch = (actual_name != link_name and actual_name != "nan")
                date_mismatch = (actual_date != link_date and actual_date != "nan")

                if name_mismatch or date_mismatch:
                    parts = []
                    if name_mismatch:
                        total_mismatch_name += 1
                        parts.append(f"名称：链接「{link_name}」→ 实际「{actual_name}」")
                    if date_mismatch:
                        total_mismatch_date += 1
                        parts.append(f"日期：链接「{link_date}」→ 实际「{actual_date}」")
                    if name_mismatch and date_mismatch:
                        check_type = "关联未更新（名称+日期）"
                    elif name_mismatch:
                        check_type = "关联未更新（名称）"
                    else:
                        check_type = "关联未更新（日期）"
                    _results.append({
                        VAR_SUBJ: r[VAR_SUBJ], VAR_SRC_FORM: r[VAR_SRC_FORM],
                        VAR_SRC_LINE: r[VAR_SRC_LINE], VAR_LINK_FIELD: r[VAR_LINK_FIELD],
                        VAR_LINK_VALUE: r[VAR_LINK_VALUE], VAR_TARGET_FORM: r[VAR_TARGET_FORM],
                        VAR_TARGET_RO: r[VAR_TARGET_RO], VAR_LINK_TEXT: link_name,
                        VAR_LINK_DATE: link_date, VAR_TARGET_TEXT: actual_name,
                        VAR_TARGET_DATE: actual_date, VAR_CHECK_TYPE: check_type,
                        VAR_CHECK_DETAIL: "；".join(parts),
                    })

        _summary.append({
            "源表单": src_form, "链接字段": link_col, "目标表单": tgt_form,
            "总记录数": n_total, "非空": n_filled, "为空": n_empty,
            "已解析链数": len(rows_parsed), "无法解析": bad_parse_count,
        })

# ── 3 格式化 ──

df_out = pd.DataFrame(_results, columns=OUTPUT_COLS_RAW) if _results else pd.DataFrame(columns=OUTPUT_COLS_RAW)
df_out = df_out.rename(columns=_SYS_RENAME)
df_out = df_out[OUTPUT_COLS]
df_summ = pd.DataFrame(_summary)

# ── 4 输出 ──

print(f"\n=== 各表单动态链接填写统计 ===")
print(f"{'源表单':<10} {'链接字段':<30} {'总记录':<6} {'非空':<6} {'为空':<6} {'已解析链':<8} {'异常':<4}")
print("-" * 76)
for _, row in df_summ.iterrows():
    print(f"{row['源表单']:<10} {row['链接字段']:<30} {row['总记录数']:<6} {row['非空']:<6} {row['为空']:<6} {row['已解析链数']:<8} {row['无法解析']:<4}")

print(f"\n=== 核查汇总 ===")
print(f"已解析有效链接: {total_linked}")
print(f"关联空行（行号不存在）: {total_bad_row}")
print(f"关联未更新（名称不一致）: {total_mismatch_name}")
print(f"关联未更新（日期不一致）: {total_mismatch_date}")
print(f"无法解析: {df_summ['无法解析'].sum()}")
print(f"问题记录合计: {len(df_out)} 条")

title = CHECK_NAME
title_text = f"{title}（{len(df_out)}条）"

if len(df_out) > 0:
    export_to_one_excel_with_format(
        df_out,
        f"{output_listing_dir}/{title}.xlsx",
        title,
        title_text,
        add_title=True,
    )
    print(f"输出文件: {output_listing_dir}/{title}.xlsx")
else:
    print("所有动态链接数据关联正确，无异常记录。")
