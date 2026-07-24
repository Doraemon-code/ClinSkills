# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 医学编码情况汇总三线表：从医学编码 Excel 读取各表单编码明细，
#       按编码数据来源（不良事件/既往病史/合并用药等）汇总编码数量、
#       例次、例数及所用编码字典版本。
# @tags 医学编码,MedDRA,WHODRUG,编码字典,汇总,DMR,三线表
# @config REPORT_NAME, CODE_FILE, SHEETS

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import code_path, output_table_dir
from utils.output_format import save_table_to_docx_threeline
from docx.enum.table import WD_TABLE_ALIGNMENT

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列 sheet 名、表单名称、字典版本、列名均为项目特异。

REPORT_NAME = "医学编码情况"

CODE_FILE = code_path   # 编码文件完整路径（通常 config.code_path）

# 编码 sheet 配置：{ sheet_name: (表单名称, 编码字典版本) }
SHEETS = {
    "AE--不良事件":              ("不良事件",           "MedDRA 28.0 Chinese"),
    "MH--既往病史及现病史":       ("既往病史及现病史",    "MedDRA 28.0 Chinese"),
    "PR--既往合并非药物治疗":     ("既往合并非药物治疗",  "MedDRA 28.0 Chinese"),
    "CM--伴随用药记录":           ("伴随用药记录",        "WHODRUG GLOBAL B3 March 1, 2025 Chinese"),
}

# ── 列名集中管理 ──

IMPORT_SUBJECT = "受试者筛选号"

# ── 1 读取 ──

rows = []
total_n = 0
for sheet, (form_name, dict_version) in SHEETS.items():
    df = pd.read_excel(CODE_FILE, sheet_name=sheet, header=0, dtype=str)
    df = df.replace("", pd.NA)
    n_rows = len(df)
    n_subj = df[IMPORT_SUBJECT].nunique() if IMPORT_SUBJECT in df.columns else 0
    total_n += n_rows
    rows.append({
        "编码数据（表单名称）": form_name,
        "编码字典": dict_version,
        "编码数量": n_rows,
        "例次": n_rows,
        "例数": n_subj,
    })

df_out = pd.DataFrame(rows)

# ── 2 排序 ──

sheet_order = [v[0] for v in SHEETS.values()]
df_out["编码数据（表单名称）"] = pd.Categorical(
    df_out["编码数据（表单名称）"], categories=sheet_order, ordered=True
)
df_out = df_out.sort_values("编码数据（表单名称）").reset_index(drop=True)

# ── 8 输出 ──

notes = [f"本试验医学编码总条目数为{total_n}条"]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=False,
    include_notes=True,
    alignment=WD_TABLE_ALIGNMENT.CENTER,
)
