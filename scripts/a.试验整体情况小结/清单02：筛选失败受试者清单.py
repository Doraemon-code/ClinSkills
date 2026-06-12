import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, output_path, export_to_excel_with_format
from utils.loaders import load_rand, load_sheet

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ['受试者', '受试者状态', '受试者是否随机入组_TXT',
               '不符合入选标准', '符合排除标准', '撤回知情同意',
               '失访，尝试联系≥3次均未成功', '其他筛选失败原因']
IMPORT_ICF  = ['受试者', '知情同意书签署日期']

# 中间列名
VAR_SUBJ        = "受试者"
VAR_STATUS      = "受试者状态"
VAR_ICF_DATE    = "知情同意书签署日期"
VAR_REASON      = "筛选失败原因"
VAR_RESULT      = "结果"

# 输出列名
VAR_SCREEN_NO   = "筛选号"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_ICF_DATE, VAR_REASON]

# 筛选失败原因列
REASON_COLS = ['不符合入选标准', '符合排除标准', '撤回知情同意',
               '失访，尝试联系≥3次均未成功', '其他筛选失败原因']

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_icf  = load_sheet("DS_ICF", IMPORT_ICF)

# ── 4 变形 ──

df_fail = df_rand.melt(
    id_vars=[VAR_SUBJ, VAR_STATUS, "受试者是否随机入组_TXT"],
    value_vars=REASON_COLS,
    var_name=VAR_REASON,
    value_name=VAR_RESULT,
)

# ── 3 筛选 ──

df_fail = df_fail[(df_fail[VAR_STATUS] == "筛选失败") & (df_fail[VAR_RESULT] == '1')]

# ── 6 连接 ──

df_out = df_fail.merge(df_icf, on=[VAR_SUBJ], how="left")

# ── 7 格式化 ──

df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})
df_out = df_out[OUTPUT_COLS]

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

export_to_excel_with_format(
    df_out,
    f"{output_path}/listing/表32 筛选失败受试者清单.xlsx",
    "表32 筛选失败受试者清单",
    f"表32 筛选失败受试者清单（{n}例）",
)
