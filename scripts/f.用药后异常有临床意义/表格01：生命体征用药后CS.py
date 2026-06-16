import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_path
from utils.loaders import load_sheet, load_rand, load_first_dose, load_completion
from utils.output_format import export_to_excel_twoheader

# ── 列名集中管理 ──

# 中间列名
VAR_SUBJ        = "受试者"
VAR_STATUS      = "受试者状态"
VAR_VISIT       = "访视名称"
VAR_PAGE        = "页面名称"
VAR_ASSESS_DATE = "检查日期"
VAR_ITEM        = "检查项"
VAR_RESULT      = "结果"
VAR_CS          = "临床意义"
VAR_UNIT        = "单位"
VAR_FIRST_DOSE  = "服药日期"
VAR_GROUP       = "分组"
VAR_AE          = "不良事件名称"
VAR_MH          = "病史名称"
VAR_OTHER       = "其他请说明"

# 输出列名
VAR_SCREEN_NO   = "筛选号"
VAR_RAND_NO     = "随机号"
VAR_FORM        = "表单名称"
VAR_VISIT_PRE   = "访视名称_首次用药前"
VAR_VISIT_POST  = "访视名称_首次用药后"
VAR_DATE_PRE    = "检查日期_首次用药前"
VAR_DATE_POST   = "检查日期_首次用药后"
VAR_RESULT_PRE  = "检查结果_首次用药前"
VAR_RESULT_POST = "检查结果_首次用药后"
VAR_CS_PRE      = "临床意义_首次用药前"
VAR_CS_POST     = "临床意义_首次用药后"
VAR_CS_DESC     = "异常有临床意义，请描述_首次用药后"
VAR_COMPLETED   = "是否完成试验"

OUTPUT_COLS = [
    VAR_SCREEN_NO, VAR_RAND_NO, VAR_FORM, VAR_ITEM, VAR_UNIT,
    VAR_VISIT_PRE, VAR_DATE_PRE, VAR_RESULT_PRE, VAR_CS_PRE,
    VAR_VISIT_POST, VAR_DATE_POST, VAR_RESULT_POST, VAR_CS_POST,
    VAR_CS_DESC, VAR_COMPLETED,
]

# ── 辅助：VS 宽表 → 长表 ──

def _melt_vs(df_raw):
    """将 VS 宽表（每种生命体征一列）melt 为长表。"""
    # 重命名重复列（.1/.2/.3 后缀 → 语义后缀）
    rename_map = {}
    suffixes = [("体温", ""), ("心率", "_HR"), ("呼吸", "_RESP"), ("血压", "_BP")]
    for field in ["异常，请描述", "不良事件名称", "病史名称", "其他,请说明"]:
        for _, sfx in suffixes[1:]:  # 第一组保持原名
            rename_map[f"{field}{sfx.replace('_', '.')}" if sfx else field] = f"{field}{sfx}"
    # 其实直接用原始 .1/.2/.3 后缀更准确
    rename_map = {
        "异常，请描述.1": "异常，请描述_HR",
        "不良事件名称.1": "不良事件名称_HR",
        "病史名称.1":     "病史名称_HR",
        "其他,请说明.1":  "其他,请说明_HR",
        "异常，请描述.2": "异常，请描述_RESP",
        "不良事件名称.2": "不良事件名称_RESP",
        "病史名称.2":     "病史名称_RESP",
        "其他,请说明.2":  "其他,请说明_RESP",
        "异常，请描述.3": "异常，请描述_BP",
        "不良事件名称.3": "不良事件名称_BP",
        "病史名称.3":     "病史名称_BP",
        "其他,请说明.3":  "其他,请说明_BP",
    }
    df_raw = df_raw.rename(columns=rename_map)

    # 通用 ID 列（每个 VS 行共享）
    id_cols = [VAR_SUBJ, VAR_STATUS, VAR_VISIT, VAR_PAGE, VAR_ASSESS_DATE]

    # 四种生命体征 → (VS_ITEM 名, 结果列, 单位列, 临床评估列, 描述列, AE列, MH列, 其他列)
    groups = [
        ("体温",         "体温",           "体温_UNIT",         "体温-临床评估_TXT",         "异常，请描述",      "不良事件名称",     "病史名称",     "其他,请说明"),
        ("心率",         "HR",             "HR_UNIT",           "心率-临床评估_TXT",         "异常，请描述_HR",   "不良事件名称_HR",  "病史名称_HR",  "其他,请说明_HR"),
        ("呼吸",         "呼吸",           "呼吸_UNIT",         "呼吸-临床评估_TXT",         "异常，请描述_RESP", "不良事件名称_RESP","病史名称_RESP", "其他,请说明_RESP"),
        ("收缩压/舒张压", "收缩压",        "收缩压_UNIT",       "收缩压/舒张压-临床评估_TXT", "异常，请描述_BP",   "不良事件名称_BP",  "病史名称_BP",  "其他,请说明_BP"),
    ]

    parts = []
    for item_name, val_col, unit_col, cs_col, desc_col, ae_col, mh_col, other_col in groups:
        part = df_raw[id_cols].copy()
        part[VAR_ITEM]   = item_name
        part[VAR_RESULT] = df_raw[val_col]
        part[VAR_UNIT]   = df_raw[unit_col]
        part[VAR_CS]     = df_raw[cs_col]
        part[VAR_AE]     = df_raw[ae_col]
        part[VAR_MH]     = df_raw[mh_col]
        part[VAR_OTHER]  = df_raw[other_col]
        parts.append(part)

    df_long = pd.concat(parts, ignore_index=True)
    df_long = df_long[df_long[VAR_RESULT].notna() & (df_long[VAR_RESULT].astype(str).str.strip() != "")]
    return df_long


