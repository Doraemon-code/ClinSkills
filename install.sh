#!/usr/bin/env bash
# ClinSkills utils 工具层部署（legacy）
#   推荐使用 Plugin Marketplace 安装：claude plugin install clin-skills
#   本脚本仅部署 utils/ 到全局 ~/.claude/skills/build-metadata/reference/skeleton/utils/
#   供 build-metadata skill 脚手架进临床项目。插件本身通过 marketplace 或 --plugin-dir 加载。
# 依赖：git、python3。
#   curl -fsSL https://raw.githubusercontent.com/Doraemon-code/ClinSkills/master/install.sh | bash

set -euo pipefail
repo="https://github.com/Doraemon-code/ClinSkills.git"
branch="master"
claude_dir="$HOME/.claude"

echo ""
echo "ClinSkills utils 部署 → $claude_dir"

for tool in git python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "缺少依赖：$tool，请先安装。" >&2; exit 1; }
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 --branch "$branch" "$repo" "$tmp" >/dev/null 2>&1

# 部署 utils/ 到 build-metadata skeleton，供脚手架进各临床项目
skel_utils="$claude_dir/skills/build-metadata/reference/skeleton/utils"
if [ -d "$tmp/utils" ]; then
  if [ -d "$claude_dir/skills/build-metadata" ]; then
    rm -rf "$skel_utils"; mkdir -p "$(dirname "$skel_utils")"
    cp -R "$tmp/utils" "$skel_utils"
    echo "  + build-metadata/reference/skeleton/utils （供项目脚手架）"
  fi
fi

echo ""
echo "完成。utils 已部署到 $skel_utils"
echo ""
echo "如需完整 Plugin（skills / agents / hooks / utils）："
echo "  claude plugin install ./ClinSkills"
echo "或开发模式："
echo "  claude --plugin-dir ./ClinSkills"
