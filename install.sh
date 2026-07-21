#!/usr/bin/env bash
# ClinSkills 一键安装 —— 把 skills / agents / hooks 装到 ~/.claude（全局可用）
#   curl -fsSL https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.sh | bash
# 依赖：git、python3。同名 skill 会被覆盖更新；重跑即更新。

set -euo pipefail
repo="https://github.com/Doraemon-code/ClinSkills.git"
branch="master"
claude_dir="$HOME/.claude"

echo ""
echo "ClinSkills → $claude_dir"

for tool in git python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "缺少依赖：$tool，请先安装。" >&2; exit 1; }
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 --branch "$branch" "$repo" "$tmp" >/dev/null 2>&1

mkdir -p "$claude_dir"
for sub in skills agents hooks; do
  src="$tmp/.claude/$sub"
  [ -d "$src" ] || continue
  mkdir -p "$claude_dir/$sub"
  for item in "$src"/*; do
    name="$(basename "$item")"
    rm -rf "$claude_dir/$sub/$name"
    cp -R "$item" "$claude_dir/$sub/$name"
    echo "  + $sub/$name"
  done
done

python3 "$tmp/install/merge_hook.py" "$claude_dir"
echo ""
echo "完成。skills / agents / hooks 已装到 $claude_dir（全局可用）。"
echo "新临床项目：进入项目目录后触发 build-metadata 脚手架结构并解析元数据。"
