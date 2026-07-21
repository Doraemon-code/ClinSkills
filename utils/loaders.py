"""
utils/loaders.py — 数据读取层

统一使用 load_sheet 读取 EDC 导出的 Excel 数据；system_cols 解析系统列名。
"""

import json
import sys
import warnings
import pandas as pd
from config import raw_path
from pathlib import Path
from typing import overload

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# openpyxl MatchPattern 兼容 patch（太美6 AutoFilter ref 不规范等场景）
_compat_dir = str(_PROJECT_ROOT / ".claude" / "skills" / "build-metadata" / "scripts")
if _compat_dir not in sys.path:
    sys.path.insert(0, _compat_dir)
from _compat import ensure_openpyxl_patch
ensure_openpyxl_patch()

# EDC 导出的 xlsx 无默认样式，openpyxl 每次读取都抛此 UserWarning，与数据无关，静音。
warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style",
    category=UserWarning,
)

# 读取 EDC 类型
_meta_path = _PROJECT_ROOT / "02 metadata" / "FormField.json"
with open(_meta_path, encoding="utf-8") as _f:
    _meta = json.load(_f)
EDC_TYPE = _meta.get("_meta", {}).get("edcType", "")


def _detect_header_language() -> str:
    """根据 FormField.json 的 itemName 判断表头语言：zh 或 en。

    统计 CJK 与 ASCII 字母占比；相等或无法判断时默认 zh。
    """
    cjk = 0
    ascii_letters = 0
    for rec in _meta.get("variables", []):
        name = rec.get("itemName") or ""
        for ch in name:
            if "一" <= ch <= "鿿":
                cjk += 1
            elif ch.isascii() and ch.isalpha():
                ascii_letters += 1
    if cjk == 0 and ascii_letters == 0:
        return "zh"
    return "zh" if cjk >= ascii_letters else "en"


HEADER_LANGUAGE = _detect_header_language()

# ── 系统列注册表 ──
# 同一 EDC 系统的 rawdata 系统列跨研究固定，故作确定性知识登记于此。
# 模板/脚本通过 system_cols() 取值，函数体不硬编码系统列名。
# 新增 EDC 类型时在此补一行即可。
# 注：coding-guide.md「系统列」表是本注册表的文档副本，改此处（增删 EDC / 改列名）须同步该文件。
#
# 6 个角色可完全定位 EDC 中的每一个数据点：
#   center      中心编号
#   subject     筛选号
#   visit_name  访视名称
#   visit_seq   访视序号（标记访视重复）
#   form_name   表单名称
#   row         字段行号（标记表单内重复记录）
#
# taimei6 同时登记中/英两套系统列；运行时按 FormField itemName 语言自动选用。
_TAIMEI6_SYSTEM_COLUMNS: dict[str, dict[str, str]] = {
    "zh": {
        "center":     "中心编号",
        "subject":    "受试者编号",
        "visit_name": "表单集名称",
        "visit_seq":  "表单集记录号",
        "form_name":  "表单名称",
        "row":        "字段记录号",
    },
    "en": {
        "center":     "Site ID",
        "subject":    "Subject ID",
        "visit_name": "Formset Name",
        "visit_seq":  "Formset Repeat No.",
        "form_name":  "Form Name",
        "row":        "Item Repeat No.",
    },
}

SYSTEM_COLUMNS: dict[str, dict[str, str]] = {
    "clinflash": {
        "center":     "试验中心编号",
        "subject":    "受试者编号",
        "visit_name": "数据节",
        "visit_seq":  "Instance顺序号",
        "form_name":  "数据页",
        "row":        "行号",
    },
    "taimei5": {
        "center":     "中心编号",
        "subject":    "受试者",
        "visit_name": "访视名称",
        "visit_seq":  "访视号",
        "form_name":  "页面名称",
        "row":        "记录号",
    },
    "taimei6": _TAIMEI6_SYSTEM_COLUMNS.get(
        HEADER_LANGUAGE, _TAIMEI6_SYSTEM_COLUMNS["zh"]
    ),
    "cmis": {
        "center":     "SITEID",
        "subject":    "SUBJID",
        "visit_name": "VISIT",
        "visit_seq":  "VISITNUM",
        "form_name":  "FORMNAME",
        "row":        "TOPICSEQ",
    },
}


