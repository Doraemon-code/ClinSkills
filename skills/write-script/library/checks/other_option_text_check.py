# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 核查「其他」选项的自由文本：选了「其他/其它」时，配套文本字段
#       是否为空、或与已设预设选项重复。COMPANION_MAP 给出
#       (formOID, fieldOID) → 配套自由文本 fieldOID 的映射，按项目填写。
# @tags 其他,自由文本,hasOther,编码表,companion,选项核查
# @config COMPANION_MAP, OTHER_TOKENS

import sys, json
from pathlib import Path
from collections import defaultdict

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_listing_dir
from utils.output_format import export_to_one_excel_with_format
from utils.loaders import load_sheet, system_cols, metadata_dir

# ── 系统列（读取用 EDC 专属名，输出 rename 为通用中文标签）──

_SYS = system_cols()
_SU = _SYS["subject"]
_RO = _SYS["row"]

_OUT_SUBJ = "筛选号"
_OUT_ROW  = "行号"
_SYS_RENAME = {_SU: _OUT_SUBJ, _RO: _OUT_ROW}

# ── 项目配置（按本项目元数据调整）──

CHECK_NAME = "其他选项自由文本核查"

# (formOID, 选项字段标识) → 配套自由文本字段标识
# 标识取值：clinflash 用 fieldOID，taimei/cmis 用 SAS 变量名；用 query_metadata.py fields 查询
# 选「其他」时必填的文本列即配套列
COMPANION_MAP = {
    ("DS_ICF",  "DSVER2"):   "DSVEROT",
    ("DM",      "ETHNIC"):   "ETHNICOT",
    ("RP",      "RPCAT"):    "RPCATOT",
    ("MH_SD",   "MHCAT"):    "MHCATOT",
    ("PR_HPV",  "PRCAT"):    "PRCATOT",
    ("VS",      "VSCOM"):    "VSDESC",
    ("PE",      "PECOM"):    "PEDESC",
    ("EG",      "EGCOM"):    "EGDESC",
    ("CM",      "CMDOSU"):   "CMDOSUOT",
    ("CM",      "CMDOSFRQ"): "CMFRQOT",
    ("CM",      "CMROUTE"):  "CMROUOT",
    ("CM",      "CMINDC"):   "CMDESC",
    ("AE",      "AEACNOTH"): "AEACNOT",
}

# 识别"其他"选项的显示值关键词（跨 EDC 语言）——英文项目改为 ("Other",)
OTHER_TOKENS = ("其他", "其它")

# ── 列名 ──

VAR_SUBJ   = _SU       # 读取名（clinflash→受试者编号 / taimei5→受试者 / taimei6→受试者编号）
VAR_ROW    = _RO       # 读取名（clinflash→行号 / taimei5→记录号 / taimei6→字段记录号）
VAR_FORM   = "表单"
VAR_FIELD  = "字段"
VAR_VALUE  = "选项值"
VAR_TEXT   = "自由文本"
VAR_RESULT = "核查结果"
# issues 用读取名构造，rename 后输出
_OUTPUT_COLS_RAW = [VAR_SUBJ, VAR_ROW, VAR_FORM, VAR_FIELD, VAR_VALUE, VAR_TEXT, VAR_RESULT]
OUTPUT_COLS = [_OUT_SUBJ, _OUT_ROW, VAR_FORM, VAR_FIELD, VAR_VALUE, VAR_TEXT, VAR_RESULT]

# ── 1 读取元数据，构建列名 + 已设选项 ──

_meta_dir = metadata_dir()
_ff = json.load(open(_meta_dir / "FormField.json", encoding="utf-8"))
_cl = json.load(open(_meta_dir / "CodeList.json", encoding="utf-8"))

_EDC_TYPE = _ff.get("_meta", {}).get("edcType", "")

def _col_name(v):
    """按 EDC 类型还原数据列名：clinflash→{itemName}({fieldOID})；taimei→itemName；cmis→sasFieldName。"""
    item = v.get("itemName", "")
    if _EDC_TYPE == "clinflash":
        oid = v.get("fieldOID", "")
        return f"{item}({oid})" if item and oid else item
    if _EDC_TYPE == "cmis":
        return v.get("sasFieldName", item)
    return item  # taimei5/6 及未知类型默认字段标签

