import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_path
from utils.loaders import load_sheet
from utils.output_format import save_table_to_docx_threeline

# ── 列名集中管理 ──

IMPORT_BASE   = ["受试者", "记录号"]
VAR_SUBJ      = "受试者"
VAR_KEY       = "记录号"
VAR_AEYN      = "是否发生不良事件_TXT"

# ── 辅助函数 ──

def _checkbox_summary(df, cols, key, mark, cat):
    """CheckBox 多选列汇总：每列统计 mark 值的例数/例次。"""
    rows = []
    for col in cols:
        subset = df[df[col] == mark]
        rows.append({
            "项目": cat,
            "类别": col,
            "例数": subset[key].nunique(),
            "例次": len(subset),
        })
    return pd.DataFrame(rows)


def _radio_summary(df, col, key, cat):
    """RadioButton/ DropDownList 单选列汇总：按值分组统计例数/例次。"""
    res = df.groupby(col, dropna=False).agg(
        例数=(key, "nunique"),
        例次=(key, "size"),
    ).reset_index()
    res.rename(columns={col: "类别"}, inplace=True)
    res.insert(0, "项目", cat)
    return res


# ── 1 读取 ──

# CheckBox 列（多选，值为 "Y"）
IMPORT_CHECKBOX_TRT = IMPORT_BASE + [VAR_AEYN, "无", "药物治疗", "非药物治疗", "其他"]
IMPORT_CHECKBOX_SAE = IMPORT_BASE + [VAR_AEYN,
    "死亡", "危及生命", "需住院治疗或延长住院时间",
    "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
    "其他重要的医学事件",
]

# RadioButton/ DropDownList 列（单选，解码列）
IMPORT_RADIO = IMPORT_BASE + [
    "是否发生不良事件_TXT",
    "初始严重程度（CTCAE 5.0）_TXT",
    "CTCAE分级是否有变化_TXT",
    "CTCAE分级-1_TXT", "CTCAE分级-2_TXT", "CTCAE分级-3_TXT",
    "对试验药物采取的初始措施_TXT",
    "与试验药物的关系_TXT",
    "是否为严重不良事件_TXT",
    "转归_TXT",
]

# ── 3 筛选 & 4 变形 ──

# 治疗措施（CheckBox）
df_cb_trt = load_sheet("AE", cols=IMPORT_CHECKBOX_TRT)
df_cb_trt = df_cb_trt[df_cb_trt[VAR_AEYN] == "是"]
res_trt = _checkbox_summary(
    df_cb_trt,
    ["无", "药物治疗", "非药物治疗", "其他"],
    VAR_SUBJ, "Y", "是否采取治疗措施",
)

# 严重不良事件定义（CheckBox）
df_cb_sae = load_sheet("AE", cols=IMPORT_CHECKBOX_SAE)
df_cb_sae = df_cb_sae[df_cb_sae[VAR_AEYN] == "是"]
res_sae = _checkbox_summary(
    df_cb_sae,
    ["死亡", "危及生命", "需住院治疗或延长住院时间",
     "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
     "其他重要的医学事件"],
    VAR_SUBJ, "Y", "严重不良事件定义",
)

# 单选列汇总
df_radio = load_sheet("AE", cols=IMPORT_RADIO)
df_radio = df_radio[df_radio[VAR_AEYN] == "是"]

RADIO_COLS = [
    ("初始严重程度（CTCAE 5.0）_TXT", "初始严重程度"),
    ("CTCAE分级是否有变化_TXT",     "严重程度是否有变化"),
    ("CTCAE分级-1_TXT",            "严重程度-1"),
    ("CTCAE分级-2_TXT",            "严重程度-2"),
    ("CTCAE分级-3_TXT",            "严重程度-3"),
    ("对试验药物采取的初始措施_TXT",   "对试验药物采取的措施"),
    ("与试验药物的关系_TXT",         "与试验药物的关系"),
    ("是否为严重不良事件_TXT",       "是否符合严重不良事件定义"),
    ("转归_TXT",                  "试验结束时，转归"),
]

res_radio_parts = []
for raw_col, cat_name in RADIO_COLS:
    res_radio_parts.append(_radio_summary(df_radio, raw_col, VAR_SUBJ, cat_name))
res_radio = pd.concat(res_radio_parts, ignore_index=True)

# 全部不良事件汇总行
n_subj = df_radio[VAR_SUBJ].nunique()
n_records = len(df_radio)
row_total = pd.DataFrame({
    "项目": ["全部不良事件"],
    "类别": [""],
    "例数": [n_subj],
    "例次": [n_records],
})

# ── 6 连接 ──

df_all = pd.concat([res_trt, res_sae, res_radio, row_total], ignore_index=True)

# ── 7 格式化：补齐 schema 缺失类别，填 0 ──

schema = {
    "全部不良事件":               [""],
    "初始严重程度":              ["1级", "2级", "3级", "4级", "5级"],
    "严重程度是否有变化":          ["是", "否"],
    "严重程度-1":               ["1级", "2级", "3级", "4级", "5级"],
    "严重程度-2":               ["1级", "2级", "3级", "4级", "5级"],
    "严重程度-3":               ["1级", "2级", "3级", "4级", "5级"],
    "是否采取治疗措施":           ["无", "药物治疗", "非药物治疗", "其他"],
    "对试验药物采取的措施":        ["剂量不变", "增加剂量", "减少剂量", "暂停用药",
                               "停止用药", "已结束用药", "不适用"],
    "与试验药物的关系":           ["肯定有关", "很可能有关", "可能有关", "可能无关", "无关"],
    "是否符合严重不良事件定义":     ["是", "否"],
    "严重不良事件定义":           ["死亡", "危及生命", "需住院治疗或延长住院时间",
                               "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
                               "其他重要的医学事件"],
    "试验结束时，转归":           ["痊愈", "痊愈伴后遗症", "好转/缓解", "未好转/持续",
                               "致死", "未知"],
}

frame_rows = []
for project, categories in schema.items():
    for cat in categories:
        frame_rows.append({"项目": project, "类别": cat})
df_frame = pd.DataFrame(frame_rows)

df_out = pd.merge(df_frame, df_all, on=["项目", "类别"], how="left")
df_out["例数"] = df_out["例数"].fillna(0).astype(int)
df_out["例次"] = df_out["例次"].fillna(0).astype(int)

# ── 8 输出 ──

notes = [
    "受试者不良事件情况以实际发生计例次和例数，不做任何规则处理；",
    '不良事件详细清单见附件"不良事件清单"。',
]
save_table_to_docx_threeline(
    df_out,
    f"{output_path}/table/表28 不良事件总体分布情况.docx",
    "表28 不良事件总体分布情况",
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
    merge_columns=["项目"],
)

print(f"已保存：{output_path}/table/表28 不良事件总体分布情况.docx")
