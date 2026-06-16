"""
query_metadata.py — 元数据查询工具

从 VisitForm.json / FormField.json / CodeList.json 中查询信息，
辅助编写数据核查脚本时确定需要哪些表、哪些列、编码值等。

用法:
    python query_metadata.py <command> [args...]

命令:
    forms                       列出所有表单（formName）
    fields <formName>           列出指定表单的所有字段
    search <keyword>            在所有表单中搜索含关键字的字段
    codelist <name>             查看指定编码表的枚举值
    codelists                   列出所有编码表名称及条目数
    visits                      列出所有访视及关联表单
    find-field <sasFieldName>   按 SAS 字段名精确查找字段所在表单
    field-codelist <fieldName>  根据字段名（SAS名或中文标签）查询其编码表枚举值
    summary                     输出元数据概览（表单数、字段数、编码表数）
"""

import json
import sys
from pathlib import Path

def _resolve_metadata_dir():
    """定位 metadata 目录（含 FormField.json）。

    优先项目根 `metadata/`；找不到则向下搜索最近的 `metadata/FormField.json`，
    以兼容 study 子目录布局。
    """
    project_root = Path(__file__).resolve().parents[4]
    default = project_root / "metadata"
    if (default / "FormField.json").exists():
        return default
    for p in sorted(project_root.glob("**/metadata/FormField.json")):
        return p.parent
    return default


METADATA_DIR = _resolve_metadata_dir()

def _load(name):
    p = METADATA_DIR / f"{name}.json"
    if not p.exists():
        print(f"错误: 找不到 {p}，请先运行 build-metadata 生成元数据。")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cmd_forms():
    """列出所有表单。"""
    ff = _load("FormField")
    forms = {}
    for v in ff.get("variables", []):
        name = v.get("formName", "")
        oid = v.get("formOID", "")
        if name and name not in forms:
            forms[name] = oid
    print(f"共 {len(forms)} 个表单:\n")
    for name, oid in forms.items():
        n_fields = sum(1 for v in ff["variables"] if v.get("formName") == name)
        print(f"  {name}  (OID={oid}, {n_fields} 字段)")


def cmd_fields(form_name):
    """列出指定表单的所有字段。"""
    ff = _load("FormField")
    matched = [v for v in ff.get("variables", [])
               if v.get("formName") == form_name or v.get("formOID") == form_name]
    if not matched:
        # 模糊匹配
        matched = [v for v in ff.get("variables", [])
                   if form_name in v.get("formName", "") or form_name in v.get("formOID", "")]
        if matched:
            print(f"未精确匹配 '{form_name}'，模糊匹配到表单 '{matched[0]['formName']}':")
        else:
            print(f"未找到表单 '{form_name}'。")
            _suggest_forms(form_name)
            return
    print(f"表单: {matched[0].get('formName', '')}  (共 {len(matched)} 字段)\n")
    print(f"{'SAS字段名':<20} {'字段标签':<30} {'字段格式':<20} {'编码表':<25} {'脚本列名'}")
    print("-" * 110)
    for v in matched:
        cl = v.get("codeList")
        cl_str = ""
        col_name = v.get("itemName", "")
        if cl:
            cl_str = f"{cl['name']} ({cl['count']}项)"
            if cl.get("hasOther"):
                cl_str += " [含其他]"
            col_name = f"{v.get('itemName', '')}_TXT  ← 用此列"
        print(f"{v.get('sasFieldName',''):<20} {v.get('itemName',''):<30} {v.get('fieldFormat',''):<20} {cl_str:<25} {col_name}")


def cmd_search(keyword):
    """在所有表单中搜索含关键字的字段。"""
    ff = _load("FormField")
    matched = [v for v in ff.get("variables", [])
               if keyword in v.get("itemName", "")
               or keyword in v.get("sasFieldName", "")
               or keyword in v.get("formName", "")
               or keyword in v.get("formOID", "")]
    if not matched:
        print(f"未找到含 '{keyword}' 的字段。")
        return
    print(f"搜索 '{keyword}' 命中 {len(matched)} 个字段:\n")
    for v in matched:
        cl = v.get("codeList")
        cl_str = ""
        if cl:
            cl_str = f"  编码表:{cl['name']}({cl['count']}项)"
            if cl.get("hasOther"):
                cl_str += "[含其他]"
        print(f"  [{v.get('formName','')}] {v.get('sasFieldName','')} = {v.get('itemName','')}  ({v.get('fieldFormat','')}){cl_str}")


def cmd_codelist(name):
    """查看指定编码表的枚举值。"""
    cl = _load("CodeList")
    if name in cl:
        items = cl[name]
        print(f"编码表 {name} ({len(items)} 项):\n")
        for item in items:
            print(f"  {item['codedValue']}: {item['displayValue']}")
    else:
        # 模糊匹配
        matches = [k for k in cl if name.lower() in k.lower()]
        if matches:
            print(f"未精确匹配 '{name}'，相似编码表:")
            for m in matches:
                print(f"  {m} ({len(cl[m])} 项)")
        else:
            print(f"未找到编码表 '{name}'。")


def cmd_codelists():
    """列出所有编码表。"""
    cl = _load("CodeList")
    print(f"共 {len(cl)} 个编码表:\n")
    for name, items in cl.items():
        print(f"  {name}: {len(items)} 项")
        for item in items[:3]:
            print(f"    {item['codedValue']}: {item['displayValue']}")
        if len(items) > 3:
            print(f"    ... (共 {len(items)} 项)")


