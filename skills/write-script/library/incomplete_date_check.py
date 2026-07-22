# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 扫描元数据中所有日期/时间字段，找出含 UK/UNK 的不完整录入，
#       拆出年/月/日/时/分部件，描述缺失类型并生成质疑说明。
#       完全元数据驱动。源数据须为 ISO 格式（日期 yyyy-MM-dd、时间 HH:mm）；
#       DATE_FORMATS / TIME_FORMATS 仅决定字段分类，非格式适配开关（详见配置块注释）。
# @tags 日期,时间,UK,UNK,不完整,部分日期,元数据驱动
# @config DATE_FORMATS, TIME_FORMATS

import sys, json, re
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols, metadata_dir

# ── 系统列（按 EDC 类型自动解析，勿手填）──

_SYS = system_cols()
_SUBJ    = _SYS["subject"]
_VISIT   = _SYS["visit_name"]
_FORMPG  = _SYS["form_name"]
_SYSTEM_COLS = list(_SYS.values())   # 全部系统列，用于过滤业务字段

# ── 项目配置（按本项目元数据调整）──

CHECK_NAME = "不完整日期时间核查"

# 元数据 fieldFormat 取值——仅用于把字段分类为「日期」或「时间」两条处理路径。
# ⚠ 下方部件解析写死 ISO 分隔符（日期 `-`、时间 `:`）与「年-月-日」顺序：改这两个
#    常量只改变分类，不会让解析器适配别的格式（如 dd/MM/yyyy）。源数据非 ISO 时，
#    须改解析逻辑本身，而非仅改此处取值。
DATE_FORMATS = ("yyyy-MM-dd",)
TIME_FORMATS = ("HH:mm",)

# ── 列名（输出用通用中文标签，EDC 无关）──

VAR_SUBJ    = "筛选号"
VAR_VISIT   = "访视"
VAR_FORMPG  = "表单页"
VAR_FORM    = "表单名称"
VAR_FIELD   = "字段名"
VAR_VALUE   = "录入值"
VAR_YEAR    = "年份"
VAR_MONTH   = "月份"
VAR_DAY     = "日期"
VAR_HOUR    = "小时"
VAR_MINUTE  = "分钟"
VAR_MISSING = "缺失类型"
VAR_NOTE    = "核查说明"

# rawdata 系统列名 → 输出标签
_SYS_RENAME = {_SUBJ: VAR_SUBJ, _VISIT: VAR_VISIT, _FORMPG: VAR_FORMPG}

OUTPUT_COLS = [
    VAR_SUBJ, VAR_VISIT, VAR_FORMPG, VAR_FORM, VAR_FIELD, VAR_VALUE,
    VAR_YEAR, VAR_MONTH, VAR_DAY, VAR_HOUR, VAR_MINUTE,
    VAR_MISSING, VAR_NOTE,
]

# ── 工具：从录入值提取日期/时间部件 ──

def _extract_part(series: pd.Series, pattern: str):
    extracted = series.str.extract(pattern, expand=False)
    numeric = pd.to_numeric(extracted, errors="coerce")
    return numeric.astype("Int64")

def _normalize_val(val_str: str) -> str:
    return (val_str.replace("\uff1a", ":")
                   .replace("\uff0d", "-")
                   .replace("\u2014", "-")
                   .replace("\u2013", "-"))

def _describe_parts(val_str, labels, sep):
    raw = str(val_str) if pd.notna(val_str) else ""
    norm = _normalize_val(raw)
    parts = norm.split(sep)
    unknown, known = [], []
    for i, part in enumerate(parts):
        if i >= len(labels):
            break
        if re.search(r"UK|UNK", part, re.IGNORECASE):
            unknown.append(labels[i])
        else:
            known.append(labels[i])
    if not unknown:
        return "", ""
    missing_type = "、".join(unknown)
    if known:
        note = (f"{raw}，具体" + "、".join(known) + "已知，但"
                + "、".join(unknown) + "未知，发送质疑核实" + "、".join(unknown))
    else:
        note = f"{raw}，{sep == '-' and '日期' or '时间'}完全未知，发送质疑核实完整{sep == '-' and '日期' or '时间'}"
    return missing_type, note

