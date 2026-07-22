#!/usr/bin/env python
"""PreToolUse 钩子：拦截直接读取 raw 原始数据；允许读取 metadata。**全局安全**。

由 hooks/hooks.json 声明，随 ClinSkills plugin 加载（matcher: Bash|Read|PowerShell），读 stdin 的工具事件
JSON。落地 constraints.md #2「查数据形状先用 query_metadata.py」的机制下限。

**全局安全**：本 hook 设计为可注册进用户级 `~/.claude/settings.json`（跨项目生效）而不误伤非临床
项目——只针对**确切指向 raw 原始数据**的操作判定，绝不因命令里出现裸 `read_excel(` / openpyxl 就拦。

判定：
- Read 工具：`02 metadata/` 下表格文件 → 放行；`01 rawdata/` 下 → 硬拒绝。
  项目根优先取 `CLAUDE_PROJECT_DIR`（随 ClinSkills plugin 安装仍能定位当前项目）。
- Bash / PowerShell：仅当命令 (a) 出现字面 `01 rawdata/…xlsx|xls|csv` 路径，或 (b)【仅临床项目】有
  实际读调用（`read_excel(` / `load_workbook(` / `ExcelFile(`）且用了 `raw_path` 配置变量 → 硬拒绝。
  排除：`query_metadata.py`、`04 scripts/` 脚本、每个读取都带 `nrows≤2` 的兜底读取（constraints #2）。
"""

import json
import os
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# 项目根：优先 Claude Code 注入的 CLAUDE_PROJECT_DIR（本 hook 随 ClinSkills plugin 安装，
# 通过 $PLUGIN_ROOT 定位）；未设置则回退本文件向上三级（本仓库自身作项目时成立）。
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
# 本项目是否为临床数据项目（存在 01 rawdata/）——用于门控只在临床项目才成立的启发式，
# 使本 hook 全局注册后不误伤普通数据项目（如其中恰有名为 raw_path 的变量）。
_CLINICAL_PROJECT = (PROJECT_ROOT / "01 rawdata").is_dir()

_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}

# 实际读调用：紧跟左括号，只匹配"调用"而非 import / grep / 源码里的裸标识符。
_READ_CALL_RE = re.compile(r"(?:read_excel|load_workbook|ExcelFile)\s*\(")
# 字面 raw 原始数据路径：限项目约定的 "01 rawdata/"（带序号+空格，足够特异），
# 全局注册也不会误伤别的项目里普通的 raw/ 或 rawdata/ 目录。
_RAW_PATH_RE = re.compile(r"""01\s+rawdata[/\\][^"'\s]*\.(?:xlsx|xls|csv)""", re.IGNORECASE)
# raw_path 配置变量：仅当与实际读调用同现时才视为"读 raw"。
_RAW_PATH_VAR_RE = re.compile(r"\braw_path\b")
_RUN_SCRIPT_RE = re.compile(r"""python[\w.]*\s+["']?(?:04\s+)?scripts[/\\]""")
# constraints #2 兜底：每个读取都带 nrows≤2（含表头≤3 行）的受控读取放行。
_BOUNDED_NROWS_RE = re.compile(r"nrows\s*=\s*[012]\b")

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
        # 全局安全：仅当命令确切指向 raw 原始数据才拦——
        #  (a) 出现字面 "01 rawdata/…xlsx" 路径（自证特异，任何项目都拦）；或
        #  (b) 有实际读调用且用了 raw_path 配置变量——此启发式**仅在临床项目**（存在 01 rawdata/）
        #      才生效，避免全局注册后误伤普通数据项目里恰好也叫 raw_path 的变量。
        #  裸 read_excel(（无 raw 指向）一律不拦。
        if _RAW_PATH_RE.search(cmd) or (
            _CLINICAL_PROJECT and _READ_CALL_RE.search(cmd) and _RAW_PATH_VAR_RE.search(cmd)
        ):
            return _decide("deny", _DENY_RAW_REASON)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
