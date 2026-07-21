#!/usr/bin/env python
"""幂等地把全局 harness 配置合并进用户级 settings.json。

由 install.ps1 / install.sh 调用：`python merge_hook.py <claude_dir>`。
注册两个 hook（syntax_check / raw_read_guard）+ raw 数据 deny 权限；已存在则跳过。
三者均全局安全（raw_read_guard 只在命令确切指向 raw 时才拦），故可放入用户级、跨项目生效——
项目无需自带 `.claude/`。只增不删，保留其它已有配置。
"""
import json
import sys
from pathlib import Path


def _has_hook(entries, needle):
    for m in entries:
        for h in m.get("hooks", []):
            if needle in (h.get("command") or ""):
                return True
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python merge_hook.py <claude_dir>", file=sys.stderr)
        return 1
    claude_dir = Path(sys.argv[1])
    settings_path = claude_dir / "settings.json"
    hooks_dir = claude_dir / "hooks"

    settings = {}
    if settings_path.exists():
        text = settings_path.read_text(encoding="utf-8")
        if text.strip():
            try:
                settings = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                print("  ! 现有 settings.json 无法解析，跳过——请手动配置。", file=sys.stderr)
                return 0
            if not isinstance(settings, dict):
                print("  ! 现有 settings.json 顶层非对象，跳过——请手动配置。", file=sys.stderr)
                return 0

    changed = False
    hooks = settings.setdefault("hooks", {})

    # 1) PostToolUse: syntax_check（改脚本后语法地板）
    post = hooks.setdefault("PostToolUse", [])
    if not _has_hook(post, "syntax_check.py"):
        post.append({
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [{"type": "command",
                       "command": f'"{sys.executable}" "{hooks_dir / "syntax_check.py"}"'}],
        })
        changed = True
        print("  ✓ 注册 syntax_check (PostToolUse)")

    # 2) PreToolUse: raw_read_guard（全局安全，仅拦确切读 raw 的操作）
    pre = hooks.setdefault("PreToolUse", [])
    if not _has_hook(pre, "raw_read_guard.py"):
        pre.append({
            "matcher": "Bash|Read|PowerShell",
            "hooks": [{"type": "command",
                       "command": f'"{sys.executable}" "{hooks_dir / "raw_read_guard.py"}"'}],
        })
        changed = True
        print("  ✓ 注册 raw_read_guard (PreToolUse)")

    # 3) permissions.deny: 硬拦 Read 工具直读 rawdata（非临床项目无此目录、无副作用）
    perms = settings.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    rule = "Read(01 rawdata/**)"
    if rule not in deny:
        deny.append(rule)
        changed = True
        print("  ✓ 添加 deny Read(01 rawdata/**)")

    if changed:
        settings_path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        print("  · 全局配置已就绪，跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
