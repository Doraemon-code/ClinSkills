#!/usr/bin/env python
"""幂等地把通用 syntax_check hook 注册进用户级 settings.json。

由 install.ps1 / install.sh 调用：`python merge_hook.py <claude_dir>`。
只动 hooks.PostToolUse，其它配置原样保留；已注册则跳过。
raw_read_guard 等项目级护栏不在此注册（由 build-metadata 写进各项目）。
"""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python merge_hook.py <claude_dir>", file=sys.stderr)
        return 1
    claude_dir = Path(sys.argv[1])
    settings_path = claude_dir / "settings.json"
    hook_cmd = f'python "{claude_dir / "hooks" / "syntax_check.py"}"'

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            print("  ! 现有 settings.json 无法解析，跳过 hook 注册——请手动添加。",
                  file=sys.stderr)
            return 0

    hooks = settings.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])

    for matcher in post:
        for h in matcher.get("hooks", []):
            if "syntax_check.py" in (h.get("command") or ""):
                print("  · syntax_check hook 已注册，跳过")
                return 0

    post.append({
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [{"type": "command", "command": hook_cmd}],
    })
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  ✓ 已注册 syntax_check hook 到全局 settings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
