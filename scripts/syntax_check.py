#!/usr/bin/env python3
"""PostToolUse 钩子：项目 04 scripts/ 与 utils/ 下的 .py 被 Edit/Write/MultiEdit 后自动做语法检查。

由 hooks/hooks.json 声明，随 ClinSkills plugin 加载；读取 stdin 的工具事件 JSON。
- 仅对项目根 04 scripts/ 与 utils/ 目录下的 .py 生效（排除 skills/**/scripts/ 等同名目录）。
- 语法错误 → 退出码 2：stderr 回灌给模型，要求修复（rule #3 的"语法地板"）。
- 其余情况一律放行（退出码 0），不打扰。

这是 rule #3"改脚本后必须验证"的机制化下限：实跑 + 看输出文件仍由 write-script
skill Step 5 负责，本钩子只保证"至少语法可解析"这条底线总会被检查。
"""
import ast
import json
import os
import sys
from pathlib import Path

# 输出统一 UTF-8，避免 Windows 默认 cp936 与上游 UTF-8 解码不一致导致中文乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# 项目根：优先 Claude Code 注入的 CLAUDE_PROJECT_DIR（本 hook 随 ClinSkills plugin 安装，
# 通过 $CLAUDE_PLUGIN_ROOT 定位）；未设置则回退本文件向上三级（本仓库自身作项目时成立）。
PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # 非预期输入，放行

    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    raw_path = tool_input.get("file_path") or tool_response.get("filePath")
    if not raw_path:
        return 0

    p = Path(raw_path)
    if p.suffix != ".py":
        return 0

    # 仅限项目根 04 scripts/ 或 utils/ 下
    try:
        rel = p.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return 0  # 项目外，放行
    if not rel.parts or rel.parts[0] not in ("04 scripts", "utils"):
        return 0

    try:
        source = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0  # 文件读不到或编码不兼容，放行

    try:
        ast.parse(source, filename=str(p))
    except SyntaxError as e:
        print(f"语法检查未通过 [{rel}] 第 {e.lineno} 行: {e.msg}", file=sys.stderr)
        return 2  # 退出码 2：阻塞性反馈，stderr 回灌给模型

    return 0  # 语法通过，静默放行


if __name__ == "__main__":
    sys.exit(main())
