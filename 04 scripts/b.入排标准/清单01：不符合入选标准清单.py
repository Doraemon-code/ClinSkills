import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_rand, load_sheet, load_completion

# ── 列名集中管理 ──

# 导入列名
IMPORT_RAND = ['受试者', '随机号']
IMPORT_IE   = ['受试者', '不符合入选标准/符合排除标准类型_TXT',
               '入选标准编号_TXT', '排除标准编号_TXT']

# 中文列名常量
VAR_SUBJ         = "受试者"
VAR_TYPE         = "不符合入选标准/符合排除标准类型_TXT"
VAR_INC_NO       = "入选标准编号_TXT"
VAR_EXC_NO       = "排除标准编号_TXT"
VAR_CRITERIA_NO  = "标准编号"

# 输出列名
VAR_SCREEN_NO    = "筛选号"
VAR_RAND_NO      = "随机号"
VAR_COMPLETED    = "是否完成试验"
OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_COMPLETED, VAR_CRITERIA_NO]

# ── 1 读取 ──

df_ie   = load_sheet("IE", IMPORT_IE).fillna("")
df_rand = load_rand(cols=IMPORT_RAND)
df_end  = load_completion()

# ── 3 筛选 ──

df_ie = df_ie[df_ie[VAR_TYPE] == "入选标准"]
df_ie = df_ie[df_ie[VAR_INC_NO] != ""]

# ── 7 格式化 ──

df_ie[VAR_CRITERIA_NO] = df_ie[VAR_INC_NO]

# ── 6 连接 ──

df_out = (df_ie.merge(df_rand, on=[VAR_SUBJ], how="left")
               .merge(df_end,  on=[VAR_SUBJ], how="left")
        )

df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})
df_out = df_out[OUTPUT_COLS]
df_out = df_out.fillna("")

n = len(df_out)
df_out.insert(0, "No.", range(1, n + 1))

# ── 8 输出 ──

save_table_to_docx_threeline(
    df_out,
    f'{output_path}/table/表15 不符合入选标准清单.docx',
    f'表15 不符合入选标准清单（{n}例）',
    row_height_cm=0.6,
    auto_width=True,
)
