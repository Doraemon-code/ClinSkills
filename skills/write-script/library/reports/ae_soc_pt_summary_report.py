# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 不良事件按 SOC/PT 汇总三线表：从医学编码 Excel 读取 AE 编码数据，
#       按系统器官分类(SOC)和首选语(PT)分组汇总例数与例次，
#       输出按 SOC 合并单元格的三线表。
# @tags 不良事件,AE,SOC,PT,MedDRA,医学编码,汇总,DMR,三线表
# @config REPORT_NAME, CODE_FILE, SHEET_AE, IMPORT_SUBJECT/IMPORT_SOC/IMPORT_PT

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import code_path, output_table_dir
from utils.output_format import save_table_to_docx_threeline

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列字段名、sheet 名均为项目特异，须据实际编码文件探索替换。

REPORT_NAME = "不良事件按照SOC、PT汇总情况"

# 医学编码文件与 sheet
CODE_FILE = code_path        # 编码文件完整路径（通常 config.code_path）
SHEET_AE  = "AE--不良事件"    # AE 编码 sheet 名

# 编码文件中的列名
IMPORT_SUBJECT = "受试者筛选号"
IMPORT_SOC     = "系统器官分类术语(SOC)"
IMPORT_PT      = "首选语术语(PT)"

# ── 列名集中管理 ──

VAR_SUBJECT = IMPORT_SUBJECT
VAR_SOC     = IMPORT_SOC
VAR_PT      = IMPORT_PT

# ── 1 读取 ──

df_code = pd.read_excel(CODE_FILE, sheet_name=SHEET_AE, dtype=str)

# ── 3 筛选 ──

df_ae = df_code[[VAR_SUBJECT, VAR_SOC, VAR_PT]].drop_duplicates()

# ── 4 变形：按 SOC + PT 分组汇总 ──

df_summary = df_ae.groupby([VAR_SOC, VAR_PT]).agg(
    例数=(VAR_SUBJECT, "nunique"),
    例次=(VAR_SUBJECT, "size"),
).reset_index()

df_summary = df_summary.rename(columns={VAR_SOC: "SOC", VAR_PT: "PT"})

# ── 7 格式化 ──

df_summary = df_summary.sort_values(["SOC", "PT"]).reset_index(drop=True)

# ── 8 输出 ──

save_table_to_docx_threeline(
    df_summary,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    [],
    row_height_cm=0.6,
    auto_width=True,
    include_notes=False,
    merge_columns=["SOC"],
)
