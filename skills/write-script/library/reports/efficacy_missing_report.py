# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 疗效性评价指标缺失三线表：逐表单检查疗效评价指标（gate="是" 但
#       结果列为空，或 gate="否" 整表缺失），melt 为长表后输出缺失清单。
# @tags 疗效,缺失,gate,表单缺失,melt,DMR,三线表
# @config REPORT_NAME, EFFICACY_FORMS, FORM_RAND/FORM_END,
#         IMPORT_RAND_NO/IMPORT_COMPLETED

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np
from config import output_table_dir
from utils.output_format import save_table_to_docx_threeline
from utils.loaders import load_sheet, system_cols

# ── 系统列（勿硬编码）──

VAR_SUBJ = system_cols("subject")    # 受试者列

# ── 项目配置（按本项目元数据调整；仅业务字段）──
# 下列表单 OID、字段名、gate 值与结果列为项目特异。

REPORT_NAME = "疗效性评价指标缺失"

FORM_RAND = "DS_RAND"
FORM_END  = "DS_END"

IMPORT_RAND_NO  = "随机号"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"   # 解码列；后缀随 EDC

# 疗效评价表单定义：{ sheet_oid: { "gate": gate列, "results": [结果列列表] } }
# gate="是" 但结果列为 NaN → 缺失项
# gate="否" → 整个表单缺失
EFFICACY_FORMS = {
    "QS_TCM": {
        "gate":     "是否进行中医证候评估_TXT",
        "results": [
            "腰背疼痛_TXT", "腰背活动受限_TXT", "晨僵_TXT",
            "疼痛夜重_TXT", "刺痛_TXT", "局部冷痛_TXT",
            "畏寒喜暖_TXT", "足跟痛_TXT", "腰膝酸软_TXT",
            "症状积分",
            "舌紫暗", "舌淡", "有瘀斑", "苔白",
            "沉细", "涩",
            "是否诊断为肾阳亏虚、瘀血痹阻证_TXT",
        ],
    },
    "QS_SPI": {
        "gate":     "受试者是否对过去一周的脊柱疼痛情况进行评估_TXT",
        "results":  ["评分", "脊柱疼痛", "过去一周的夜间背痛与过去一周的总体背痛情况_TXT"],
    },
    "QS_DAI": {
        "gate":     "受试者是否对过去一周症状进行BASDAI评估_TXT",
        "results":  ["评分", "巴斯强直性脊柱炎疾病活动性指数(BASDAI)",
                     "在过去的一星期，巴斯强直性脊柱炎疾病活动性指数（BASDAI）_TXT"],
    },
    "QS_SFI": {
        "gate":     "受试者是否对过去一周症状进行BASFI评估_TXT",
        "results":  ["评分", "巴斯强直性脊柱炎躯体功能性指数（BASFI）",
                     "巴斯强直性脊柱炎躯体功能性指数（BASFI）_TXT"],
    },
    "RS": {
        "gate":     "受试者是否对过去一周整体的疾病活动进行评估_TXT",
        "results":  ["上一周当中您对您的疾病的总体评价"],
    },
}

# ── 列名集中管理 ──

IMPORT_SYSTEM = [VAR_SUBJ, "受试者状态", "访视名称", "页面名称"]

VAR_STATUS = "受试者状态"
VAR_VISIT  = "访视名称"
VAR_FORM   = "页面名称"
VAR_ITEM   = "缺失项"
VAR_GATE   = "是否评估"
VAR_RESULT = "结果"

VAR_SCREEN_NO = "筛选号"
VAR_RAND_NO   = "随机号"
VAR_FORM_NAME = "表单名称"
VAR_COMPLETED = "是否完成试验"

OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, VAR_VISIT, VAR_FORM_NAME, VAR_ITEM, VAR_COMPLETED]

# ── 1 读取 ──

missing_parts = []

for sheet, cfg in EFFICACY_FORMS.items():
    gate_col = cfg["gate"]
    result_cols = cfg["results"]

    cols_to_load = IMPORT_SYSTEM + [gate_col] + result_cols
    cols_to_load = list(dict.fromkeys(cols_to_load))  # 去重

    df_f = load_sheet(sheet, usecols=cols_to_load)
    df_f = df_f.rename(columns={gate_col: VAR_GATE})

    # ── 情况A：gate="是" 但结果缺失 ──
    df_done = df_f[df_f[VAR_GATE] == "是"].copy()
    if len(df_done) > 0:
        df_melt = df_done.melt(
            id_vars=IMPORT_SYSTEM + [VAR_GATE],
            value_vars=result_cols,
            var_name=VAR_ITEM,
            value_name=VAR_RESULT,
        )
        df_missing_done = df_melt[df_melt[VAR_RESULT].isna()]
        df_missing_done = df_missing_done[IMPORT_SYSTEM + [VAR_ITEM]]
        missing_parts.append(df_missing_done)

    # ── 情况B：gate="否" → 整个表单缺失 ──
    df_skip = df_f[df_f[VAR_GATE] == "否"].copy()
    if len(df_skip) > 0:
        df_skip[VAR_ITEM] = df_skip[VAR_FORM]
        df_skip = df_skip[IMPORT_SYSTEM + [VAR_ITEM]].drop_duplicates()
        missing_parts.append(df_skip)

# ── 2 归一化 ──

if not missing_parts:
    print("无缺失数据")
    exit()

df_missing = pd.concat(missing_parts, ignore_index=True)

# ── 3 筛选 ──

df_missing = df_missing[df_missing[VAR_STATUS] != "筛选失败"]

# ── 6 连接：随机号 + 完成状态 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_RAND_NO])

df_end = load_sheet(FORM_END, usecols=[VAR_SUBJ, IMPORT_COMPLETED])
df_end = df_end.rename(columns={IMPORT_COMPLETED: VAR_COMPLETED})

df_out = (
    df_missing.merge(df_rand, on=VAR_SUBJ, how="left")
              .merge(df_end, on=VAR_SUBJ, how="left")
)

# ── 7 格式化 ──

df_out[VAR_RAND_NO] = df_out[VAR_RAND_NO].apply(
    lambda x: str(x) if pd.notna(x) and x != "" else ""
)

_RENAME_MAP = {
    VAR_SUBJ: VAR_SCREEN_NO,
    VAR_FORM: VAR_FORM_NAME,
}
df_out = df_out.rename(columns=_RENAME_MAP)
df_out = df_out[OUTPUT_COLS].fillna("")
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

notes = [
    "确认受试者访视缺失，该访视相关检查缺失不在此处重复罗列；",
    "整个表单缺失时，缺失项为表单名称。",
]

save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=False,
)