# ── 1 读取：日期/时间字段元数据 ──

_meta_path = metadata_dir() / "FormField.json"
with open(_meta_path, encoding="utf-8") as _f:
    _meta = json.load(_f)

date_fields = [
    v for v in _meta["variables"]
    if v.get("fieldFormat", "") in (DATE_FORMATS + TIME_FORMATS)
]
print(f"日期/时间字段总数: {len(date_fields)}")

_fields_by_form = {}
for v in date_fields:
    _fields_by_form.setdefault(v["formOID"], []).append(v)

# ── 2 遍历表单、查找 UK/UNK 录入 ──

results = []

for form_oid, fields in _fields_by_form.items():
    try:
        df_sheet = load_sheet(form_oid, usecols=None)
    except Exception as e:
        print(f"  跳过 {form_oid}: {e}")
        continue

    sheet_cols = df_sheet.columns.tolist()
    all_sys_in_sheet = [c for c in _SYSTEM_COLS if c in sheet_cols]
    out_sys_in_sheet = [c for c in [_SUBJ, _VISIT, _FORMPG] if c in sheet_cols]

    for fmeta in fields:
        item_name = fmeta["itemName"]
        field_format = fmeta["fieldFormat"]
        form_name = fmeta.get("formName", form_oid)

        matched_cols = [c for c in sheet_cols if item_name in c and c not in all_sys_in_sheet]
        if not matched_cols:
            continue
        col = matched_cols[0]

        df_has = df_sheet[out_sys_in_sheet + [col]].copy()
        df_has = df_has.rename(columns={**_SYS_RENAME, col: VAR_VALUE})

        val_series = df_has[VAR_VALUE].fillna("").astype(str)
        mask = val_series.str.contains(r"UK|UNK", case=False, na=False)
        df_hit = df_has[mask].copy()
        if len(df_hit) == 0:
            continue

        df_hit[VAR_FORM] = form_name
        df_hit[VAR_FIELD] = item_name

        is_date = field_format in DATE_FORMATS
        _val_clean = df_hit[VAR_VALUE].apply(
            lambda x: _normalize_val(str(x)) if pd.notna(x) else x
        )
        if is_date:
            df_hit[VAR_YEAR]   = _extract_part(_val_clean, r"^(\d{2,4})-")
            df_hit[VAR_MONTH]  = _extract_part(_val_clean, r"-(\d{1,2})-")
            df_hit[VAR_DAY]    = _extract_part(_val_clean, r"-(\d{1,2})$")
            df_hit[VAR_HOUR]   = pd.NA
            df_hit[VAR_MINUTE] = pd.NA
        else:
            df_hit[VAR_HOUR]   = _extract_part(_val_clean, r"^(\d{1,2}):")
            df_hit[VAR_MINUTE] = _extract_part(_val_clean, r":(\d{2})$")
            df_hit[VAR_YEAR]   = pd.NA
            df_hit[VAR_MONTH]  = pd.NA
            df_hit[VAR_DAY]    = pd.NA

        missing_types, notes = [], []
        for _, row in df_hit.iterrows():
            if is_date:
                mt, note = _describe_parts(row[VAR_VALUE], ["年份", "月份", "日期"], "-")
            else:
                mt, note = _describe_parts(row[VAR_VALUE], ["小时", "分钟"], ":")
            missing_types.append(mt)
            notes.append(note)
        df_hit[VAR_MISSING] = missing_types
        df_hit[VAR_NOTE] = notes

        results.append(df_hit)

print()

# ── 3 合并结果 ──

if results:
    df_out = pd.concat(results, ignore_index=True)
else:
    df_out = pd.DataFrame(columns=OUTPUT_COLS)

# ── 4 格式化 ──

for c in [VAR_VISIT, VAR_FORMPG]:
    if c not in df_out.columns:
        df_out[c] = ""

df_out = df_out[OUTPUT_COLS]

for c in [VAR_YEAR, VAR_MONTH, VAR_DAY, VAR_HOUR, VAR_MINUTE]:
    df_out[c] = df_out[c].apply(lambda x: "" if pd.isna(x) else int(x))

# ── 5 输出 ──

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
