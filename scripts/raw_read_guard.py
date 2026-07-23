#!/usr/bin/env python3
"""PreToolUse 钩子：拦截直接读取 raw 原始数据；允许读取 metadata。**全局安全**。

由 hooks/hooks.json 声明，随 ClinSkills plugin 加载（matcher: Bash|Read|PowerShell|Grep），读 stdin 的
工具事件 JSON。落地「查数据形状先用 query_metadata.py」的机制下限。

**全局安全**：可随 plugin 跨项目生效而不误伤非临床项目——只针对**确切指向 raw 原始数据**
的操作判定，绝不因命令里出现裸 `read_excel(` / openpyxl 就拦。

判定：
- Read 工具：`02 metadata/` 下表格文件 → 放行；`01 rawdata/` 下 → 硬拒绝。
  项目根优先取 `CLAUDE_PROJECT_DIR`。
- Grep 工具：`path` 落在 `01 rawdata/` 下 → 硬拒绝（CSV 等纯文本可被 Grep 直接吐出）。
- Bash / PowerShell：按 `&&` / `||` / `;` / `|` / 换行 **分段逐条判定**，任一段命中 deny 即拒绝整条
  （消解「query_metadata.py / 04 scripts/ 子串短路整条命令」的绕过）。段内：
  (0) 每个读调用都带 `nrows≤2` 的兜底读取（先剥 # 注释再计数）→ 放行；
  (a) 出现字面 `01 rawdata` 目录引用（裸目录或任意后缀，含 cat/head/rglob/find/cd）→ 硬拒绝；
  (b) 引号内路径 resolve 后落在 `01 rawdata/`（符号链接回指 raw）→ 硬拒绝；
  (c)【仅临床项目】有实际读调用且用了 `raw_path` 配置变量 → 硬拒绝；
  否则该段若是 `query_metadata.py` / `04 scripts/` 脚本运行 → 放行。
  裸 read_excel(（无 raw 指向）一律不拦。

**已接受残留风险**（不做脆弱的脚本内容扫描）：
- `python /tmp/x.py` 内部 `read_excel('01 rawdata/...')`——命令串无字面 raw 路径时本 hook 不拦，
  依赖 Bash 未进 allow 白名单 → 提示用户兜底。
- 字符串拼接（`'01 '+'rawdata'`）规避字面路径正则——需刻意构造。
- 朴素分段不解析引号：`echo "a; 01 rawdata/x"` 会被误分段并偏保守 deny（对 guard 可接受）。
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

# 项目根：优先 CLAUDE_PROJECT_DIR；未设置则回退本文件向上一级（scripts/ → repo root）。
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])
try:
    PROJECT_ROOT = PROJECT_ROOT.resolve()
except OSError:
    pass
# 本项目是否为临床数据项目（存在 01 rawdata/）——门控只在临床项目才成立的启发式。
_CLINICAL_PROJECT = (PROJECT_ROOT / "01 rawdata").is_dir()

_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}

# 实际读调用：紧跟左括号；含 read_csv 使 CSV 的 nrows≤2 兜底与 Excel 对称。
_READ_CALL_RE = re.compile(r"(?:read_excel|read_csv|load_workbook|ExcelFile)\s*\(")
# 字面 raw 目录引用：裸目录 `01 rawdata` 或 `01 rawdata/...`（任意后缀）。
_RAW_DIR_REF_RE = re.compile(r"""01\s+rawdata(?:[/\\]|['"\s]|$)""", re.IGNORECASE)
_RAW_PATH_VAR_RE = re.compile(r"\braw_path\b")
_RUN_SCRIPT_RE = re.compile(r"""python[\w.]*\s+["']?(?:04\s+)?scripts[/\\]""")
_BOUNDED_NROWS_RE = re.compile(r"nrows\s*=\s*[012]\b")
_CMD_SPLIT_RE = re.compile(r"(?:&&|\|\||[;|\n])")
_PATH_TOKEN_RE = re.compile(r"""['"]([^'"]+)['"]""")

_DENY_RAW_REASON = (
    "严禁直接读取 raw 原始数据。按项目约定应先用 "
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
    """检查路径是否在项目根下指定目录内（resolve 后比较）。"""
    if not path_str:
        return False
    p = Path(path_str)
    try:
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        rel = p.resolve().relative_to(PROJECT_ROOT)
    except (ValueError, OSError):
        return False
    return bool(rel.parts) and rel.parts[0] == dir_name


def _looks_like_raw_path(path_str):
    """path 是否指向 01 rawdata/（resolve 归属或字面相对路径）。"""
    if not path_str:
        return False
    if _under_dir(path_str, "01 rawdata"):
        return True
    normalized = path_str.replace("\\", "/").lstrip("./")
    return bool(re.match(r"01\s+rawdata(/|$)", normalized, re.IGNORECASE))


def _strip_hash_comments(cmd: str) -> str:
    """剥离 # 注释（尊重引号内的 #），避免 `# nrows=2` 伪造兜底放行。"""
    out_lines = []
    for line in cmd.splitlines():
        result = []
        in_single = in_double = False
        for c in line:
            if c == "'" and not in_double:
                in_single = not in_single
                result.append(c)
            elif c == '"' and not in_single:
                in_double = not in_double
                result.append(c)
            elif c == "#" and not in_single and not in_double:
                break
            else:
                result.append(c)
        out_lines.append("".join(result))
    return "\n".join(out_lines)


def _all_reads_bounded(cmd: str) -> bool:
    """命令中每个读取调用都必须配有 nrows≤2；先剥注释再计数。"""
    cleaned = _strip_hash_comments(cmd)
    n_reads = len(_READ_CALL_RE.findall(cleaned))
    if n_reads == 0:
        return False
    n_bounded = len(_BOUNDED_NROWS_RE.findall(cleaned))
    return n_bounded >= n_reads


def _any_token_resolves_to_raw(cmd: str) -> bool:
    """引号内路径 token resolve 后是否落在 01 rawdata/（捕获符号链接）。"""
    for m in _PATH_TOKEN_RE.finditer(cmd):
        token = m.group(1)
        if _under_dir(token, "01 rawdata"):
            return True
    return False


def _segment_denies(seg: str) -> bool:
    """单段命令是否应被拒绝。

    判定顺序：
    1) 真 nrows≤2 兜底（剥注释后）→ 放行
    2) 字面 01 rawdata 引用 / resolve 到 raw → deny（在脚本白名单之前，避免子串洗白）
    3) query_metadata / 04 scripts → 放行
    4) 临床项目：读调用 + raw_path 变量 → deny
    """
    if _all_reads_bounded(seg):
        return False
    if _RAW_DIR_REF_RE.search(seg) or _any_token_resolves_to_raw(seg):
        return True
    if "query_metadata.py" in seg or _RUN_SCRIPT_RE.search(seg):
        return False
    if _CLINICAL_PROJECT and _READ_CALL_RE.search(seg) and _RAW_PATH_VAR_RE.search(seg):
        return True
    return False


def _command_denies(cmd: str) -> bool:
    """整条命令是否应被拒绝：分段后任一段 deny 即拒绝。"""
    segments = [s.strip() for s in _CMD_SPLIT_RE.split(cmd) if s.strip()]
    if not segments:
        return False
    return any(_segment_denies(seg) for seg in segments)


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
            return 0  # 非表格文件，不干预（全后缀靠 settings deny 兜底）

        if _under_dir(file_path, "02 metadata"):
            return _decide("allow")
        if _under_dir(file_path, "01 rawdata"):
            return _decide("deny", _DENY_RAW_REASON)

        return 0

    if tool_name == "Grep":
        path = tool_input.get("path") or ""
        if _looks_like_raw_path(path):
            return _decide("deny", _DENY_RAW_REASON)
        return 0

    if tool_name == "Bash" or tool_name == "PowerShell":
        cmd = tool_input.get("command") or ""
        if _command_denies(cmd):
            return _decide("deny", _DENY_RAW_REASON)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
