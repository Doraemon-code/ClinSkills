import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, output_path, save_table_to_docx_threeline
from utils.loaders import load_sheet

# ── 列名集中管理 ──

# 导入列名
IMPORT_DS_INTED = ['受试者', '页面名称', '永久终止试验干预原因_TXT']
IMPORT_EC       = ['受试者', '开始日期', '结束日期']
IMPORT_DS_END   = ['受试者', '页面名称', '受试者是否完成试验_TXT']
IMPORT_AE       = ['受试者', '不良事件名称',
                   '对试验药物采取的措施-1_TXT', '对试验药物采取的措施-2_TXT',
                   '对试验药物采取的措施-3_TXT', '对试验药物采取的措施-4_TXT',
                   '对试验药物采取的措施-5_TXT', '对试验药物采取的措施-6_TXT',
                   '与试验药物的关系_TXT', '导致死亡']
IMPORT_RAND     = ['受试者', '随机号']

# 中间列名
VAR_SUBJ         = "受试者"
VAR_TERM_REASON  = "永久终止试验干预原因_TXT"
VAR_START_DATE   = "开始日期"
VAR_END_DATE     = "结束日期"
VAR_FIRST_DOSE   = "首次用药日期"
VAR_LAST_DOSE    = "末次用药日期"
VAR_TREAT_DAYS   = "治疗天数（天）"
VAR_COMPLETE     = "受试者是否完成试验_TXT"
VAR_MEASURES     = "对试验药物采取的措施"
VAR_AE_NAME      = "不良事件名称"
VAR_RELATION     = "与试验药物的关系_TXT"
VAR_DEATH        = "导致死亡"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_RAND_NO      = "随机号"
VAR_RELATION_OUT = "与试验用药品的关系"
VAR_TERM_REASON_OUT = "提前终止治疗的原因"
VAR_COMPLETED    = "是否完成试验"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_FIRST_DOSE, VAR_LAST_DOSE,
               VAR_TREAT_DAYS, VAR_AE_NAME, VAR_RELATION_OUT,
               VAR_TERM_REASON_OUT, VAR_COMPLETED]

MEASURE_COLS = [
    "对试验药物采取的措施-1_TXT", "对试验药物采取的措施-2_TXT",
    "对试验药物采取的措施-3_TXT", "对试验药物采取的措施-4_TXT",
    "对试验药物采取的措施-5_TXT", "对试验药物采取的措施-6_TXT",
]

# ── 1 读取 ──

df_inted = load_sheet("DS_INTED", IMPORT_DS_INTED)
df_ec    = load_sheet("EC_ED", IMPORT_EC).fillna("")
df_end   = load_sheet("DS_END", IMPORT_DS_END).fillna("")
df_ae    = load_sheet("AE", IMPORT_AE)
df_rand  = load_sheet("DS_RAND", IMPORT_RAND)

# ── 3 筛选 ──

df_inted = df_inted[
    df_inted[VAR_TERM_REASON] == "试验期间受试者发生不良事件，研究者认为受试者需永久停止服用试验用药品"
]
df_inted = df_inted.drop(columns=["页面名称"])

# ── 2 归一化 ──

df_ec[VAR_START_DATE] = pd.to_datetime(df_ec[VAR_START_DATE], errors="coerce")
df_ec[VAR_END_DATE]   = pd.to_datetime(df_ec[VAR_END_DATE], errors="coerce")

df_ae[VAR_MEASURES] = df_ae[MEASURE_COLS].apply(
    lambda row: ",".join(
        [x.strip() for x in row
         if pd.notna(x) and str(x).strip() not in ["", "nan", "NaN"]]
    ),
    axis=1,
)
df_ae = df_ae[(df_ae[VAR_MEASURES] == "永久停药") | (df_ae[VAR_DEATH] == "Y")]

# ── 5 派生 ──

df_ec[VAR_TREAT_DAYS] = (df_ec[VAR_END_DATE] - df_ec[VAR_START_DATE]).dt.days + 1
df_ec[VAR_TREAT_DAYS] = df_ec[VAR_TREAT_DAYS].astype("Int64").astype("string").fillna("")

df_ec[VAR_FIRST_DOSE] = df_ec[VAR_START_DATE].dt.strftime("%Y-%m-%d")
df_ec[VAR_LAST_DOSE]  = df_ec[VAR_END_DATE].dt.strftime("%Y-%m-%d")

# ── 6 连接 ──

df_out = (df_inted.merge(df_rand, on=[VAR_SUBJ], how="left")
                  .merge(df_ec,    on=[VAR_SUBJ], how="left")
                  .merge(df_end,   on=[VAR_SUBJ], how="left")
                  .merge(df_ae,    on=[VAR_SUBJ], how="left")
          )

df_out = df_out.rename(columns={
    VAR_SUBJ:        VAR_SCREEN_NO,
    VAR_RELATION:    VAR_RELATION_OUT,
    VAR_TERM_REASON: VAR_TERM_REASON_OUT,
    VAR_COMPLETE:    VAR_COMPLETED,
})

# ── 7 格式化 ──

df_out = df_out[OUTPUT_COLS]

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

notes = [
    "治疗天数（天）= 试验药物末次用药日期 - 试验药物首次用药日期 + 1；",
]

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表9 因与试验用药品相关的不良事件而发生的提前终止治疗.docx',
    '表9 因与试验用药品相关的不良事件而发生的提前终止治疗',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
