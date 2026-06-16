"""
loaders.py — 基础加载层（load_sheet）

提供 load_sheet 作为所有数据读取的底层函数。
领域专用 loader（load_rand、load_completion 等）放在 proj_utils/loaders.py。
"""

from pathlib import Path
import yaml
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_CONFIG = _PROJECT_ROOT / "config.yaml"
with open(_CONFIG, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)
raw_path = str(_PROJECT_ROOT / _cfg["path"]["raw_path"])


def load_sheet(sheet_name, cols, path=None, header=0, skiprows=None):
    """读取原始 Excel 的单个 sheet，统一 dtype=str。

    Parameters
    ----------
    sheet_name : str
        Sheet 名称。
    cols : list[str]
        需要的列名。
    path : str, optional
        Excel 文件路径，默认使用 raw_path。
    header : int, optional
        表头行号（0-indexed），默认 0。
    skiprows : list[int], optional
        需要跳过的行号列表。默认跳过第 1 行（即 header=0 时的第二行副标题）。

    Returns
    -------
    pd.DataFrame
    """
    if path is None:
        path = raw_path
    if skiprows is None:
        skiprows = [header + 1] if header == 0 else []
    return pd.read_excel(
        path, sheet_name=sheet_name,
        header=header, skiprows=skiprows,
        usecols=cols, dtype=str,
    )
