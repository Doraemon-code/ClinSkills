"""make_template.py — 从本项目抽取通用骨架，生成可作为 GitHub 模板仓库的干净目录树。

用法:
    python make_template.py [输出目录]      # 默认 ../DMR-template

只拷贝跨项目通用的部分（.claude 全套技能/规则/钩子/权限、utils、config.py、
依赖与 git 配置），生成骨架 config.yaml / CLAUDE.md，并为数据目录留 .gitkeep 占位。
绝不拷贝任何具体项目的脚本、笔记本、元数据或原始/产出数据。

"纯拷贝"约定：模板是技能的权威副本。改进了某项目里的技能后，若要让新项目受益，
重新运行本脚本刷新模板（或把改动手动回灌模板仓库），再 push。

抽取后：cd 进输出目录 → git init/add/commit → push 到 GitHub →
仓库 Settings 勾选 "Template repository"，即可 "Use this template" 开新试验。
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 通用部分，整目录/整文件拷贝（跨项目不变）
COPY_PATHS = [
    ".claude/skills",
    ".claude/rules",
    ".claude/hooks",
    ".claude/settings.json",   # 不含 settings.local.json（个人/历史残留）
    "utils",
    "config.py",
    "requirements.txt",
    ".gitignore",
    ".gitattributes",
]

# 留 .gitkeep 占位的空目录（项目数据，不拷内容）
EMPTY_DIRS = ["scripts", "metadata", "raw", "output"]

SKELETON_CONFIG_YAML = """\
path:
  # 各原始数据 Excel 路径（相对项目根），按新项目实际填写
  raw_path: "raw/<日期>/<受试者数据导出>.xlsx"
  pd_path: "raw/<日期>/<方案偏离>.xlsx"
  code_path: "raw/<日期>/<医学编码报告>.xlsx"
  remark_path: "raw/<日期>/<备注明细>.xlsx"
  timewin_path: "raw/time window.xlsx"
  output_path: "output/<日期>"
"""

SKELETON_CLAUDE_MD = """\
# Project: <项目名>数据审核报告

## Overview
临床试验数据审核报告项目。通过 Python + pandas 处理 EDC 导出的 Excel 数据，生成 .docx/.xlsx 报表。

## Directory Structure
```
├── config.py / config.yaml   # 路径配置
├── scripts/                   # 分析代码（按章节拆分）
├── utils/                     # 公共工具（loaders / output_format 等）
├── metadata/                  # EDC 元数据 Excel + build-metadata 生成的 JSON
├── raw/                       # 原始数据（不入 Git）
└── output/                    # 生成的报表（不入 Git）
```

## Permissions
- `scripts/`、`utils/`、`config.py`、`config.yaml`：Claude Code 可编辑
- `raw/`、`output/`：不在 Git 中

## Conventions

编码规范详见 `/write-script` skill 的 `SKILL.md`。跨 skill 的通用约定：

- 表头结构：首次写脚本时由 write-script Step 0 询问并写回本节
- 报表函数来自 `utils/output_format.py`
- 数据读取函数来自 `utils/loaders.py`（`load_sheet` / `load_rand` 等）
- 生成文件路径由 `config.yaml` 的 `output_path` 控制（`config.py` 自动解析为绝对路径）
- 虚拟环境位于 `.venv/`，安装依赖：`pip install -r requirements.txt`

## 新项目初始化
1. `pip install -r requirements.txt`
2. 元数据 Excel 放进 `metadata/`，运行 `/build-metadata` 解析为 JSON
3. 填写 `config.yaml` 的数据路径
4. 用 `/write-script` 写第一个核查脚本（Step 0 会问表头结构并写回本文件）
"""


def _ignore(directory, names):
    """copytree 过滤：丢弃 Python 缓存。"""
    return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]


def main():
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT.parent / "DMR-template")
    if out.exists():
        print(f"错误: 输出目录已存在: {out}（请删除或指定其他路径）", file=sys.stderr)
        sys.exit(1)
    out.mkdir(parents=True)

    for rel in COPY_PATHS:
        src = ROOT / rel
        if not src.exists():
            print(f"  跳过（不存在）: {rel}")
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=_ignore)
        else:
            shutil.copy2(src, dst)
        print(f"  拷贝: {rel}")

    for d in EMPTY_DIRS:
        keep = out / d / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("", encoding="utf-8")
        print(f"  留空: {d}/.gitkeep")

    (out / "config.yaml").write_text(SKELETON_CONFIG_YAML, encoding="utf-8")
    (out / "CLAUDE.md").write_text(SKELETON_CLAUDE_MD, encoding="utf-8")
    print("  骨架: config.yaml, CLAUDE.md")

    print(f"\n模板已生成: {out}")
    print("下一步: cd 进去 → git init && git add -A && git commit -m 'init template'")
    print("        → push 到 GitHub → 仓库 Settings 勾选 'Template repository'")


if __name__ == "__main__":
    main()
