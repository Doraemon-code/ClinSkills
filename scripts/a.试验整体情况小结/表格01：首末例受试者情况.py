import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, np, output_path, save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet

# ── 列名集中管理 ──

# 导入列名（load_sheet / load_rand 的 usecols）
IMPORT_RAND   = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_END_A  = ['受试者', '页面名称', '受试者是否完成试验_TXT']
IMPORT_ICF    = ['受试者', '知情同意书签署日期', '知情同意书签署时间']
IMPORT_END_B  = ['受试者', '试验完成日期', '提前退出日期']

# 中间列名（归一化 / 筛选 / 派生阶段产生或引用）
VAR_SUBJ           = "受试者"
VAR_ICF_SIGN_DATE  = "知情同意书签署日期"
VAR_ICF_SIGN_TIME  = "知情同意书签署时间"
VAR_COMPLETE_DATE  = "试验完成日期"
VAR_EARLY_EXIT     = "提前退出日期"
VAR_SIGN_DT        = "签署日期时间"
VAR_STUDY_END      = "研究结束日期"
VAR_CASE_TYPE       = "首末例"

# 输出列名（最终表格的列名与 rename 映射）
VAR_SCREEN_NO      = "筛选号"
VAR_STUDY_START    = "研究开始日期"
VAR_COMPLETED      = "是否完成试验"
VAR_RAND_NO        = "随机号"
VAR_RAND_TIME      = "随机时间"
VAR_STUDY_DAYS     = "试验时长（天）"
# rename 后 "首末例" → "受试者"，"受试者" → "筛选号"，最终列名受试者 = 原首末例
OUTPUT_COLS = [VAR_SUBJ, VAR_SCREEN_NO, VAR_RAND_NO, VAR_STUDY_START,
               VAR_RAND_TIME, VAR_STUDY_END, VAR_STUDY_DAYS, VAR_COMPLETED]

# ── 1 读取 ──

df_rand     = load_rand(cols=IMPORT_RAND)
df_end_raw  = load_sheet("DS_END", IMPORT_END_A)
df_icf      = load_sheet("DS_ICF", IMPORT_ICF)
df_end_info = load_sheet("DS_END", IMPORT_END_B)

# ── 2 归一化 ──

df_icf[VAR_SIGN_DT] = pd.to_datetime(
    df_icf[VAR_ICF_SIGN_DATE].astype(str).str.strip() + " " +
    df_icf[VAR_ICF_SIGN_TIME].fillna("00:00").astype(str).str.strip(),
    errors="coerce",
)

df_end_info[VAR_STUDY_END] = np.where(
    df_end_info[VAR_COMPLETE_DATE].notna(),
    df_end_info[VAR_COMPLETE_DATE],
    df_end_info[VAR_EARLY_EXIT],
)

# ── 3 筛选 ──

earliest_sign = df_icf[VAR_SIGN_DT].min()
df_first_case = df_icf.loc[df_icf[VAR_SIGN_DT] == earliest_sign, [VAR_SUBJ]].copy()
df_first_case[VAR_CASE_TYPE] = "首例"

end_dt = pd.to_datetime(df_end_info[VAR_STUDY_END], errors="coerce")
latest_end = end_dt.max()
df_last_case = df_end_info.loc[end_dt == latest_end, [VAR_SUBJ]].copy()
df_last_case[VAR_CASE_TYPE] = "末例"

# ── 6 连接 ──

df_out = pd.concat([df_first_case, df_last_case])
df_out = (df_out.merge(df_icf, on=[VAR_SUBJ], how="left")
                .merge(df_end_info, on=[VAR_SUBJ], how="left")
                .merge(df_rand, on=[VAR_SUBJ], how="left")
                .merge(df_end_raw, on=[VAR_SUBJ], how="left")
         )

df_out = df_out.rename(columns={
    VAR_SUBJ:          VAR_SCREEN_NO,
    VAR_ICF_SIGN_DATE: VAR_STUDY_START,
    "受试者是否完成试验_TXT": VAR_COMPLETED,
    VAR_CASE_TYPE:     VAR_SUBJ,
})

df_first = df_out[df_out[VAR_SUBJ] == '首例']
df_first = df_first.loc[df_first[VAR_STUDY_END].idxmax(), :].to_frame().T
df_last = df_out[df_out[VAR_SUBJ] == '末例']
df_last = df_last.loc[df_last[VAR_STUDY_START].idxmax(), :].to_frame().T
df_out = pd.concat([df_first, df_last])

# ── 5 派生 ──

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
    f'{output_path}/table/表1 首末例受试者情况.docx',
    '表1 首末例受试者情况',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
