"""
parse_clinflash.py
ClinFlash SDS Excel 解析模块。

输入: openpyxl.WorkBook
输出: dict[str, dict] — key 为 JSON 文件名（不含 .json），value 为该文件的数据

输出文件（通用命名，所有 EDC 解析器共用）:
  - VisitForm.json : 访视与表单的包含关系（Folder + FolderModule）
  - FormField.json : 表单与字段的关系及字段属性（Field + Form）
  - CodeList.json  : 完整编码表（DataDictionary + DataDictionaryEntry）
"""
from _compat import read_sheet, has_other


# ── CodeList ───────────────────────────────────────────────────


def _build_codelist(wb):
    """从 DataDictionary + DataDictionaryEntry 构建编码表字典。

    返回: {dataDictionaryOID: [...items]}
    """
    # DataDictionary: OID -> name 映射
    dd_rows = read_sheet(wb, "DataDictionary")
    dd_names = {}
    for row in dd_rows:
        oid = row.get("dataDictionaryOID")
        name = row.get("dataDictionaryName")
        if oid and name:
            dd_names[oid] = name

    # DataDictionaryEntry: 按 dataDictionaryOID 分组
    dde_rows = read_sheet(wb, "DataDictionaryEntry")
    codelist = {}
    for row in dde_rows:
        oid = row.get("dataDictionaryOID")
        if not oid:
            continue
        name = dd_names.get(oid, oid)
        if name not in codelist:
            codelist[name] = []
        cv = str(row.get("entryOID", "") or "")
        dv = str(row.get("itemDataString", "") or "")
        codelist[name].append({"codedValue": cv, "displayValue": dv})

    return codelist


# ── FormField ──────────────────────────────────────────────────


def _build_form_fields(wb, codelist):
    """从 Field + Form sheet 构建字段列表。"""
    # Form: formOID -> formName 映射
    form_rows = read_sheet(wb, "Form")
    form_names = {}
    for row in form_rows:
        oid = row.get("formOID")
        name = row.get("formName")
        if oid and name:
            form_names[oid] = name

    # DataDictionary: OID -> Name 映射（用于字段 → 编码表查找）
    dd_rows = read_sheet(wb, "DataDictionary")
    oid_to_name = {}
    for row in dd_rows:
        oid = row.get("dataDictionaryOID")
        name = row.get("dataDictionaryName")
        if oid and name:
            oid_to_name[oid] = name

    fi_rows = read_sheet(wb, "Field")
    variables = []
    for row in fi_rows:
        control_type = str(row.get("controlType", "") or "").strip()

        # 合并 controlType + dataFormat → fieldFormat
        data_format = str(row.get("dataFormat", "") or "").strip()
        if control_type == "日期框" and data_format:
            field_format = data_format
        else:
            field_format = control_type

        form_oid = row.get("formOID")
        rec = {
            "formOID": form_oid,
            "formName": form_names.get(form_oid, form_oid),
            "fieldOID": row.get("fieldOID"),
            "sasFieldName": row.get("SASText"),
            "itemName": row.get("fieldName"),
            "fieldFormat": field_format,
        }

        # dataDictionaryOID → codeList 引用（name + count + hasOther）
        cl_oid = str(row.get("dataDictionaryOID") or "").strip()
        if cl_oid:
            cl_name = oid_to_name.get(cl_oid, cl_oid)
            if cl_name in codelist:
                items = codelist[cl_name]
                cl_ref = {"name": cl_name, "count": len(items)}
                if any(has_other(item.get("displayValue")) for item in items):
                    cl_ref["hasOther"] = True
                rec["codeList"] = cl_ref

        variables.append(rec)

    return variables


# ── VisitForm ──────────────────────────────────────────────────


def _build_visit_forms(wb):
    """从 Folder + FolderModule 构建访视-表单矩阵。

    Folder: 访视期（folderOID, folderName）
    FolderModule: 访视-模块关联（folderOID, moduleOID）
    模块 OID 与表单 OID 是一一对应的 → moduleOID 即 formOID
    """
    # Folder: folderOID -> folderName
    f_rows = read_sheet(wb, "Folder")
    folders = {}
    for row in f_rows:
        oid = row.get("folderOID")
        name = row.get("folderName")
        if oid and name:
            folders[str(oid)] = str(name).strip()

    # FolderModule: folderOID -> [moduleOID, ...]
    fm_rows = read_sheet(wb, "FolderModule")
    visit_forms_map = {}
    for row in fm_rows:
        f_oid = str(row.get("folderOID") or "")
        m_oid = str(row.get("moduleOID") or "")
        if not f_oid or not m_oid:
            continue
        if f_oid not in visit_forms_map:
            visit_forms_map[f_oid] = []
        if m_oid not in visit_forms_map[f_oid]:
            visit_forms_map[f_oid].append(m_oid)

    result = []
    for f_oid, f_name in folders.items():
        forms = visit_forms_map.get(f_oid, [])
        result.append({"visit": f_name, "forms": forms})

    return result


# ── 入口 ───────────────────────────────────────────────────────


def parse(wb, output_dir):
    """解析 ClinFlash SDS Excel，返回要生成的 JSON 文件。

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