def cmd_visits():
    """列出所有访视及关联表单。"""
    vf = _load("VisitForm")
    visits = vf.get("visitForms", [])
    print(f"共 {len(visits)} 个访视:\n")
    for v in visits:
        forms = v.get("forms", [])
        print(f"  {v['visit']} ({len(forms)} 个表单)")
        for f in forms:
            print(f"    - {f}")


def cmd_find_field(sas_name):
    """按 SAS 字段名查找所在表单。"""
    ff = _load("FormField")
    matched = [v for v in ff.get("variables", [])
               if v.get("sasFieldName", "").upper() == sas_name.upper()
               or v.get("sasFieldName", "") == sas_name]
    if not matched:
        # 模糊匹配
        matched = [v for v in ff.get("variables", [])
                   if sas_name.upper() in v.get("sasFieldName", "").upper()]
    if not matched:
        print(f"未找到字段 '{sas_name}'。")
        return
    print(f"字段 '{sas_name}' 找到 {len(matched)} 处:\n")
    for v in matched:
        cl = v.get("codeList")
        cl_str = ""
        if cl:
            cl_str = f"  编码表:{cl['name']}({cl['count']}项)"
        print(f"  表单: {v.get('formName','')} (OID={v.get('formOID','')})")
        print(f"    标签: {v.get('itemName','')}  格式: {v.get('fieldFormat','')}{cl_str}")


def cmd_field_codelist(field_name):
    """根据字段名（SAS 名或中文标签）查询其编码表枚举值。"""
    ff = _load("FormField")
    cl_data = _load("CodeList")

    # 按 SAS 字段名或中文标签匹配
    matched = [v for v in ff.get("variables", [])
               if v.get("sasFieldName", "") == field_name
               or v.get("itemName", "") == field_name]
    if not matched:
        # 模糊匹配
        matched = [v for v in ff.get("variables", [])
                   if field_name in v.get("sasFieldName", "")
                   or field_name in v.get("itemName", "")]
    if not matched:
        print(f"未找到字段 '{field_name}'。")
        return

    # 提取有编码表的字段
    with_cl = [v for v in matched if v.get("codeList")]
    if not with_cl:
        print(f"字段 '{field_name}' 找到 {len(matched)} 处，但均无编码表:\n")
        for v in matched:
            print(f"  [{v.get('formName','')}] {v.get('sasFieldName','')} = {v.get('itemName','')}  ({v.get('fieldFormat','')})")
        return

    # 按编码表去重输出
    seen = set()
    for v in with_cl:
        cl_name = v["codeList"]["name"]
        if cl_name in seen:
            continue
        seen.add(cl_name)
        items = cl_data.get(cl_name, [])
        has_other = " [含'其他'选项]" if v["codeList"].get("hasOther") else ""
        print(f"字段 {v.get('sasFieldName','')}（{v.get('itemName','')}）→ 编码表 {cl_name}{has_other} ({len(items)} 项):\n")
        for item in items:
            print(f"  {item['codedValue']}: {item['displayValue']}")
        print()

    # 输出无编码表的匹配字段（如有）
    without_cl = [v for v in matched if not v.get("codeList")]
    if without_cl:
        print(f"另有 {len(without_cl)} 处匹配字段无编码表:")
        for v in without_cl:
            print(f"  [{v.get('formName','')}] {v.get('sasFieldName','')} = {v.get('itemName','')}  ({v.get('fieldFormat','')})")


def cmd_summary():
    """元数据概览。"""
    vf = _load("VisitForm")
    ff = _load("FormField")
    cl = _load("CodeList")

    visits = vf.get("visitForms", [])
    variables = ff.get("variables", [])
    forms = set(v.get("formName", "") for v in variables if v.get("formName"))

    print("=== 元数据概览 ===\n")
    print(f"  访视数:   {len(visits)}")
    print(f"  表单数:   {len(forms)}")
    print(f"  字段数:   {len(variables)}")
    print(f"  编码表数: {len(cl)}")

    # 有编码表引用的字段数
    with_cl = sum(1 for v in variables if v.get("codeList"))
    with_other = sum(1 for v in variables if v.get("codeList", {}).get("hasOther"))
    print(f"  带编码表字段: {with_cl}")
    print(f"  含'其他'选项: {with_other}")


def _suggest_forms(keyword):
    ff = _load("FormField")
    forms = sorted(set(v.get("formName", "") for v in ff.get("variables", []) if v.get("formName")))
    print("可用表单:")
    for f in forms:
        print(f"  - {f}")


COMMANDS = {
    "forms": cmd_forms,
    "fields": cmd_fields,
    "search": cmd_search,
    "codelist": cmd_codelist,
    "codelists": cmd_codelists,
    "visits": cmd_visits,
    "find-field": cmd_find_field,
    "field-codelist": cmd_field_codelist,
    "summary": cmd_summary,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("用法: python query_metadata.py <command> [args...]\n")
        print("命令:")
        print("  forms                 列出所有表单")
        print("  fields <formName>     列出指定表单的所有字段")
        print("  search <keyword>      搜索含关键字的字段")
        print("  codelist <name>       查看编码表枚举值")
        print("  codelists             列出所有编码表")
        print("  visits                列出所有访视及关联表单")
        print("  find-field <name>     按 SAS 字段名查找")
        print("  field-codelist <name> 根据字段名查询编码表枚举值")
        print("  summary               元数据概览")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in ("forms", "codelists", "visits", "summary"):
        COMMANDS[cmd]()
    elif cmd in ("fields", "search", "codelist", "find-field", "field-codelist"):
        if not args:
            print(f"错误: '{cmd}' 需要一个参数。")
            sys.exit(1)
        COMMANDS[cmd](args[0])
    else:
        COMMANDS[cmd](*args)


if __name__ == "__main__":
    main()
