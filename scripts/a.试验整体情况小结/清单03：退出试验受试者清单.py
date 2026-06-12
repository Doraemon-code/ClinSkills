import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, np, output_path, save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND    = ['受试者', '受试者状态', '随机时间', '随机号']
IMPORT_ICF     = ['受试者', '知情同意书签署日期']
IMPORT_SV      = ['受试者', '访视OID', '访视名称', '访视日期']
IMPORT_SV_EXIT = ['受试者', '访视OID', '访视日期']
IMPORT_END     = ['受试者', '页面名称', '受试者退出试验原因_TXT',
                  '试验完成日期', '提前退出日期']
IMPORT_INTED   = ['受试者', '页面名称', '受试者是否永久终止试验干预_TXT']
IMPORT_EC      = ['受试者', '开始日期', '结束日期']

# 中间列名
VAR_SUBJ         = "受试者"
VAR_RAND_NO      = "随机号"
VAR_RAND_TIME    = "随机时间"
VAR_ICF_DATE     = "知情同意书签署日期"
VAR_START_DATE   = "开始日期"
VAR_END_DATE     = "结束日期"
VAR_FIRST_DOSE   = "首次用药日期"
VAR_LAST_DOSE    = "末次用药日期"
VAR_TREAT_DAYS   = "治疗天数（天）"
VAR_VISIT_NAME   = "访视名称"
VAR_VISIT_DATE   = "访视日期"
VAR_EARLY_EXIT   = "提前退出日期"
VAR_COMPLETE_DATE = "试验完成日期"
VAR_STUDY_END    = "研究结束日期"
VAR_EXIT_REASON  = "受试者退出试验原因_TXT"
VAR_TERMINATE    = "受试者是否永久终止试验干预_TXT"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_STUDY_START  = "研究开始日期"
VAR_STUDY_DAYS   = "试验时长（天）"
VAR_LAST_VISIT   = "末次已完成的计划内访视"
VAR_EXIT_VISIT   = "是否进行提前退出访视"
VAR_TERMINATE_OUT = "是否提前终止治疗"
VAR_EXIT_REASON_OUT = "提前退出原因"
VAR_SAFETY       = "用药后安全性指标评估情况"
VAR_EFFICACY     = "用药后疗效性指标评估情况"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_STUDY_START, VAR_RAND_TIME,
               VAR_FIRST_DOSE, VAR_LAST_DOSE, VAR_TREAT_DAYS,
               VAR_TERMINATE_OUT, VAR_STUDY_END, VAR_STUDY_DAYS,
               VAR_LAST_VISIT, VAR_EXIT_VISIT, VAR_SAFETY, VAR_EFFICACY,
               VAR_EXIT_REASON_OUT]

# ── 1 读取 ──

df_rand   = load_rand(cols=IMPORT_RAND)
df_icf    = load_sheet("DS_ICF", IMPORT_ICF)
df_sv     = load_sheet("SV", IMPORT_SV)
df_sv_exit = load_sheet("SV", IMPORT_SV_EXIT)
df_end    = load_sheet("DS_END", IMPORT_END)
df_inted  = load_sheet("DS_INTED", IMPORT_INTED)
df_ec     = load_sheet("EC_ED", IMPORT_EC).fillna("")

# ── 3 筛选 ──

df_out = df_rand[df_rand["受试者状态"] == "中止退出"].copy()

df_sv = df_sv[(df_sv["访视OID"] != "V90") & (df_sv["访视OID"] != "V80")]

df_sv_exit = df_sv_exit[df_sv_exit["访视OID"] == "V80"]
df_sv_exit[VAR_EXIT_VISIT] = "是"

# ── 2 归一化 ──

df_icf = df_icf.rename(columns={VAR_ICF_DATE: VAR_STUDY_START})

df_sv[VAR_VISIT_DATE] = pd.to_datetime(df_sv[VAR_VISIT_DATE], errors="coerce")
idx = df_sv.groupby(VAR_SUBJ)[VAR_VISIT_DATE].idxmax()
df_sv = df_sv.loc[idx, [VAR_SUBJ, VAR_VISIT_NAME, VAR_VISIT_DATE]]
df_sv = df_sv.rename(columns={VAR_VISIT_NAME: VAR_LAST_VISIT})

df_end[VAR_STUDY_END] = np.where(
    df_end[VAR_COMPLETE_DATE].notna(),
    df_end[VAR_COMPLETE_DATE],
    df_end[VAR_EARLY_EXIT],
)

df_ec[VAR_START_DATE] = pd.to_datetime(df_ec[VAR_START_DATE], errors="coerce")
df_ec[VAR_END_DATE]   = pd.to_datetime(df_ec[VAR_END_DATE], errors="coerce")

# ── 5 派生 ──

# 首末次用药日期 + 治疗天数
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

# ── 6 连接 ──

df_out = (df_out.merge(df_ec_out, on=[VAR_SUBJ], how="left")
               .merge(df_sv,      on=[VAR_SUBJ], how="left")
               .merge(df_end,     on=[VAR_SUBJ], how="left")
               .merge(df_inted,   on=[VAR_SUBJ], how="left")
               .merge(df_icf,     on=[VAR_SUBJ], how="left")
               .merge(df_sv_exit, on=[VAR_SUBJ], how="left")
        )

df_out = df_out.rename(columns={
    VAR_EXIT_REASON: VAR_EXIT_REASON_OUT,
    VAR_SUBJ:        VAR_SCREEN_NO,
    VAR_TERMINATE:   VAR_TERMINATE_OUT,
})

# ── 5 派生（续）──

# 试验时长
df_out[VAR_STUDY_END]   = pd.to_datetime(df_out[VAR_STUDY_END], errors="coerce")
df_out[VAR_STUDY_START] = pd.to_datetime(df_out[VAR_STUDY_START], errors="coerce")
df_out[VAR_STUDY_DAYS]  = (df_out[VAR_STUDY_END] - df_out[VAR_STUDY_START]).dt.days + 1

# 占位列
df_out[VAR_SAFETY]   = "有/无"
df_out[VAR_EFFICACY] = "有/无"

# ── 7 格式化 ──

df_out[VAR_STUDY_END]   = df_out[VAR_STUDY_END].dt.strftime("%Y-%m-%d")
df_out[VAR_STUDY_START] = df_out[VAR_STUDY_START].dt.strftime("%Y-%m-%d")

df_out = df_out[OUTPUT_COLS]

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

notes = [
    "提前退出：受试者未进行访视6（V6，D71±3）；",
    "治疗天数（天）=末次用药日期-首次用药日期+1；",
    "研究开始日期：最早一次知情同意书签署日期；",
    "研究结束日期：最晚一次访视完成日期；",
    "试验时长（天）=研究结束日期-研究开始日期+1。",
]

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表5 退出试验受试者清单（{n}例）.docx',
    '表5 退出试验受试者清单',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
