"""
parse_taimei5.py
太美5 项目配置信息 Excel 解析模块。

输入: openpyxl.WorkBook
输出: dict[str, dict] — key 为 JSON 文件名（不含 .json），value 为该文件的数据

输出文件（通用命名，所有 EDC 解析器共用）:
  - VisitForm.json : 访视与表单的包含关系（EventWorkflow）
  - FormField.json : 表单与字段的关系及字段属性（DataStructure）
  - CodeList.json  : 完整编码表（从 DataStructure.CodeListOID 内联格式解析）
"""
import re
from _compat import read_sheet, has_other


def _parse_code_list_oid(raw):
    """解析内联 CodeListOID 字符串，返回 (name, items_list) 或 None。

    格式示例: "DS.3=[1|受试者撤回知情同意,2|试验期间...,99|其他,]"
    """
    if not raw or "=" not in str(raw):
        return None
    match = re.match(r'^(.+?)=\[(.+)\]$', str(raw).strip())
    if not match:
        return None
    name = match.group(1)
    items = []
    for pair in match.group(2).split(","):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split("|", 1)
        if len(parts) == 2:
            items.append({"codedValue": parts[0], "displayValue": parts[1]})
    return name, items


def _build_codelist(data_rows):
    """从 DataStructure 行中提取所有 CodeList，按 OID 分组去重。"""
    codelist_dict = {}
    for row in data_rows:
        parsed = _parse_code_list_oid(row.get("CodeListOID"))
        if parsed is None:
            continue
        name, items = parsed
        if name not in codelist_dict:
            codelist_dict[name] = items
    return codelist_dict


def _build_visit_forms(wb):
    """从 EventWorkflow sheet 解析访视-表单矩阵。"""
    if "EventWorkflow" not in wb.sheetnames:
        return []
    ew = wb["EventWorkflow"]
    rows = list(ew.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    header = rows[0]
    # 收集有效访视列（跳过第一列 CRF\Visit 和空列头）
    visit_indices = []
    for i in range(1, len(header)):
        if header[i] and str(header[i]).strip():
            visit_indices.append(i)

    result = []
    for vi in visit_indices:
        visit_name = str(header[vi]).strip()
        forms = []
        for row in rows[1:]:
            if row[0] and vi < len(row) and row[vi] == "√":
                forms.append(str(row[0]).strip())
        result.append({"visit": visit_name, "forms": forms})
    return result


def parse(wb, output_dir):
    """解析太美5元数据 Excel，返回要生成的 JSON 文件。

    输出（通用命名）:
      - VisitForm: 访视-表单包含关系
      - FormField: 表单-字段关系及属性
      - CodeList : 完整编码表
    """
    # ── 1. FormField（从 DataStructure） ────────────────────────
    ds_rows = read_sheet(wb, "DataStructure")
    variables = []
    for row in ds_rows:
        # DisplayMode == Label 的行跳过
        if str(row.get("DisplayMode", "")).strip().lower() == "label":
            continue

        # 合并 DisplayMode + DataFormat → FieldFormat
        dm = str(row.get("DisplayMode", "") or "").strip()
        df = str(row.get("DataFormat", "") or "").strip()
        if dm.lower() == "datetime" and df:
            field_format = df
        else:
            field_format = dm

        rec = {
            "formOID": row.get("FormOID"),
            "formName": row.get("FormName"),
            "sasFieldName": row.get("SASFieldName"),
            "itemName": row.get("ItemName"),
            "fieldFormat": field_format,
        }

        # CodeListOID → name + count（空值省略字段）
        parsed = _parse_code_list_oid(row.get("CodeListOID"))
        if parsed is not None:
            name, items = parsed
            cl_ref = {"name": name, "count": len(items)}
            if any(has_other(item.get("displayValue")) for item in items):
                cl_ref["hasOther"] = True
            rec["codeList"] = cl_ref

        variables.append(rec)

    # ── 2. CodeList（完整编码表，独立文件） ─────────────────────
    codelist_dict = _build_codelist(ds_rows)

    # ── 3. VisitForm（从 EventWorkflow） ───────────────────────
    visit_forms = _build_visit_forms(wb)

    # ── 返回（通用文件名） ─────────────────────────────────────
    return {
        "VisitForm": {"visitForms": visit_forms},
        "FormField": {"variables": variables},
        "CodeList": codelist_dict,
    }
