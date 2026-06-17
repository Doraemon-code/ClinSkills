"""
utils/loaders.py — 数据读取层

统一使用 load_sheet / load_rand 读取 EDC 导出的 Excel 数据。
"""

import json
import pandas as pd
from config import raw_path
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取 EDC 类型
_meta_path = _PROJECT_ROOT / "02 metadata" / "FormField.json"
with open(_meta_path, encoding="utf-8") as _f:
    _meta = json.load(_f)
EDC_TYPE = _meta.get("_meta", {}).get("edcType", "")


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
    form_name: str | None = None,
    dtype: dict | type | None = None,
) -> pd.DataFrame:
    """读取 EDC 导出 Excel 的指定 sheet。

    Args:
        form_oid: 表单 OID（即 sheet 名的核心部分）
        usecols: 只读取指定列（中文列名列表）
        form_name: 表单中文名（cmis 用于拼接 sheet 名；省略则自动从元数据查找）
        dtype: 列类型覆盖（传给 pd.read_excel 的 dtype 参数，用于保留前导零等）

    Returns:
        DataFrame
    """
    sheet = _resolve_sheet_name(form_oid, form_name)
    return pd.read_excel(raw_path, sheet_name=sheet, header=0, skiprows=[1], usecols=usecols, dtype=dtype)
