#!/usr/bin/env python
"""PreToolUse 钩子：拦截直接读取 raw 原始数据；允许读取 metadata。**全局安全**。

由 hooks/hooks.json 声明，随 ClinSkills plugin 加载（matcher: Bash|Read|PowerShell|Grep），
读 stdin 的工具事件 JSON。落地「查数据形状先用 query_metadata.py」的机制下限。

**全局安全**：可随 plugin 跨项目生效而不误伤非临床项目——只针对**确切指向 raw 原始数据**
的操作判定，绝不因命令里出现裸 `read_excel(` / openpyxl 就拦。

判定：
- Read 工具：`02 metadata/` 下表格文件 → 放行；`01 rawdata/` 下 → 硬拒绝。
  项目根优先取 `CLAUDE_PROJECT_DIR`。
- Grep 工具：`path` 落在 `01 rawdata/` 下 → 硬拒绝（CSV 等纯文本可被 Grep 直接吐出，
  此前仅拦 Read/Bash 时存在旁路）。
- Bash / PowerShell：按 `&&` / `||` / `;` / `|` / 换行 **分段逐条判定**，任一段命中 deny
  即拒绝整条（消解「query_metadata.py / 04 scripts/ 子串短路整条命令」的绕过）。段内：
  (0) 每个读调用都带 `nrows≤2` 的兜底读取（先剥 # 注释再计数，防 `# nrows=2` 伪造）→ 放行；
  (a) 出现字面 `01 rawdata` 目录引用（裸目录或任意后缀，含 cat/head/rglob/find/cd）→ 硬拒绝；
  (b) 引号内路径 resolve 后落在 `01 rawdata/`（符号链接回指 raw）→ 硬拒绝；
  (c)【仅临床项目】有实际读调用且用了 `raw_path` 配置变量 → 硬拒绝；
  否则该段若是 `query_metadata.py` / `04 scripts/` 脚本运行 → 放行。
  裸 read_excel(（无 raw 指向）一律不拦。

**不保护 `03 output/`**：脚本产出需由 agent 回读核对结果是否正确，故本 hook 与
settings deny 均不拦截 output 目录。

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

# 项目根：优先 Claude Code 注入的 CLAUDE_PROJECT_DIR（plugin 安装后仍能定位「当前打开的项目」）；
# 未设置时回退本文件向上一级——本仓库布局为 repo/scripts/raw_read_guard.py，parents[1] = repo root。
# （勿用 parents[2]：那会指到 repo 的父目录，导致 _under_dir / 临床项目探测全部失效。）
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])
try:
    # resolve 一次，消除符号链接与相对段，后续 relative_to 比较更稳。
    PROJECT_ROOT = PROJECT_ROOT.resolve()
except OSError:
    pass

# 是否为临床数据项目（存在 01 rawdata/）。
# 仅用此门控「读调用 + raw_path 变量」启发式，避免 plugin 全局生效后误伤普通项目里
# 恰好也叫 raw_path 的变量；字面 01 rawdata 引用则任何项目都拦（路径足够特异）。
_CLINICAL_PROJECT = (PROJECT_ROOT / "01 rawdata").is_dir()

_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}

# 实际读调用：紧跟左括号，只匹配「调用」而非 import / 标识符。
# 含 read_csv：CSV 与 Excel 对称地享受 nrows≤2 兜底；否则 CSV 只能走字面路径 deny。
_READ_CALL_RE = re.compile(r"(?:read_excel|read_csv|load_workbook|ExcelFile)\s*\(")

# 字面 raw 目录引用：匹配裸目录 `01 rawdata` 或 `01 rawdata/...`（任意后缀）。
# 比旧版「仅 .xlsx|.xls|.csv」更严——挡住 cat/head/find/cd 以及 .sas7bdat 等非表格后缀。
_RAW_DIR_REF_RE = re.compile(r"""01\s+rawdata(?:[/\\]|['"\s]|$)""", re.IGNORECASE)

# raw_path 配置变量：仅当与实际读调用同现、且在临床项目中时，才视为「读 raw」。
_RAW_PATH_VAR_RE = re.compile(r"\braw_path\b")

# 运行 04 scripts/ 下真实脚本（或历史路径 scripts/）→ 白名单放行（脚本内部由 loaders 合规读）。
_RUN_SCRIPT_RE = re.compile(r"""python[\w.]*\s+["']?(?:04\s+)?scripts[/\\]""")

# constraints #2 兜底：nrows=0/1/2 视为「只探字段/取样」的受控读。
_BOUNDED_NROWS_RE = re.compile(r"nrows\s*=\s*[012]\b")

# 把复合 shell 命令拆成独立段，避免「前半段白名单 + 后半段偷读 raw」整条被短路放行。
# 例：`python query_metadata.py search x && cat '01 rawdata/a.csv'` 必须 deny。
_CMD_SPLIT_RE = re.compile(r"(?:&&|\|\||[;|\n])")

# 提取引号内路径 token，供 resolve 后判断是否落入 01 rawdata/（含符号链接回指）。
_PATH_TOKEN_RE = re.compile(r"""['"]([^'"]+)['"]""")

_DENY_RAW_REASON = (
    "严禁直接读取 raw 原始数据。按项目约定应先用 "
    "query_metadata.py 无接触查询字段名/编码表/列名结构（用法见 write-script skill "
    "Step 2），查不到再考虑其他方式。"
)


def _decide(decision, reason=None):
    """输出 PreToolUse hook 决策 JSON；exit 0 表示 hook 自身执行成功（非业务放行）。"""
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
    """是否为 hook 关心的表格后缀（xlsx/xls/csv）；其它后缀交给 settings deny 等层处理。"""
    if not path_str:
        return False
    return Path(path_str).suffix.lower() in _DATA_SUFFIXES


def _under_dir(path_str, dir_name):
    """路径是否落在项目根下指定一级目录内（resolve 后比较）。

    相对路径先拼到 PROJECT_ROOT 再 resolve，避免 cwd 与项目根不一致时误判。
    """
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
    """path 是否指向 01 rawdata/（resolve 归属，或字面相对路径前缀）。

    供 Grep 使用：Grep 的 path 可能是未 resolve 的相对串，两路都查可避免漏拦。
    """
    if not path_str:
        return False
    if _under_dir(path_str, "01 rawdata"):
        return True
    normalized = path_str.replace("\\", "/").lstrip("./")
    return bool(re.match(r"01\s+rawdata(/|$)", normalized, re.IGNORECASE))


def _strip_hash_comments(cmd: str) -> str:
    """剥离 shell 风格 # 注释，但尊重引号内的 #。

    用途：防 `# nrows=2` 伪造成「有界读」而洗白真实全量 read_excel。
    不处理行续接 / 复杂 quoting 嵌套——偏保守即可。
    """
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
    """命令中每个读取调用都必须配有 nrows≤2；先剥注释再计数。

    返回 True 表示「整段都是受控取样读」→ 上层应放行。
    无读调用时返回 False（不能凭空当作有界读）。
    """
    cleaned = _strip_hash_comments(cmd)
    n_reads = len(_READ_CALL_RE.findall(cleaned))
    if n_reads == 0:
        return False
    n_bounded = len(_BOUNDED_NROWS_RE.findall(cleaned))
    return n_bounded >= n_reads


def _any_token_resolves_to_raw(cmd: str) -> bool:
    """引号内路径 token resolve 后是否落在 01 rawdata/。

    捕获「字面路径不写 01 rawdata，但符号链接 / 绝对路径实际指向 raw」的情况。
    """
    for m in _PATH_TOKEN_RE.finditer(cmd):
        token = m.group(1)
        if _under_dir(token, "01 rawdata"):
            return True
    return False


def _segment_denies(seg: str) -> bool:
    """单段命令是否应被拒绝。

    判定顺序（顺序敏感）：
    1) 真 nrows≤2 兜底（剥注释后）→ 放行
    2) 字面 01 rawdata 引用 / resolve 到 raw → deny
       （必须在 query_metadata / 04 scripts 白名单之前，避免子串洗白）
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
    """整条命令是否应被拒绝：分段后任一段 deny 即拒绝整条。

    拆段是为消解「白名单命令 && 偷读 raw」一类短路绕过；空命令不拦。
    """
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
        # 非表格后缀不在本 hook 职责内；全后缀硬拦依赖 settings.permissions.deny。
        if not _is_table_file(file_path):
            return 0

        if _under_dir(file_path, "02 metadata"):
            return _decide("allow")  # metadata → 显式放行
        if _under_dir(file_path, "01 rawdata"):
            return _decide("deny", _DENY_RAW_REASON)  # raw → 硬拒绝

        return 0

    # Grep 可对 CSV 等纯文本直接吐出内容，需与 Read 同级拦截。
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
