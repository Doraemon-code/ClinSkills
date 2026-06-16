"""
parse_taimei6.py
太美6 项目配置信息 Excel 解析模块。

输入: openpyxl.WorkBook
输出: dict[str, dict] — key 为 JSON 文件名（不含 .json），value 为该文件的数据

输出文件（通用命名，所有 EDC 解析器共用）:
  - VisitForm.json : 访视与表单的包含关系（Plan20）
  - FormField.json : 表单与字段的关系及字段属性（FormItem）
  - CodeList.json  : 完整编码表（CodeList + CodeListItems）
"""
from _compat import read_sheet, has_other


# ── CodeList ───────────────────────────────────────────────────


def _build_codelist(wb):
    """从 CodeList + CodeListItems 构建编码表字典。"""
    cli_rows = read_sheet(wb, "CodeListItems")

    codelist = {}
    for row in cli_rows:
        oid = row.get("CodeListOID")
        if not oid:
            continue
        if oid not in codelist:
            codelist[oid] = []
        dv = str(row.get("DisplayValue", "") or "")
        cv = str(row.get("CodedValue", "") or "")
        codelist[oid].append({"codedValue": cv, "displayValue": dv})

    return codelist


# ── FormField ──────────────────────────────────────────────────


def _build_form_fields(wb, codelist):
    """从 FormItem 构建字段列表。"""
    fi_rows = read_sheet(wb, "FormItem")
    variables = []
    for row in fi_rows:
        control_type = str(row.get("ControlType", "") or "").strip()

        # Label 类型跳过
        if control_type.lower() == "label":
            continue

        # 合并 ControlType + DataFormat → FieldFormat
        data_format = str(row.get("DataFormat", "") or "").strip()
        if control_type.lower() == "calendar" and data_format:
            field_format = data_format
        else:
            field_format = control_type

        rec = {
            "formOID": row.get("FormOID"),
            "formName": row.get("FormName"),
            "sasFieldName": row.get("SASFieldName"),
            "itemName": row.get("ItemName"),
            "fieldFormat": field_format,
        }

        # CodeListOID → name + count + hasOther（空值省略字段）
        # FormItem 的 CodeListOID 可能是内联格式 "CL.5=[Y|Yes,N|No]"，需提取 OID
        raw_cl = str(row.get("CodeListOID") or "").strip()
        cl_oid = raw_cl.split("=")[0].strip() if raw_cl else None
        if cl_oid and cl_oid in codelist:
            items = codelist[cl_oid]
            cl_ref = {"name": cl_oid, "count": len(items)}
            if any(has_other(item.get("displayValue")) for item in items):
                cl_ref["hasOther"] = True
            rec["codeList"] = cl_ref

        variables.append(rec)

    return variables


# ── VisitForm ──────────────────────────────────────────────────


def _build_visit_forms(wb):
    """从 Plan20 sheet 解析访视-表单矩阵。"""
    ws = wb["Plan20"]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    header = rows[0]
    visit_indices = []
    for i in range(1, len(header)):
        if header[i] and str(header[i]).strip():
            visit_indices.append(i)

    result = []
    for vi in visit_indices:
        visit_id = str(header[vi]).strip()
        forms = []
        for row in rows[1:]:
            if row[0] and vi < len(row) and row[vi] == "√":
                forms.append(str(row[0]).strip())
        result.append({"visit": visit_id, "forms": forms})
    return result


# ── 入口 ───────────────────────────────────────────────────────


def parse(wb, output_dir):
    """解析太美6元数据 Excel，返回要生成的 JSON 文件。

    输出（通用命名）:
      - VisitForm: 访视-表单包含关系
      - FormField: 表单-字段关系及属性
      - CodeList : 完整编码表
    """
    codelist = _build_codelist(wb)
    variables = _build_form_fields(wb, codelist)
    visit_forms = _build_visit_forms(wb)

    return {
        "VisitForm": {"visitForms": visit_forms},
        "FormField": {"variables": variables},
        "CodeList": codelist,
    }
