# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 首末例受试者情况三线表：首例=最早签署知情同意书的受试者，
#       末例=最晚结束研究的受试者。汇总其筛选号、随机号/随机时间、研究
#       起止日期、试验时长与是否完成试验。研究结束日期取完成日期，缺失
#       时回退为提前退出日期。首/末例并列时各取一条代表记录。
# @tags 首末例,首例,末例,知情同意,随机,研究时长,DMR,三线表,报表,试验整体情况
# @config REPORT_NAME, FORM_ICF/FORM_END/FORM_RAND,
#         IMPORT_ICF_DATE/IMPORT_ICF_TIME,
#         IMPORT_COMPLETE_DATE/IMPORT_EARLY_EXIT/IMPORT_COMPLETED,
#         IMPORT_RAND_NO/IMPORT_RAND_TIME

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（读取用 EDC 专属名，勿硬编码）──

VAR_SUBJ = system_cols("subject")   # 受试者/筛选号列，按 EDC 自动取名（taimei5→受试者 / cmis→SUBJID …）

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID 与字段名均为项目特异，须据 query_metadata.py 实际探索结果替换。
# 示例值取自某 taimei5 项目，仅作占位。

REPORT_NAME = "首末例受试者情况"

# 表单 OID（sheet 名）
FORM_ICF  = "DS_ICF"     # 知情同意书表单
FORM_END  = "DS_END"     # 研究结束/试验结束表单
FORM_RAND = "DS_RAND"    # 随机表单（若随机信息在独立文件，改用对应读取方式）

# 知情同意书字段
IMPORT_ICF_DATE = "知情同意书签署日期"
IMPORT_ICF_TIME = "知情同意书签署时间"

# 研究结束字段
IMPORT_COMPLETE_DATE = "试验完成日期"          # 完成试验者的结束日期
IMPORT_EARLY_EXIT    = "提前退出日期"          # 提前退出者的结束日期
IMPORT_COMPLETED     = "受试者是否完成试验_TXT"  # 是否完成试验（解码列；后缀随 EDC：taimei→_TXT / cmis→_DEC / clinflash 解码值含于列名）

# 随机字段
IMPORT_RAND_NO   = "随机号"
IMPORT_RAND_TIME = "随机时间"

# ── 列名集中管理（中间 + 输出）──

# 中间列名（归一化 / 派生阶段产生或引用）
VAR_SIGN_DT   = "签署日期时间"
VAR_CASE_TYPE = "首末例"

# 输出列名（中文报表表头）
_OUT_CASE       = "受试者"        # 值为「首例」/「末例」
VAR_SCREEN_NO   = "筛选号"
VAR_RAND_NO     = "随机号"
VAR_RAND_TIME   = "随机时间"
VAR_STUDY_START = "研究开始日期"
VAR_STUDY_END   = "研究结束日期"
VAR_STUDY_DAYS  = "试验时长（天）"
VAR_COMPLETED   = "是否完成试验"

OUTPUT_COLS = [_OUT_CASE, VAR_SCREEN_NO, VAR_RAND_NO, VAR_STUDY_START,
               VAR_RAND_TIME, VAR_STUDY_END, VAR_STUDY_DAYS, VAR_COMPLETED]

# ── 1 读取 ──

df_icf  = load_sheet(FORM_ICF,  usecols=[VAR_SUBJ, IMPORT_ICF_DATE, IMPORT_ICF_TIME])
df_end  = load_sheet(FORM_END,  usecols=[VAR_SUBJ, IMPORT_COMPLETED, IMPORT_COMPLETE_DATE, IMPORT_EARLY_EXIT])
df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_RAND_NO, IMPORT_RAND_TIME])

# ── 2 归一化 ──

# 签署日期 + 签署时间 → 完整时间戳（时间缺失按 00:00 补）
df_icf[VAR_SIGN_DT] = pd.to_datetime(
    df_icf[IMPORT_ICF_DATE].astype(str).str.strip() + " " +
    df_icf[IMPORT_ICF_TIME].fillna("00:00").astype(str).str.strip(),
    errors="coerce",
)

# 研究结束日期 = 完成日期，缺失则取提前退出日期
df_end[VAR_STUDY_END] = np.where(
    df_end[IMPORT_COMPLETE_DATE].notna(),
    df_end[IMPORT_COMPLETE_DATE],
    df_end[IMPORT_EARLY_EXIT],
)

# ── 3 筛选：定位首例（最早签署）与末例（最晚结束）──

earliest_sign = df_icf[VAR_SIGN_DT].min()
df_first_case = df_icf.loc[df_icf[VAR_SIGN_DT] == earliest_sign, [VAR_SUBJ]].copy()
df_first_case[VAR_CASE_TYPE] = "首例"

end_dt = pd.to_datetime(df_end[VAR_STUDY_END], errors="coerce")
latest_end = end_dt.max()
df_last_case = df_end.loc[end_dt == latest_end, [VAR_SUBJ]].copy()
df_last_case[VAR_CASE_TYPE] = "末例"

# ── 6 连接 ──

df_out = pd.concat([df_first_case, df_last_case])
df_out = (df_out.merge(df_icf,  on=[VAR_SUBJ], how="left")
                .merge(df_end,  on=[VAR_SUBJ], how="left")
                .merge(df_rand, on=[VAR_SUBJ], how="left")
         )

df_out = df_out.rename(columns={
    VAR_SUBJ:         VAR_SCREEN_NO,    # EDC 受试者列 → 筛选号
    IMPORT_ICF_DATE:  VAR_STUDY_START,  # 知情同意书签署日期 → 研究开始日期
    IMPORT_COMPLETED: VAR_COMPLETED,    # 是否完成试验（解码列）→ 是否完成试验
    IMPORT_RAND_NO:   VAR_RAND_NO,      # 随机号列名归一
    IMPORT_RAND_TIME: VAR_RAND_TIME,    # 随机时间列名归一
    VAR_CASE_TYPE:    _OUT_CASE,        # 首末例 → 受试者
})

# 首/末例各取一条代表记录（多受试者并列时，首例按研究结束日期、末例按研究开始日期取其一）
df_first = df_out[df_out[_OUT_CASE] == "首例"]
df_first = df_first.loc[df_first[VAR_STUDY_END].idxmax(), :].to_frame().T
df_last  = df_out[df_out[_OUT_CASE] == "末例"]
df_last  = df_last.loc[df_last[VAR_STUDY_START].idxmax(), :].to_frame().T
df_out = pd.concat([df_first, df_last])

# ── 5 派生：试验时长 ──

df_out[VAR_STUDY_END]   = pd.to_datetime(df_out[VAR_STUDY_END], errors="coerce")
df_out[VAR_STUDY_START] = pd.to_datetime(df_out[VAR_STUDY_START], errors="coerce")
df_out[VAR_STUDY_DAYS]  = (df_out[VAR_STUDY_END] - df_out[VAR_STUDY_START]).dt.days + 1

# ── 7 格式化 ──

df_out[VAR_STUDY_START] = df_out[VAR_STUDY_START].dt.strftime("%Y-%m-%d")
df_out[VAR_STUDY_END]   = df_out[VAR_STUDY_END].dt.strftime("%Y-%m-%d")
df_out = df_out[OUTPUT_COLS]

# ── 8 输出 ──

notes = [
    "首例病例为入组受试者中第一例签署知情同意书的受试者；末例病例为入组受试者中最后结束研究的受试者；",
    "研究开始日期：最早一次知情同意书签署日期；",
    "研究结束日期：最晚一次访视完成日期；",
    "试验时长（天）=研究结束日期-研究开始日期+1。",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
