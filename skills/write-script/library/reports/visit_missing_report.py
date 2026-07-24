# ⚠ 模板文件——复制到 04 scripts/、改下方「项目配置」块后再运行
#
# @desc 访视缺失三线表：构建受试者×访视完整网格，与实际 SV 访视记录
#       left-join 后标记各访视「是/否/未激活」状态，筛选存在部分缺失的
#       受试者，透视输出宽表。
# @tags 访视缺失,缺失,visit,未激活,透视,DMR,三线表
# @config REPORT_NAME, FORM_SV/FORM_RAND/FORM_END, IMPORT_RAND_NO/IMPORT_COMPLETED,
#         VISIT_COLS, EXCLUDE_VISIT_OIDS

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
# 下列表单 OID、字段名均为项目特异，须据 query_metadata.py 实际探索结果替换。

REPORT_NAME = "访视缺失"

FORM_SV   = "SV"                            # 访视表单 OID（含访视名称、访视OID、访视日期）
FORM_RAND = "DS_RAND"                       # 随机表单 OID
FORM_END  = "DS_END"                        # 研究结束表单 OID

# SV 导入列名（业务字段；系统列由 system_cols() 自动解析）
IMPORT_RAND_NO = "随机号"
IMPORT_COMPLETED = "受试者是否完成试验_TXT"   # 是否完成试验（解码列；后缀随 EDC）
IMPORT_VISIT_NAME = "访视名称"
IMPORT_VISIT_OID  = "访视OID"
IMPORT_VISIT_DATE = "访视日期"
IMPORT_PAGE       = "页面名称"
IMPORT_STATUS     = "受试者状态"              # 受试者状态（用于排除筛选失败）

# 透视后的访视列（来自 SV.访视名称 的取值，按访视OID 顺序排列）
VISIT_COLS = [
    "筛选/基线期（D-15～D-1）",
    "治疗期（用药后第4周末±3天）",
    "治疗期（用药后第8周末±3天）",
    "提前退出访视",
]

# 排除的访视 OID（如计划外访视）
EXCLUDE_VISIT_OIDS = ["V90"]

# SV 中代表「访视日期」页面的页面名称
SV_DATE_PAGE = "访视日期"

# ── 列名集中管理 ──

VAR_VISIT_NAME  = IMPORT_VISIT_NAME
VAR_VISIT_OID   = IMPORT_VISIT_OID
VAR_PAGE        = IMPORT_PAGE
VAR_ASSESS_DATE = "评估日期"
VAR_DONE        = "是否进行"
VAR_RAND_NO     = IMPORT_RAND_NO
VAR_COMPLETED   = IMPORT_COMPLETED
VAR_STATUS      = IMPORT_STATUS

# 输出列名
VAR_SCREEN_NO = "筛选号"
VAR_COMPLETE  = "是否完成试验"

OUTPUT_COLS = [VAR_SCREEN_NO, VAR_RAND_NO, *VISIT_COLS, VAR_COMPLETE]

# ── 1 读取 ──

df_rand = load_sheet(FORM_RAND, usecols=[VAR_SUBJ, IMPORT_RAND_NO])
df_end  = load_sheet(FORM_END, usecols=[VAR_SUBJ, IMPORT_COMPLETED])
df_sv   = load_sheet(FORM_SV, usecols=[
    VAR_SUBJ, VAR_STATUS, VAR_VISIT_NAME, VAR_PAGE,
    VAR_VISIT_OID, VAR_VISIT_DATE,
])

# ── 2 归一化 + 交叉表 ──

# 完成状态：解码列去后缀，还原为输出名
df_end = df_end.rename(columns={VAR_COMPLETED: VAR_COMPLETE})

# 构建 受试者×访视 完整网格，确保未激活的访视也有行
df_cross = pd.MultiIndex.from_product(
    [df_sv[VAR_SUBJ].unique(), VISIT_COLS],
    names=[VAR_SUBJ, VAR_VISIT_NAME],
).to_frame(index=False)

# SV 只保留访视日期页 + 去重，每受试者×访视一行
df_sv_date = df_sv[df_sv[VAR_PAGE] == SV_DATE_PAGE].copy()
df_sv_date = df_sv_date.rename(columns={VAR_VISIT_DATE: VAR_ASSESS_DATE})
df_sv_date = df_sv_date.sort_values(
    by=[VAR_SUBJ, VAR_VISIT_NAME, VAR_ASSESS_DATE]
).drop_duplicates(subset=[VAR_SUBJ, VAR_VISIT_NAME])

# ── 3a 筛选（剔除无效记录）──

df_sv_date = df_sv_date[
    (df_sv_date[VAR_STATUS] != "筛选失败")
    & (~df_sv_date[VAR_VISIT_OID].isin(EXCLUDE_VISIT_OIDS))
]

# 交叉表合并实际访视数据（left → 保留未激活的访视行）
df_sv_out = df_cross.merge(
    df_sv_date[[VAR_SUBJ, VAR_VISIT_NAME, VAR_STATUS, VAR_VISIT_OID, VAR_ASSESS_DATE]],
    on=[VAR_SUBJ, VAR_VISIT_NAME],
    how="left",
)

# ── 5 派生 ──

# 是否进行：无访视记录=未激活，有记录但无日期=否，有日期=是
df_sv_out[VAR_DONE] = np.where(
    df_sv_out[VAR_ASSESS_DATE].notna(), "是",
    np.where(df_sv_out[VAR_VISIT_OID].notna(), "否", "未激活"),
)

# ── 6 连接 ──

df_out = (
    df_sv_out.merge(df_rand, on=VAR_SUBJ, how="left")
             .merge(df_end,  on=VAR_SUBJ, how="left")
)

# ── 3b 筛选（仅保留部分访视缺失的受试者）──

df_out = df_out.sort_values(by=[VAR_SUBJ, VAR_VISIT_OID])
df_out = df_out.groupby(VAR_SUBJ, group_keys=False).filter(
    lambda x: x[VAR_DONE].nunique() > 1
)

# ── 4 变形 ──

df_out = df_out.pivot(
    index=[VAR_SUBJ, VAR_RAND_NO, VAR_COMPLETE],
    columns=VAR_VISIT_NAME,
    values=VAR_DONE,
).reset_index()
df_out.columns.name = None
df_out = df_out.reindex(columns=[VAR_SUBJ, VAR_RAND_NO, VAR_COMPLETE, *VISIT_COLS])

# ── 7 格式化 ──

# 随机号为文本编码（含前导零），仅将缺失填为空串
df_out[VAR_RAND_NO] = df_out[VAR_RAND_NO].apply(
    lambda x: str(x) if pd.notna(x) and x != "" else ""
)
df_out = df_out.fillna("未激活")
df_out = df_out.rename(columns={VAR_SUBJ: VAR_SCREEN_NO})
df_out = df_out[OUTPUT_COLS].copy()
df_out.insert(0, "No.", range(1, len(df_out) + 1))

# ── 8 输出 ──

notes = [
    "访视列：「是」代表进行本次访视，「否」代表已激活但未进行本次访视，「未激活」代表该访视未激活",
]
save_table_to_docx_threeline(
    df_out,
    f"{output_table_dir}/{REPORT_NAME}.docx",
    REPORT_NAME,
    notes,
    row_height_cm=0.6,
    auto_width=True,
    include_notes=True,
)