@overload
def system_cols(role: None = None) -> dict: ...
@overload
def system_cols(role: str) -> str: ...
def system_cols(role: str | None = None) -> dict | str:
    """返回当前 EDC 类型的系统列名。

    Args:
        role: 指定角色（center/subject/visit_name/visit_seq/form_name/row）
              则返回对应列名；省略则返回整 dict。

    Raises:
        ValueError: 当前 EDC 类型未登记，或已登记但缺少请求的角色——
                    提示在 SYSTEM_COLUMNS 中补全。
    """
    cols = SYSTEM_COLUMNS.get(EDC_TYPE)
    if cols is None:
        raise ValueError(
            f"EDC 类型 '{EDC_TYPE}' 未在 utils/loaders.py 的 SYSTEM_COLUMNS 登记，"
            f"请补全该 EDC 的系统列名（center/subject/visit_name/visit_seq/form_name/row）。"
        )
    if role is None:
        return cols
    if role not in cols:
        raise ValueError(
            f"EDC '{EDC_TYPE}' 未登记系统列角色 '{role}'，"
            f"请在 utils/loaders.py 的 SYSTEM_COLUMNS['{EDC_TYPE}'] 补全。"
        )
    return cols[role]


def _resolve_sheet_name(form_oid: str, form_name: str | None = None) -> str:
    """根据 EDC 类型构造实际 sheet 名称。

    cmis 的 sheet 名为 '{formOID}--{formName}'，
    taimei5/taimei6 的 sheet 名直接是 formOID。
    """
    if EDC_TYPE == "cmis":
        if form_name is None:
            # 从元数据自动查找 formName
            for rec in _meta["variables"]:
                if rec["formOID"] == form_oid:
                    form_name = rec["formName"]
                    break
        if form_name:
            return f"{form_oid}--{form_name}"
    return form_oid


def load_sheet(
    form_oid: str,
    usecols: list[str] | None = None,
    cols: list[str] | None = None,
    form_name: str | None = None,
    dtype: dict | type | None = None,
) -> pd.DataFrame:
    """读取 EDC 导出 Excel 的指定 sheet。

    Args:
        form_oid: 表单 OID（即 sheet 名的核心部分）
        usecols / cols: 只读取指定列（EDC 实际列名列表：字段标签或 SAS 名），cols 为 usecols 的别名
        form_name: 表单中文名（cmis 用于拼接 sheet 名；省略则自动从元数据查找）
        dtype: 列类型覆盖（传给 pd.read_excel 的 dtype 参数，用于保留前导零等）

    Returns:
        DataFrame
    """
    sheet = _resolve_sheet_name(form_oid, form_name)
    # 受试者(筛选号)、随机号为 ID 编码，强制 str 读取以保留前导零；
    # pandas 会忽略 sheet 中不存在的 dtype 键，故对所有 sheet 传入无副作用。
    # 注：此处硬编码的"随机号"是字段标签字面量，仅命中标签恰为"随机号"的表头（clinflash/taimei 常见）；
    #     cmis（用 SAS 名）或英文标签项目命不中，其随机号列需 caller 显式传 dtype 强制 str。
    # caller 显式传入的 dtype 优先（dict 合并覆盖，或整体替换）。
    id_dtype = {system_cols("subject"): str, "随机号": str}
    if isinstance(dtype, dict):
        eff_dtype = {**id_dtype, **dtype}
    elif dtype is not None:
        eff_dtype = dtype
    else:
        eff_dtype = id_dtype
    kwargs = {"header": 0, "usecols": usecols or cols, "dtype": eff_dtype}
    if EDC_TYPE != "clinflash":
        kwargs["skiprows"] = [1]
    return pd.read_excel(raw_path, sheet_name=sheet, **kwargs)
