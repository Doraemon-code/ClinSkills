"""
utils/loaders.py — 数据加载层

自包含定义所有数据读取函数：
  - load_sheet      ：底层单 sheet 读取（统一 dtype=str）
  - load_rand       ：DS_RAND 随机化信息
  - load_completion ：DS_END 试验完成情况
  - load_first_dose ：EC 首次服药日期

用法：
    from utils.loaders import load_sheet, load_rand, load_completion
"""

from pathlib import Path
import yaml
import pandas as pd

# 从 config.yaml 加载 raw_path（相对于 utils/ 所在目录的上一级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
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


def load_rand(cols, path=None, header=0, skiprows=None):
    """读取 DS_RAND（受试者随机化信息）。"""
    return load_sheet("DS_RAND", cols, path, header=header, skiprows=skiprows)


def load_completion(path=None):
    """读取 DS_END 并过滤为"试验完成情况总结"行。

    返回 DataFrame，含 ["受试者", "是否完成试验"] 两列。
    """
    df = load_sheet("DS_END", ["受试者", "页面名称", "受试者是否完成试验_TXT"], path).fillna("")
    df = df[df["页面名称"] == "试验总结表"].drop(columns="页面名称")
    df = df.rename(columns={"受试者是否完成试验_TXT": "是否完成试验"})
    return df


def load_first_dose(path=None):
    """读取 EC_ED，返回每受试者最早用药开始日期。"""
    ec = load_sheet("EC_ED", ["受试者", "开始日期"], path).fillna("")
    ec["开始日期"] = pd.to_datetime(ec["开始日期"], errors="coerce")
    ec = ec[ec["开始日期"].notna()]
    return (
        ec.groupby("受试者", dropna=False)["开始日期"]
        .min()
        .reset_index()
        .rename(columns={"开始日期": "首次用药日期"})
    )
