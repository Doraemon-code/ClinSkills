#!/usr/bin/env python
"""PreToolUse 钩子：严禁不经同意直接读取 raw 原始数据；允许直接读取 metadata。

由 .claude/settings.json 的 PreToolUse 钩子调用（matcher: Bash|Read|PowerShell），读取 stdin
的工具事件 JSON。落地 constraints.md #2"查数据形状先用 query_metadata.py"的机制下限。

判定：
- 02 metadata/ 下的表格文件 → 显式放行（无需弹窗）
- 01 rawdata/ 下的表格文件 → 硬拒绝（禁止直接读取，引导使用 query_metadata.py）
- Bash 命令中出现 raw 读取特征 → 硬拒绝（排除 04 scripts/ 脚本、query_metadata.py，
  以及命令内每个读取调用都带 nrows≤2 的兜底读取——见 constraints #2）
"""

import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}

# Bash 命令中"读 raw 原始数据"的特征。
# 不含裸 "openpyxl"：纯 import / pip 安装不视为读数据；实际读表走 load_workbook。
_RAW_READ_RE = re.compile(r"read_excel|load_workbook|ExcelFile|raw_path")
_RAW_PATH_RE = re.compile(r"""(?:raw[/\\]|rawdata[/\\]|01\s+rawdata[/\\])[^"'\s]*\.(?:xlsx|xls|csv)""", re.IGNORECASE)
_RUN_SCRIPT_RE = re.compile(r"""python[\w.]*\s+["']?(?:04\s+)?scripts[/\\]""")
# constraints #2 兜底：带行数上限（nrows≤2，含表头≤3 行）的受控读取属例外，放行
_BOUNDED_NROWS_RE = re.compile(r"nrows\s*=\s*[012]\b")
# 读取调用计数（用于判定"命令中每个读取都带 nrows 上限"，防止混入无界读绕过）
_READ_CALL_RE = re.compile(r"read_excel|load_workbook|ExcelFile")

_DENY_RAW_REASON = (
    "严禁直接读取 raw 原始数据。按项目约定（constraints.md #2）应先用 "
    "query_metadata.py 无接触查询字段名/编码表/列名结构（用法见 write-script skill "
    "Step 2），查不到再考虑其他方式。"
)


def _decide(decision, reason=None):
    """输出 hook 决策 JSON，exit 0 表示 hook 本身执行成功。"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(output, ensure_ascii=False))
    return 0


def _is_table_file(path_str):
    if not path_str:
        return False
    return Path(path_str).suffix.lower() in _DATA_SUFFIXES


def _under_dir(path_str, dir_name):
    """检查路径是否在项目根下指定目录内。"""
    if not path_str:
        return False
    p = Path(path_str)
    try:
        rel = p.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == dir_name


def _all_reads_bounded(cmd: str) -> bool:
    """命令中每个读取调用都必须配有 nrows≤2；缺一则不放行。"""
    n_reads = len(_READ_CALL_RE.findall(cmd))
    if n_reads == 0:
        return False
    n_bounded = len(_BOUNDED_NROWS_RE.findall(cmd))
    return n_bounded >= n_reads


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}

    if tool_name == "Read":
        file_path = tool_input.get("file_path") or ""
        if not _is_table_file(file_path):
            return 0  # 非表格文件，不干预

        if _under_dir(file_path, "02 metadata"):
            return _decide("allow")  # metadata → 显式放行
        if _under_dir(file_path, "01 rawdata"):
            return _decide("deny", _DENY_RAW_REASON)  # raw → 硬拒绝

        return 0

    if tool_name == "Bash" or tool_name == "PowerShell":
        cmd = tool_input.get("command") or ""
        if "query_metadata.py" in cmd or _RUN_SCRIPT_RE.search(cmd):
            return 0  # 元数据工具 / scripts 下真实脚本，放行
        if _all_reads_bounded(cmd):
            return 0  # 兜底：每个读取都带 nrows≤2 上限（constraints #2），放行
        if _RAW_READ_RE.search(cmd) or _RAW_PATH_RE.search(cmd):
            return _decide("deny", _DENY_RAW_REASON)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
