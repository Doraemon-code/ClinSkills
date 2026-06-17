import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet

# ── 列名集中管理 ──

# 导入列名（load_sheet 的 usecols）
IMPORT_DS_INTED = ['受试者', '永久终止试验干预原因_TXT', '其他永久终止试验干预的原因']
IMPORT_EC       = ['受试者', '开始日期', '结束日期']
IMPORT_DS_END   = ['受试者', '受试者是否完成试验_TXT']
IMPORT_RAND     = ['受试者', '随机号']

# 中文列名常量
VAR_SUBJ           = "受试者"
VAR_TERM_REASON    = "永久终止试验干预原因_TXT"
VAR_OTHER_DETAIL   = "其他永久终止试验干预的原因"
VAR_START_DATE     = "开始日期"
VAR_END_DATE       = "结束日期"
VAR_FIRST_DOSE     = "首次用药日期"
VAR_LAST_DOSE      = "末次用药日期"
VAR_TREAT_DAYS     = "治疗天数（天）"
VAR_COMPLETE       = "受试者是否完成试验_TXT"

# 输出列名
VAR_SCREEN_NO      = "筛选号"
VAR_RAND_NO        = "随机号"
VAR_TERM_REASON_OUT = "提前终止治疗的原因"
VAR_COMPLETED      = "是否完成试验"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_FIRST_DOSE, VAR_LAST_DOSE,
               VAR_TREAT_DAYS, VAR_TERM_REASON_OUT, VAR_COMPLETED]

# ── 1 读取 ──

df_inted = load_sheet("DS_INTED", IMPORT_DS_INTED).fillna("")
df_ec    = load_sheet("EC_ED", IMPORT_EC).fillna("")
df_end   = load_sheet("DS_END", IMPORT_DS_END).fillna("")
df_rand  = load_sheet("DS_RAND", IMPORT_RAND)

# ── 3 筛选 ──

# DS_INTED：只取"其他"原因的受试者
df_inted = df_inted[df_inted[VAR_TERM_REASON] == "其他"]

# ── 5 派生 ──

# 提前终止治疗的原因：合并原因 + "其他"具体说明
df_inted[VAR_TERM_REASON_OUT] = df_inted.apply(
    lambda r: f"{r[VAR_TERM_REASON]}：{r[VAR_OTHER_DETAIL]}"
              if r[VAR_OTHER_DETAIL] else r[VAR_TERM_REASON],
    axis=1,
)

# ── 2 归一化 ──

df_ec[VAR_START_DATE] = pd.to_datetime(df_ec[VAR_START_DATE], errors="coerce")
df_ec[VAR_END_DATE]   = pd.to_datetime(df_ec[VAR_END_DATE], errors="coerce")

# EC_ED 每受试者可能有多条记录，聚合为最早/最晚日期
df_ec = (df_ec.groupby(VAR_SUBJ, dropna=False)
              .agg({VAR_START_DATE: "min", VAR_END_DATE: "max"})
              .reset_index()
        )

df_ec[VAR_TREAT_DAYS] = (df_ec[VAR_END_DATE] - df_ec[VAR_START_DATE]).dt.days + 1
df_ec[VAR_TREAT_DAYS] = df_ec[VAR_TREAT_DAYS].astype("Int64").astype("string").fillna("")
df_ec[VAR_FIRST_DOSE] = df_ec[VAR_START_DATE].dt.strftime("%Y-%m-%d")
df_ec[VAR_LAST_DOSE]  = df_ec[VAR_END_DATE].dt.strftime("%Y-%m-%d")

# ── 6 连接 ──

df_out = (df_inted.merge(df_rand, on=[VAR_SUBJ], how="left")
                  .merge(df_ec,   on=[VAR_SUBJ], how="left")
                  .merge(df_end,  on=[VAR_SUBJ], how="left")
          )

df_out = df_out.rename(columns={
    VAR_SUBJ:    VAR_SCREEN_NO,
    VAR_COMPLETE: VAR_COMPLETED,
})

# ── 7 格式化 ──

df_out = df_out[OUTPUT_COLS]
df_out = df_out.fillna("<NA>")

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

notes = [
    "治疗天数（天）= 试验药物末次用药日期 - 试验药物首次用药日期 + 1；",
]

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表5 因其他原因而发生的提前终止治疗.docx',
    '表5 因其他原因而发生的提前终止治疗',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
