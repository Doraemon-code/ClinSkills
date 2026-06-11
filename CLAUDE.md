# Project: 脊痛宁数据审核报告

## Overview
临床试验数据审核报告项目。通过 Python + pandas 处理 EDC 导出的 Excel 数据，生成 .docx/.xlsx 报表。

## Architecture
- **Notebooks** (`a~j.*.py`): 各章节分析代码，用 jupytext `percent` 格式存储（`# %%` 分 cell）
- **env.py**: 项目环境入口，加载依赖和 config.yaml 路径配置
- **config.yaml**: 数据路径配置（raw data、output 路径）
- **utils/**: 公共工具函数（output_format、add_sheet_index 等）
- **raw/**: 原始数据（不入 Git）
- **output/**: 生成的报表（不入 Git）

## Jupytext Workflow
`.py` 文件是 Git 源文件，`.ipynb` 是运行时文件（不入 Git）。

- **编辑**: 在 Claude Code 中直接编辑 `.py` 文件（纯代码，无输出污染）
- **运行**: 在 JupyterHub 中打开 `.ipynb`（jupytext 自动同步 `.py` 变更）
- **同步**: 修改 `.py` 后打开 `.ipynb` 会自动更新；反之亦然
- **从 .py 重建 .ipynb**: `jupytext --sync *.py`

## Conventions
- Notebook 文件名格式: `[字母].中文名.py`
- 所有 notebook 通过 `%run env.py` 加载环境
- 报表函数来自 `utils/output_format.py`
- 生成文件路径由 `config.yaml` 的 `output_path` 控制