_field_info = {}
for v in _ff["variables"]:
    key = (v["formOID"], v.get("fieldOID") or v.get("sasFieldName"))
    if key not in _field_info:
        _field_info[key] = {
            "itemName":     v["itemName"],
            "formName":     v["formName"],
            "codeListName": v.get("codeList", {}).get("name", ""),
            "colName":      _col_name(v),
        }

_form_fields = defaultdict(list)
for (fid, foid), comp_oid in COMPANION_MAP.items():
    fi = _field_info.get((fid, foid))
    ci = _field_info.get((fid, comp_oid))
    if not fi or not ci:
        print(f"  跳过 ({fid}, {foid}): 元数据中找不到")
        continue
    cl_name = fi["codeListName"]
    cl_items = _cl.get(cl_name, [])
    other_vals = [it["displayValue"] for it in cl_items
                  if any(t in it["displayValue"] for t in OTHER_TOKENS)]
    preset = [it["displayValue"] for it in cl_items
              if not any(t in it["displayValue"] for t in OTHER_TOKENS)]
    _form_fields[fid].append({
        "fieldOID":     foid,
        "itemName":     fi["itemName"],
        "formName":     fi["formName"],
        "colName":      fi["colName"],
        "companionCol": ci["colName"],
        "otherVals":    other_vals,
        "preset":       preset,
    })

print(f"待核查表单 {len(_form_fields)} 个，字段对 {sum(len(v) for v in _form_fields.values())} 组")

# ── 2 逐表加载 + 筛选「其他」行 + 核查自由文本 ──

issues = []

for fid, fields in _form_fields.items():
    # 行号为系统列，rawdata 普遍存在（不在 FormField 元数据里，故不能靠元数据判断有无）
    usecols = [VAR_SUBJ, VAR_ROW]
    for f in fields:
        usecols.append(f["colName"])
        usecols.append(f["companionCol"])
    usecols = list(dict.fromkeys(usecols))

    try:
        df = load_sheet(fid, usecols=usecols)
    except Exception:
        # 个别无行号列的表：回退为不含行号
        usecols = [c for c in usecols if c != VAR_ROW]
        try:
            df = load_sheet(fid, usecols=usecols)
        except Exception as e:
            print(f"  跳过 {fid}: {e}")
            continue

    has_row = VAR_ROW in df.columns

    for f in fields:
        col, comp = f["colName"], f["companionCol"]
        if col not in df.columns or comp not in df.columns:
            continue
        other_vals = f["otherVals"]
        if not other_vals:
            continue

        mask = df[col].astype(str).apply(lambda x: any(ov in x for ov in other_vals))
        df_hit = df[mask]
        if df_hit.empty:
            continue

        for _, row in df_hit.iterrows():
            raw_text = row[comp]
            text_str = str(raw_text).strip() if pd.notna(raw_text) else ""
            if text_str in ("nan", "None"):
                text_str = ""

            if not text_str:
                result = "自由文本为空"
            elif any(text_str.lower() == p.lower() for p in f["preset"]):
                result = f"与已设选项重复：{text_str}"
            else:
                continue

            issues.append({
                VAR_SUBJ:   row.get(VAR_SUBJ, ""),
                VAR_ROW:    row.get(VAR_ROW, "") if has_row else "",
                VAR_FORM:   f["formName"],
                VAR_FIELD:  f["itemName"],
                VAR_VALUE:  row[col],
                VAR_TEXT:   text_str,
                VAR_RESULT: result,
            })

    print(f"  {fid}: 累计 {len(issues)} 条")

# ── 3 格式化 ──

df_out = pd.DataFrame(issues, columns=_OUTPUT_COLS_RAW)
df_out = df_out.rename(columns=_SYS_RENAME)
df_out = df_out[OUTPUT_COLS]

# ── 4 输出 ──

n = len(df_out)
title = CHECK_NAME
export_to_one_excel_with_format(
    df_out,
    f"{output_listing_dir}/{title}.xlsx",
    title,
    f"{title}（{n}条）",
    add_title=True,
)
