# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 不良事件总体分布情况三线表：从 AE 表单读取不良事件数据，
#       按维度（严重程度、治疗措施、与药物关系、转归等）分类汇总
#       例数与例次，含 CheckBox 多选列和 RadioButton 单选列处理。
# @tags 不良事件,AE,严重程度,治疗措施,转归,汇总,CheckBox,RadioButton,DMR,三线表
# @config REPORT_NAME, FORM_AE, IMPORT_AE_YN/IMPORT_AE_YN_YES,
#         CHECKBOX_COLS/RADIO_COLS, SCHEMA

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from config import output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")   # 受试者列

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID、字段名、解码值均为项目特异，须据 query_metadata.py 实际探索结果替换。

REPORT_NAME = "不良事件总体分布情况"

FORM_AE = "AE"          # 不良事件表单 OID

# AE 主表：是否发生 AE 字段及"是"的解码值
IMPORT_AE_YN     = "是否发生不良事件_TXT"   # 是否发生不良事件（解码列；后缀随 EDC）
IMPORT_AE_YN_YES = "是"

# CheckBox 多选列组（每列值为标记值 Y 时计为 1 例次）
# 格式：{ 分组名称: ([列名列表], 标记值) }
CHECKBOX_COLS = {
    "是否采取治疗措施": (["无", "药物治疗", "非药物治疗", "其他"], "Y"),
    "严重不良事件定义": (["死亡", "危及生命", "需住院治疗或延长住院时间",
                   "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
                   "其他重要的医学事件"], "Y"),
}

# RadioButton / DropDownList 单选列组
# 格式：[(EDC列名, 分组名称), ...]
RADIO_COLS = [
    ("初始严重程度（CTCAE 5.0）_TXT", "初始严重程度"),
    ("CTCAE分级是否有变化_TXT",       "严重程度是否有变化"),
    ("CTCAE分级-1_TXT",              "严重程度-1"),
    ("CTCAE分级-2_TXT",              "严重程度-2"),
    ("CTCAE分级-3_TXT",              "严重程度-3"),
    ("对试验药物采取的初始措施_TXT",    "对试验药物采取的措施"),
    ("与试验药物的关系_TXT",          "与试验药物的关系"),
    ("是否为严重不良事件_TXT",        "是否符合严重不良事件定义"),
    ("转归_TXT",                    "试验结束时，转归"),
]

# 输出 schema：各组所有可能的类别取值（用于补齐 0 值行）
# 格式：{ 分组名称: [类别列表] }
SCHEMA = {
    "全部不良事件":               [""],
    "初始严重程度":               ["1级", "2级", "3级", "4级", "5级"],
    "严重程度是否有变化":          ["是", "否"],
    "严重程度-1":                ["1级", "2级", "3级", "4级", "5级"],
    "严重程度-2":                ["1级", "2级", "3级", "4级", "5级"],
    "严重程度-3":                ["1级", "2级", "3级", "4级", "5级"],
    "是否采取治疗措施":            ["无", "药物治疗", "非药物治疗", "其他"],
    "对试验药物采取的措施":        ["剂量不变", "增加剂量", "减少剂量", "暂停用药",
                              "停止用药", "已结束用药", "不适用"],
    "与试验药物的关系":            ["肯定有关", "很可能有关", "可能有关", "可能无关", "无关"],
    "是否符合严重不良事件定义":     ["是", "否"],
    "严重不良事件定义":            ["死亡", "危及生命", "需住院治疗或延长住院时间",
                              "导致永久的或严重的残疾/能力丧失", "先天性异常或出生缺陷",
                              "其他重要的医学事件"],
    "试验结束时，转归":            ["痊愈", "痊愈伴后遗症", "好转/缓解", "未好转/持续",
                              "致死", "未知"],
}

# ── 列名集中管理 ──

VAR_KEY = "记录号"

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
    """RadioButton/DropDownList 单选列汇总：按值分组统计例数/例次。"""
    res = df.groupby(col, dropna=False).agg(
        例数=(key, "nunique"),
        例次=(key, "size"),
    ).reset_index()
    res.rename(columns={col: "类别"}, inplace=True)
    res.insert(0, "项目", cat)
    return res


# ── 1 读取 ──

# CheckBox 列
checkbox_parts = []
for cat_name, (cols, mark) in CHECKBOX_COLS.items():
    df_cb = load_sheet(FORM_AE, usecols=[VAR_SUBJ, VAR_KEY, IMPORT_AE_YN] + cols)
    df_cb = df_cb[df_cb[IMPORT_AE_YN] == IMPORT_AE_YN_YES]
    checkbox_parts.append(_checkbox_summary(df_cb, cols, VAR_SUBJ, mark, cat_name))

# 单选列
radio_col_names = [c[0] for c in RADIO_COLS]
df_radio = load_sheet(FORM_AE, usecols=[VAR_SUBJ, VAR_KEY, IMPORT_AE_YN] + radio_col_names)
df_radio = df_radio[df_radio[IMPORT_AE_YN] == IMPORT_AE_YN_YES]

radio_parts = []
for raw_col, cat_name in RADIO_COLS:
    radio_parts.append(_radio_summary(df_radio, raw_col, VAR_SUBJ, cat_name))

# ── 5 派生：全部不良事件汇总行 ──

n_subj = df_radio[VAR_SUBJ].nunique()
n_records = len(df_radio)
row_total = pd.DataFrame({
    "项目": ["全部不良事件"],
    "类别": [""],
    "例数": [n_subj],
    "例次": [n_records],
})

# ── 6 连接 ──

df_all = pd.concat(checkbox_parts + radio_parts + [row_total], ignore_index=True)

# ── 7 格式化：补齐 schema 缺失类别，填 0 ──

frame_rows = []
for project, categories in SCHEMA.items():
    for cat in categories:
        frame_rows.append({"项目": project, "类别": cat})
df_frame = pd.DataFrame(frame_rows)

df_out = pd.merge(df_frame, df_all, on=["项目", "类别"], how="left")
df_out["例数"] = df_out["例数"].fillna(0).astype(int)
df_out["例次"] = df_out["例次"].fillna(0).astype(int)

# ── 8 输出 ──

notes = [
    "受试者不良事件情况以实际发生计例次和例数，不做任何规则处理；",
    "不良事件详细清单见附件「不良事件清单」。",
]
save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
    merge_columns=["项目"],
)
