"""
parse_cmis.py
赛美斯(CMIS) DED Excel 解析模块。

输入: openpyxl.WorkBook
输出: dict[str, dict] — key 为 JSON 文件名（不含 .json），value 为该文件的数据

输出文件（通用命名，所有 EDC 解析器共用）:
  - VisitForm.json : 访视与表单的包含关系（访视流程）
  - FormField.json : 表单与字段的关系及字段属性（变量列表）
  - CodeList.json  : 完整编码表（受控术语）
"""
from _compat import read_sheet, has_other


def _build_codelist(rows):
    """从受控术语行构建 CodeList 字典，按受控术语名称分组。

    返回: {name: {"items": [...], "hasOther": bool}}
    """
    codelist = {}
    for row in rows:
        name = row.get("受控术语")
        if not name:
            continue
        if name not in codelist:
            codelist[name] = {"items": [], "hasOther": False}
        code_val = row.get("Code Value", "")
        code_text = row.get("Code Text", "")
        codelist[name]["items"].append({
            "codedValue": str(code_val) if code_val is not None else "",
            "displayValue": str(code_text) if code_text is not None else "",
        })
        if has_other(code_text):
            codelist[name]["hasOther"] = True
    return codelist


def _build_visit_forms(rows):
    """从访视流程行构建 VisitForm 列表，前向填充访视信息。"""
    result = []
    current_visit = None
    current_forms = []

    for row in rows:
        visit_name = row.get("访视阶段")
        if visit_name:
            # 新访视开始，保存上一个
            if current_visit is not None:
                result.append({"visit": current_visit, "forms": current_forms})
            current_visit = str(visit_name).strip()
            current_forms = []

        form_name = row.get("表单名称")
        if form_name and current_visit is not None:
            current_forms.append(str(form_name).strip())

    # 保存最后一个访视
    if current_visit is not None:
        result.append({"visit": current_visit, "forms": current_forms})

    return result


def parse(wb):
    """解析赛美斯 DED Excel，返回要生成的 JSON 文件。

    输出（通用命名）:
      - VisitForm: 访视-表单包含关系
      - FormField: 表单-字段关系及属性
      - CodeList : 完整编码表
    """
    # ── 1. CodeList（从受控术语） ──────────────────────────────
    ct_rows = read_sheet(wb, "受控术语")
    codelist = _build_codelist(ct_rows)

    # ── 2. FormField（从变量列表） ─────────────────────────────
    vl_rows = read_sheet(wb, "变量列表")
    variables = []
    for row in vl_rows:
        rec = {
            "formOID": row.get("表单代码"),
            "formName": row.get("表单名称"),
            "sasFieldName": row.get("变量名称"),
            "itemName": row.get("变量标签"),
            "fieldFormat": row.get("控件类型"),
        }

        # codeList 引用：名称 + 条目数 + hasOther
        cl_name = row.get("受控术语")
        if cl_name and cl_name in codelist:
            cl_info = codelist[cl_name]
            cl_ref = {"name": cl_name, "count": len(cl_info["items"])}
            if cl_info["hasOther"]:
                cl_ref["hasOther"] = True
            rec["codeList"] = cl_ref

        variables.append(rec)

    # ── 3. VisitForm（从访视流程） ─────────────────────────────
    vf_rows = read_sheet(wb, "访视流程")
    visit_forms = _build_visit_forms(vf_rows)

    # ── CodeList 输出只保留 items 列表 ────────────────────────
    codelist_out = {name: info["items"] for name, info in codelist.items()}

    # ── 返回（通用文件名） ─────────────────────────────────────
    return {
        "VisitForm": {"visitForms": visit_forms},
        "FormField": {"variables": variables},
        "CodeList": {"codeLists": codelist_out},
    }