# ── 1 读取 ──
# VS 宽表有重复列名（异常，请描述 / 不良事件名称 等各出现 4 次），
# load_sheet 的 usecols 无法处理重复列，故直接读全量再 melt。
df_vs_raw     = load_sheet("VS", cols=None)
df_first_dose = load_first_dose().rename(columns={"首次用药日期": VAR_FIRST_DOSE})
df_completion = load_completion()
df_rand       = load_rand(cols=["受试者", "随机号"])

# ── 2 归一化：宽表 → 长表 ──
df_vs = _melt_vs(df_vs_raw)
df_vs[VAR_ASSESS_DATE] = pd.to_datetime(df_vs[VAR_ASSESS_DATE], errors="coerce")

# ── 3 筛选：排除筛选失败 + 有临床评估的记录 ──
df_all = df_vs[
    (df_vs[VAR_STATUS] != "筛选失败") & df_vs[VAR_CS].notna()
].copy()

# ── 6 连接：合并首次用药、完成状态、随机号 ──
df_all = (
    df_all.merge(df_first_dose, on=[VAR_SUBJ], how="left")
          .merge(df_completion, on=[VAR_SUBJ], how="left")
          .merge(df_rand,       on=[VAR_SUBJ], how="left")
)

# ── 5 派生：给药前/后分组 ──
df_all[VAR_GROUP] = np.where(
    df_all[VAR_ASSESS_DATE] <= df_all[VAR_FIRST_DOSE],
    "给药前检查", "给药后检查",
)

# ── 3 筛选：给药前 — 基线期/筛选期取行 ──
df_pre = df_all[df_all[VAR_GROUP] == "给药前检查"]
df_pre = df_pre.sort_values(by=[VAR_SUBJ, VAR_PAGE, VAR_ITEM, VAR_FIRST_DOSE])

GROUP_COLS = [VAR_SUBJ, VAR_PAGE, VAR_ITEM]

def _pick_pre_rows(g):
    """基线期 CS 则整体排除；否则保留基线期行。"""
    if (g[VAR_CS] == "异常有临床意义").any():
        return g.iloc[0:0]
    return g

