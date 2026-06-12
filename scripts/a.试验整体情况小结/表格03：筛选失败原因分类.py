import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from env import pd, output_path, save_table_to_docx_threeline
from utils.loaders import load_rand

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ['受试者是否随机入组_TXT',
               '不符合入选标准', '符合排除标准', '撤回知情同意',
               '失访，尝试联系≥3次均未成功', '其他']

# 中间列名
VAR_RAND_STATUS = "受试者是否随机入组_TXT"

# 输出列名
VAR_REASON = "筛选失败原因"
VAR_COUNT  = "例次"
OUTPUT_COLS = [VAR_REASON, VAR_COUNT]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)

# ── 3 筛选 ──

df_fail = df_rand[df_rand[VAR_RAND_STATUS] == "否"]
df_fail = df_fail.drop(columns=[VAR_RAND_STATUS])

# ── 4 变形 ──

reasons = IMPORT_RAND[1:]  # 去掉第一个状态列
df_out = pd.DataFrame({
    VAR_REASON: reasons,
    VAR_COUNT:  [(df_fail[col] == "1").sum() for col in reasons],
})

# 合计行
df_out.loc[len(df_out)] = ["合计", df_out[VAR_COUNT].sum()]

# ── 7 格式化 ──

df_out[VAR_COUNT] = df_out[VAR_COUNT].astype(int)

# ── 8 输出 ──

notes = [
    "根据筛选失败原因，拆分信息按例次计算。",
]

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表3 筛选失败原因分类.docx',
    '表3 筛选失败原因分类',
    notes,
    row_height_cm=0.6,
    auto_width=True,
)
