import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.loaders import load_rand, load_sheet, load_completion
from utils.output_format import export_to_excel_with_format

# ── 列名集中管理 ──

# 导入列名（load_sheet / load_rand 的 usecols）
IMPORT_RAND = ["受试者", "随机号"]

# AE 单值 / 解码列（含 _TXT 后缀，与当前 EDC 导出列名一致）
IMPORT_AE_SINGLE = [
    "受试者",
    "不良事件名称",
    "开始日期",
    "转归日期",
    "转归_TXT",
    "初始严重程度（CTCAE 5.0）_TXT",
    "CTCAE分级是否有变化_TXT",
    "CTCAE分级变化日期-1", "CTCAE分级-1_TXT",
    "CTCAE分级变化日期-2", "CTCAE分级-2_TXT",
    "CTCAE分级变化日期-3", "CTCAE分级-3_TXT",
    "对试验药物采取的初始措施_TXT",
    "与试验药物的关系_TXT",
    "是否为严重不良事件_TXT",
    "SAE发生日期",
    "PT术语",
    "SOC术语",
]

# AE CheckBox 多选列（值 "1"=勾选，"0"=未选）
IMPORT_AE_TRT    = ["无", "药物治疗", "非药物治疗"]        # → 是否采取治疗措施
IMPORT_AE_OTHER  = ["其他措施"]                            # 其他治疗措施自由文本
IMPORT_AE_SAEDEF = ["死亡", "危及生命", "需住院治疗或延长住院时间",
                    "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
                    "其他重要的医学事件"]                   # → 严重不良事件定义

IMPORT_AE = IMPORT_AE_SINGLE + IMPORT_AE_TRT + IMPORT_AE_OTHER + IMPORT_AE_SAEDEF

# 中间列名
VAR_SUBJ        = "受试者"
VAR_AE_NAME     = "不良事件名称"
VAR_OTHER_TRT   = "其他措施"
VAR_CHECKED     = "1"                       # CheckBox 勾选值
VAR_TRT_SUMMARY = "是否采取治疗措施"          # 派生列
VAR_SAE_DEF     = "严重不良事件定义"          # 派生列
VAR_RELATION    = "与试验药物的关系"          # rename 后用于筛选

# 输出列名映射（当前 EDC 列名 → 报表列标题，去 _TXT 后缀）
_RENAME_MAP = {
    "受试者":                       "筛选号",
    "开始日期":                     "发生日期",
    "转归_TXT":                     "试验结束时，转归",
    "初始严重程度（CTCAE 5.0）_TXT":  "初始严重程度",
    "CTCAE分级是否有变化_TXT":       "严重程度是否有变化",
    "CTCAE分级变化日期-1":           "严重程度变化日期-1",
    "CTCAE分级-1_TXT":             "严重程度-1",
    "CTCAE分级变化日期-2":           "严重程度变化日期-2",
    "CTCAE分级-2_TXT":             "严重程度-2",
    "CTCAE分级变化日期-3":           "严重程度变化日期-3",
    "CTCAE分级-3_TXT":             "严重程度-3",
    "对试验药物采取的初始措施_TXT":    "对试验药物采取的措施",
    "与试验药物的关系_TXT":          "与试验药物的关系",
    "是否为严重不良事件_TXT":        "是否符合严重不良事件定义",
    "SAE发生日期":                  "严重不良事件开始日期",
    "PT术语":                       "PT",
    "SOC术语":                      "SOC",
}

# 输出列序（与原报表一致；当前 EDC 已无"是否因此不良事件退出试验""是否为特别关注不良事件"，按确认删除）
OUTPUT_COLS = [
    "筛选号", "随机号", "不良事件名称", "SOC", "PT",
    "发生日期", "转归日期", "试验结束时，转归",
    "初始严重程度", "严重程度是否有变化",
    "严重程度变化日期-1", "严重程度-1",
    "严重程度变化日期-2", "严重程度-2",
    "严重程度变化日期-3", "严重程度-3",
    "是否采取治疗措施", "对试验药物采取的措施",
    VAR_RELATION, "是否符合严重不良事件定义", "严重不良事件定义",
    "严重不良事件开始日期", "是否完成试验",
]

# 与试验药物有关的关系判定
RELATED_VALUES = ["肯定有关", "很可能有关", "可能有关"]

# ── 1 读取 ──

df_rand = load_rand(cols=IMPORT_RAND)
df_end  = load_completion()
df_ae   = load_sheet("AE", cols=IMPORT_AE)

# ── 3 筛选：仅保留有不良事件名称的记录 ──

df_ae = df_ae[df_ae[VAR_AE_NAME].notna()].copy()

# ── 5 派生：其他文本前缀、CheckBox 勾选转标签、多选拼接 ──

# 其他治疗措施自由文本加 "其他:" 前缀
m_other = df_ae[VAR_OTHER_TRT].notna() & df_ae[VAR_OTHER_TRT].astype(str).str.strip().ne("")
df_ae.loc[m_other, VAR_OTHER_TRT] = "其他:" + df_ae.loc[m_other, VAR_OTHER_TRT].astype(str)

# CheckBox：勾选（"1"）转为列名标签，未勾选（"0"/空）置空
for col in IMPORT_AE_TRT + IMPORT_AE_SAEDEF:
    df_ae[col] = df_ae[col].map({VAR_CHECKED: col})

# 拼接治疗措施（含其他文本）与严重不良事件定义
df_ae[VAR_TRT_SUMMARY] = df_ae[IMPORT_AE_TRT + IMPORT_AE_OTHER].apply(
    lambda row: ";".join(row.dropna()), axis=1)
df_ae[VAR_SAE_DEF] = df_ae[IMPORT_AE_SAEDEF].apply(
    lambda row: ";".join(row.dropna()), axis=1)
df_ae = df_ae.drop(columns=IMPORT_AE_TRT + IMPORT_AE_OTHER + IMPORT_AE_SAEDEF)

# ── 6 连接 ──

df_ae = (df_ae.merge(df_rand, on=VAR_SUBJ, how="left")
              .merge(df_end,  on=VAR_SUBJ, how="left"))

# ── 7 格式化：重命名、选列 ──

df_ae = df_ae.rename(columns=_RENAME_MAP)
df_out = df_ae[OUTPUT_COLS].copy()

# ── 3 筛选：与试验药物有关 ──

df_related = df_out[df_out[VAR_RELATION].isin(RELATED_VALUES)].copy()

# ── 7 格式化：连续序号 ──

df_related.insert(0, "No.", range(1, len(df_related) + 1))

# ── 8 输出 ──

n_records = len(df_related)
n_subj = df_related["筛选号"].nunique()
export_to_excel_with_format(
    df_related,
    f"{output_path}/listing/表40 与试验药物有关的不良事件清单.xlsx",
    "表40 与试验药物有关的不良事件清单",
    f"表40 与试验药物有关的不良事件清单（{n_records}例次{n_subj}例）",
)
