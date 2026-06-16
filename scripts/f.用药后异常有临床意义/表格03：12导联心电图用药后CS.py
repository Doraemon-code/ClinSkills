# %%
# %run ../../env.py
from utils.loaders import load_first_dose
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
index = ["受试者", "受试者状态", "访视名称", "页面名称"]
sig =["病史名称", "不良事件名称", "帕金森病_TXT", "其他，请说明"]

# %% [markdown]
# ## 12导联心电图

# %%

# 没有检查结果字段，则直接将临床意义结果视为检查结果

cols1 = ["检查日期", "临床意义_TXT", "异常描述"]
# cols2 = ["心率", "QT", "QTcF", "PR间期"]
# cols3 = ["心率_UNIT", "QT_UNIT", "QTcF_UNIT", "PR间期_UNIT"]

EG = pd.read_excel(raw_path, sheet_name = "EG", header = 0, skiprows = [1], usecols = index + cols1 + sig)

EG = EG.rename(columns={
    "检查日期":"评估日期",
    "临床意义_TXT":"临床意义",
})

EG["项目"] = EG["页面名称"]
EG["结果"] = EG["临床意义"]

# %%
df = pd.concat([EG])
df = df[(df["受试者状态"] != "筛选失败") & (df["临床意义"].notna())]

# 单个受试者最早服药日期，用来判断当前检查是给药前分组，还是给药后的分组

cols1 = ["服药日期"]
cols2 = ["受试者"]

EC = load_first_dose().rename(columns={"首次用药日期": "服药日期"})

DS_END = load_completion()

RAND = load_rand(cols=['受试者', '随机号'])

df = (df.merge(EC, on = cols2, how = "left")
        .merge(DS_END, on = cols2, how = "left")
        .merge(RAND, on = "受试者", how = "left")
     )

df["分组"] = df.apply( lambda row: "给药前检查" if row["评估日期"] <= row["服药日期"] else "给药后检查", axis=1 )

# 给药前的检查数据
# 离首次给药日期最近
# 检查结果正常或异常无临床意义
pre = df.drop(columns=sig)
pre = pre[pre["分组"] == "给药前检查"]
pre = pre.sort_values(by=["受试者", "页面名称", "项目", "服药日期"])

gcols = ["受试者", "页面名称", "项目"]

def pick_rows(g):
    base = g[g["访视名称"].eq("基线期（V2，D1）")]
    if not base.empty:
        if (base["临床意义"] == "异常有临床意义").any():
            return g.iloc[0:0]
        return base

    scr = g[g["访视名称"].eq("筛选期（V1，D-15~-13）")]
    scr = scr[scr["临床意义"].ne("异常有临床意义")]
    if not scr.empty:
        return scr

    return g.iloc[0:0]

pre = (
    pre.groupby(gcols, group_keys=False)
       .apply(pick_rows)
       .reset_index(drop=True)
)


prefix_map = { "病史名称": "MH:", "不良事件名称": "AE:", "帕金森病_TXT": "研究疾病:", "其他，请说明": "其他:" }
post = df[(df["分组"] == "给药后检查") & (df["临床意义"] == "异常有临床意义")].copy()
post["异常有临床意义，请描述"] = post[sig].apply(
    lambda row: ";".join(
        f"{prefix_map[col]}{str(val).replace('√', '帕金森病')}"
        for col, val in row.items()
        if pd.notna(val) and str(val).strip() != "" ), axis=1 )

post = post[["受试者", "访视名称", "页面名称", "评估日期", "项目", "结果", "临床意义", "异常描述", "异常有临床意义，请描述"]]

merge = pre.merge(post, on = ["受试者", "页面名称", "项目"], how = "left")
merge = merge[~((merge["结果_x"].isna()) | (merge["结果_y"].isna()))]

merge = merge.rename(columns = {
    "访视名称_x":"访视名称_首次用药前",
    "访视名称_y":"访视名称_首次用药后",
    "结果_x":"检查结果_首次用药前",
    "结果_y":"检查结果_首次用药后",
    "评估日期_x":"检查日期_首次用药前",
    "评估日期_y":"检查日期_首次用药后",
    "临床意义_x":"临床意义_首次用药前",
    "临床意义_y":"临床意义_首次用药后",
    "异常描述_x":"异常描述_首次用药前",
    "异常描述_y":"异常描述_首次用药后",
    "异常有临床意义，请描述":"异常有临床意义，请描述_首次用药后",
    "页面名称":"表单名称",
    "项目":"检查项",
    "受试者":"筛选号",
    "是否完成试验_TXT":"是否完成试验",
})

merge = merge[[
    "筛选号",
    "随机号",
    "表单名称",
    "检查项",
    # "正常值范围下限",
    # "正常值范围上限",
    # "单位",
    "访视名称_首次用药前",
    "检查日期_首次用药前",
    "检查结果_首次用药前",
    "临床意义_首次用药前",
    "异常描述_首次用药前",
    "访视名称_首次用药后",
    "检查日期_首次用药后",
    "检查结果_首次用药后",
    "临床意义_首次用药后",
    "异常描述_首次用药后",
    "异常有临床意义，请描述_首次用药后",
    "是否完成试验",
]]
merge.insert(0, "No.", range(1, len(merge) + 1))
merge['temp_id_visit'] = merge['筛选号'].astype(str) + merge['表单名称'].astype(str) + merge['检查项'].astype(str) + "_" + merge['访视名称_首次用药后'].astype(str)

# %%
eg_merge = merge.copy().drop(columns = ["temp_id_visit"])

file_name = f"{output_path}/listing/表39-4 12导联心电图用药后检查异常有临床意义清单.xlsx"
export_to_excel_twoheader(
    eg_merge, file_name, "表39-4 用药后检查异常有临床意义清单",
    title="表 39-4 用药后检查异常有临床意义清单",
    fixed_cols=['No.', '筛选号', '随机号', '表单名称', '检查项'],
    header_groups=[
        {'label': '首次用药前', 'children': ['访视名称', '检查日期', '检查结果', '临床意义', '异常描述']},
        {'label': '首次用药后', 'children': ['访视名称', '检查日期', '检查结果', '临床意义', '异常描述', '异常有临床意义，请描述']},
    ],
    trailing_cols=['是否完成试验'],
    col_widths=[(0, 0, 5), (1, 2, 8), (3, 4, 12), (5, 6, 16), (7, 7, 5), (7, 14, 18), (15, 15, 30), (16, 16, 14)],
    subject_col='筛选号',
)
