"""
config.py — 项目路径配置

从 config.yaml 加载数据路径，供各脚本直接 import。
"""

from pathlib import Path
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent
_CONFIG = _PROJECT_ROOT / "config.yaml"

with open(_CONFIG, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

raw_path    = str(_PROJECT_ROOT / _cfg["path"]["raw_path"])
pd_path     = str(_PROJECT_ROOT / _cfg["path"]["pd_path"])
code_path   = str(_PROJECT_ROOT / _cfg["path"]["code_path"])
remark_path = str(_PROJECT_ROOT / _cfg["path"]["remark_path"])
timewin_path = str(_PROJECT_ROOT / _cfg["path"]["timewin_path"])
output_path = str(_PROJECT_ROOT / _cfg["path"]["output_path"])