# group_keys=False 时 pandas 会从 apply 的输入中移除 groupby 列，
# 需要在 apply 后通过原始索引恢复。
df_pre_group_cols = df_pre[GROUP_COLS].copy()
df_pre = (
    df_pre.groupby(GROUP_COLS, group_keys=False)
          .apply(_pick_pre_rows)
)
df_pre = df_pre.join(df_pre_group_cols).reset_index(drop=True)

# ── 5 派生：给药后 — 异常有临床意义描述文本 ──
prefix_map = {VAR_MH: "MH:", VAR_AE: "AE:", "帕金森病_TXT": "研究疾病:", VAR_OTHER: "其他:"}

df_post = df_all[
    (df_all[VAR_GROUP] == "给药后检查") & (df_all[VAR_CS] == "异常有临床意义")
].copy()

desc_cols = [VAR_MH, VAR_AE, VAR_OTHER]
df_post[VAR_CS_DESC] = df_post[desc_cols].apply(
    lambda row: ";".join(
        f"{prefix_map.get(col, col)}{str(val).replace('√', '帕金森病')}"
        for col, val in row.items()
        if pd.notna(val) and str(val).strip() != ""
    ),
    axis=1,
)

df_post = df_post[[VAR_SUBJ, VAR_VISIT, VAR_PAGE, VAR_ASSESS_DATE,
                    VAR_ITEM, VAR_RESULT, VAR_CS, VAR_CS_DESC]]

# ── 6 连接：用药前 + 用药后 ──
df_merge = df_pre.merge(df_post, on=[VAR_SUBJ, VAR_PAGE, VAR_ITEM], how="left")
df_merge = df_merge[~(df_merge[f"{VAR_RESULT}_x"].isna() | df_merge[f"{VAR_RESULT}_y"].isna())]

# ── 7 格式化 ──
df_merge = df_merge.rename(columns={
    f"{VAR_VISIT}_x":       VAR_VISIT_PRE,
    f"{VAR_VISIT}_y":       VAR_VISIT_POST,
    f"{VAR_RESULT}_x":      VAR_RESULT_PRE,
    f"{VAR_RESULT}_y":      VAR_RESULT_POST,
    f"{VAR_ASSESS_DATE}_x": VAR_DATE_PRE,
    f"{VAR_ASSESS_DATE}_y": VAR_DATE_POST,
    f"{VAR_CS}_x":          VAR_CS_PRE,
    f"{VAR_CS}_y":          VAR_CS_POST,
    f"{VAR_UNIT}_x":        VAR_UNIT,
    "其他请说明_x":         VAR_OTHER,
    VAR_PAGE:               VAR_FORM,
    VAR_ITEM:               VAR_ITEM,
    VAR_SUBJ:               VAR_SCREEN_NO,
    "是否完成试验_TXT":     VAR_COMPLETED,
})

df_merge[VAR_DATE_PRE]  = df_merge[VAR_DATE_PRE].dt.strftime("%Y-%m-%d")
df_merge[VAR_DATE_POST] = df_merge[VAR_DATE_POST].dt.strftime("%Y-%m-%d")

df_merge = df_merge[OUTPUT_COLS]
df_merge.insert(0, "No.", range(1, len(df_merge) + 1))

# ── 8 输出 ──
file_name = f"{output_path}/listing/表39-2 生命体征用药后检查异常有临床意义清单.xlsx"
export_to_excel_twoheader(
    df_merge, file_name, "表39-2 用药后检查异常有临床意义清单",
    title="表 39-2 用药后检查异常有临床意义清单",
    fixed_cols=['No.', '筛选号', '随机号', '表单名称', '检查项', '单位'],
    header_groups=[
        {'label': '首次用药前', 'children': ['访视名称', '检查日期', '检查结果', '临床意义']},
        {'label': '首次用药后', 'children': ['访视名称', '检查日期', '检查结果', '临床意义', '异常有临床意义，请描述']},
    ],
    trailing_cols=['是否完成试验'],
    col_widths=[(0, 0, 5), (1, 2, 8), (3, 4, 12), (5, 5, 5), (6, 13, 18), (14, 14, 30), (15, 15, 14)],
    subject_col='筛选号',
)
