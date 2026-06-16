import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, np, output_path, export_to_excel_with_format
from utils.loaders import load_rand, load_sheet

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND   = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_END    = ['受试者', '页面名称', '受试者是否完成试验_TXT',
                 '试验完成日期', '提前退出日期']
IMPORT_EC     = ['受试者', '开始日期', '结束日期']
IMPORT_SV     = ['受试者', '访视OID', '访视日期']
IMPORT_ICF    = ['受试者', '知情同意书签署日期']

# 中间列名
VAR_SUBJ         = "受试者"
VAR_RAND_NO      = "随机号"
VAR_RAND_TIME    = "随机时间"
VAR_START_DATE   = "开始日期"
VAR_END_DATE     = "结束日期"
VAR_FIRST_DOSE   = "首次用药日期"
VAR_LAST_DOSE    = "末次用药日期"
VAR_TREAT_DAYS   = "治疗天数（天）"
VAR_VISIT_DATE   = "访视日期"
VAR_ICF_DATE     = "知情同意书签署日期"
VAR_STUDY_END    = "研究完成日期"
VAR_STUDY_START  = "研究开始日期"
VAR_EARLY_EXIT   = "提前退出日期"
VAR_COMPLETE_DATE = "试验完成日期"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_STUDY_DAYS   = "试验时长（天）"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_ICF_DATE, VAR_RAND_TIME,
               VAR_FIRST_DOSE, VAR_LAST_DOSE, VAR_TREAT_DAYS,
               VAR_COMPLETE_DATE, VAR_STUDY_DAYS]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_end  = load_sheet("DS_END", IMPORT_END).fillna("")
df_ec   = load_sheet("EC_ED", IMPORT_EC).fillna("")
df_sv   = load_sheet("SV", IMPORT_SV)
df_icf  = load_sheet("DS_ICF", IMPORT_ICF)

# ── 3 筛选 ──

df_rand = df_rand[df_rand["受试者状态"] == "完成试验"]

df_sv = df_sv[(df_sv["访视OID"] != "V90") & (df_sv["访视OID"] != "V80")]

# ── 2 归一化 ──

df_ec[VAR_START_DATE] = pd.to_datetime(df_ec[VAR_START_DATE], errors="coerce")
df_ec[VAR_END_DATE]   = pd.to_datetime(df_ec[VAR_END_DATE], errors="coerce")

df_sv[VAR_VISIT_DATE] = pd.to_datetime(df_sv[VAR_VISIT_DATE], errors="coerce")

# ── 5 派生 ──

# 首末次用药日期
df_ec1 = (
    df_ec.groupby(VAR_SUBJ, dropna=False)[VAR_START_DATE]
         .agg(["min"])
         .rename(columns={"min": VAR_FIRST_DOSE})
)
df_ec2 = (
    df_ec.groupby(VAR_SUBJ, dropna=False)[VAR_END_DATE]
         .agg(["max"])
         .rename(columns={"max": VAR_LAST_DOSE})
)
df_ec_out = df_ec1.merge(df_ec2, on=[VAR_SUBJ], how="inner")

df_ec_out[VAR_TREAT_DAYS] = (df_ec_out[VAR_LAST_DOSE] - df_ec_out[VAR_FIRST_DOSE]).dt.days + 1
df_ec_out[VAR_TREAT_DAYS] = df_ec_out[VAR_TREAT_DAYS].where(
    df_ec_out[VAR_TREAT_DAYS] > 0, np.nan
)
df_ec_out = df_ec_out.reset_index()

# 最晚访视日期
idx = df_sv.groupby(VAR_SUBJ)[VAR_VISIT_DATE].idxmax()
df_sv = df_sv.loc[idx, [VAR_SUBJ, VAR_VISIT_DATE]]

# 研究结束日期 = 试验完成日期（优先）或提前退出日期
df_end[VAR_STUDY_END] = np.where(
    df_end[VAR_COMPLETE_DATE].notna(),
    df_end[VAR_COMPLETE_DATE],
    df_end[VAR_EARLY_EXIT],
)

# ── 6 连接 ──

df_out = (df_rand.merge(df_ec_out, on=[VAR_SUBJ], how="left")
                .merge(df_icf,     on=[VAR_SUBJ], how="left")
                .merge(df_end,     on=[VAR_SUBJ], how="left")
          )

# ── 5 派生（续）──

df_out[VAR_STUDY_END]   = pd.to_datetime(df_out[VAR_STUDY_END], errors="coerce")
df_out[VAR_ICF_DATE]    = pd.to_datetime(df_out[VAR_ICF_DATE], errors="coerce")
df_out[VAR_STUDY_DAYS]  = (df_out[VAR_STUDY_END] - df_out[VAR_ICF_DATE]).dt.days + 1

df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})

# ── 7 格式化 ──

df_out[VAR_FIRST_DOSE]  = df_out[VAR_FIRST_DOSE].dt.strftime("%Y-%m-%d")
df_out[VAR_LAST_DOSE]   = df_out[VAR_LAST_DOSE].dt.strftime("%Y-%m-%d")
df_out[VAR_ICF_DATE]    = df_out[VAR_ICF_DATE].dt.strftime("%Y-%m-%d")
df_out[VAR_STUDY_END]   = df_out[VAR_STUDY_END].dt.strftime("%Y-%m-%d")

df_out = df_out[OUTPUT_COLS]

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/完成试验受试者清单.xlsx",
    "完成试验受试者清单",
    f"完成试验受试者清单（{n}例）",
)
