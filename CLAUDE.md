# Project: 脊痛宁数据审核报告

## Overview
临床试验数据审核报告项目。通过 Python + pandas 处理 EDC 导出的 Excel 数据，生成 .docx/.xlsx 报表。

## Directory Structure
```
├── env.py              # 项目环境入口（加载依赖和 config.yaml）
├── config.yaml         # 数据路径配置
├── requirements.txt    # Python 依赖
├── 注意事项.md          # 业务规则说明
├── scripts/            # 分析代码（按章节拆分，与 notebooks/ 一一对应）
│   ├── a.试验整体情况小结/
│   ├── b.入排标准/
│   ├── c.方案偏离/
│   ├── d.超窗/
│   ├── e.缺失/
│   ├── f.用药后异常有临床意义/
│   ├── g.不良事件相关汇总/
│   ├── h.常规附件清单/
│   ├── i.方案禁止的合并用药清单/
│   └── j.依从性计算/
├── notebooks/          # Jupyter 原始笔记本（只读参考）
├── utils/              # 公共工具函数
│   ├── loaders.py      # 数据读取层（load_sheet / load_rand 等）
│   └── output_format.py # 报表输出函数（三线表、xlsx 等）
├── raw/                # 原始数据（不入 Git）
└── output/             # 生成的报表（不入 Git）
```

## Permissions
- `.ipynb` 文件：Claude Code 禁止编辑（只读，仅作参考）
- `scripts/`、`utils/`、`env.py`、`config.yaml`：Claude Code 可编辑
- `raw/`、`output/`：不在 Git 中

## Conventions
- 脚本通过标准 Python import 加载环境：`from env import pd, np, output_path, ...`
- 路径引导代码：`sys.path.insert(0, project_root)` 后 import（见已有脚本模板）
- 报表函数来自 `utils/output_format.py`
- 数据读取函数来自 `utils/loaders.py`（`load_sheet` / `load_rand` 等）
- 生成文件路径由 `config.yaml` 的 `output_path` 控制（env.py 自动解析为绝对路径）
- 虚拟环境位于 `.venv/`，安装依赖：`pip install -r requirements.txt`
- `env.py` 也可在 Jupyter 中通过 `%run` 直接运行（变量注入当前命名空间）

## 命名规范

### 变量前缀
- **DataFrame**：`df_` 前缀，如 `df_icf`、`df_end_info`、`df_out`
- **列名变量**（字符串常量）：`VAR_` 前缀，如 `VAR_SUBJ`、`VAR_STUDY_START`
- **导入列名集合**：`IMPORT_` 前缀，如 `IMPORT_RAND`、`IMPORT_ICF`

### 列名集中管理
脚本顶部集中声明所有中文列名，分三区，每区用注释标题隔开：

```python
# ── 列名集中管理 ──

# 导入列名（load_sheet / load_rand 的 usecols）
IMPORT_RAND  = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_ICF   = ['受试者', '知情同意书签署日期', '知情同意书签署时间']
IMPORT_END   = ['受试者', '试验完成日期', '提前退出日期']

# 中间列名（归一化 / 筛选 / 派生阶段产生或引用）
VAR_SUBJ          = "受试者"
VAR_ICF_SIGN_DATE = "知情同意书签署日期"
VAR_SIGN_DT       = "签署日期时间"       # 归一化阶段派生
VAR_STUDY_END     = "研究结束日期"
VAR_CASE_TYPE     = "首末例"             # 筛选阶段产生

# 输出列名（rename 映射目标 + 最终列序）
VAR_SCREEN_NO     = "筛选号"
VAR_STUDY_START   = "研究开始日期"
VAR_COMPLETED     = "是否完成试验"
VAR_STUDY_DAYS    = "试验时长（天）"
OUTPUT_COLS = [VAR_SUBJ, VAR_SCREEN_NO, ...]
```

**三区职责：**
- `IMPORT_*`：只出现在 `load_sheet` / `load_rand` 的 `cols` 参数中
- `VAR_*`（中间）：出现在归一化、筛选、派生、连接步骤中
- `VAR_*`（输出）+ `OUTPUT_COLS`：出现在 rename 映射和最终选列中

**注意事项：**
- rename 操作可能导致列名语义变化（如 `"首末例" → "受试者"`），`OUTPUT_COLS` 中引用的是 rename 后的实际列名
- 同一个 `VAR_SUBJ` 在 rename 前指"受试者原始 ID"，rename 后指"首例/末例"标签，由 rename 操作保证衔接

## 脚本结构：八步操作模型

每张表的脚本按以下步骤组织（顺序可重复、可交错，非每步必选）。
此模型只作**约定 + 决定什么进 utils**，不做成运行时引擎。

| 组 | 步骤 | 复用性 / 去向 |
|---|---|---|
| 固定书挡（前） | **1 读取** | 高 → `loaders.py` |
| | **2 归一化**（列名映射、日期/数值 parse、多表 concat、去重） | 高 → `loaders.py` |
| 柔性内核 | **3 筛选**（布尔过滤、组内选行、去重留首/末） | 低，留在表文件 |
| | **4 变形**（melt/pivot、groupby 聚合、crosstab） | 中，聚合可进 `loaders.py` |
| | **5 派生**（日期差、np.where、多选拼接、regex） | 低，留在表文件 |
| | **6 连接**（富化连接=高复用；关联/自连接=独有） | 富化 → `loaders.py`，关联留表文件 |
| 固定书挡（后） | **7 格式化**（选列、列序、改展示名、strftime、%/Int） | 高 → utils |
| | **8 输出**（三线表/xlsx、标题含例次例数、脚注、合并列） | 高 → `output_format.py` |

脚本中用 `# ── N 步骤名 ──` 标记每个阶段的起始位置。
