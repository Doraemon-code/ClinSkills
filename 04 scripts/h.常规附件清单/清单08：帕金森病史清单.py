# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

# %% [markdown]
# # 清单：帕金森病史

# %%
index = ["受试者"]
cols1 = [
    "是否明确诊断帕金森综合征_TXT",
    "最早诊断帕金森病时间",
    "是否诊断为帕金森病_TXT",
]

cols2 = ["运动迟缓", "静止性震颤", "肌强直"]
cols3 = ["确诊不存在绝对排除标准", "至少存在2条支持标准", "没有警示征象"]
cols4 = ["是否发生精神症状_TXT", "精神症状_TXT", "首次出现日期", "筛选前一个月每周是否出现_TXT"]

MH_PD = pd.read_excel(raw_path, sheet_name = "MH_PD", header = 0, skiprows = [1], usecols = index + cols1 + cols2 + cols3+ cols4)
# 多选拼接
for index, row in MH_PD.iterrows():
    for col in cols2:
        if pd.notna(row[col]):
            MH_PD.at[index, col] = col

for index, row in MH_PD.iterrows():
    for col in cols3:
        if pd.notna(row[col]):
            MH_PD.at[index, col] = col

MH_PD["帕金森综合征诊断条件"] = MH_PD[cols2].apply(lambda row: ";".join(row.dropna()), axis=1)
MH_PD["帕金森病具备的诊断条件"] = MH_PD[cols3].apply(lambda row: ";".join(row.dropna()), axis=1)

MH_PD = MH_PD.merge(RAND, on = "受试者", how = "left")
MH_PD.columns = [col.replace("_TXT", "") for col in MH_PD.columns]

MH_PD = MH_PD.rename(columns = {
    "受试者":"筛选号",
})

stand_cols = [
    "筛选号",
    "随机号",
    "是否明确诊断帕金森综合征",
    "最早诊断帕金森病时间",
    "帕金森综合征诊断条件",
    "是否诊断为帕金森病",
    "帕金森病具备的诊断条件",
    "是否发生精神症状",
    "精神症状",
    "首次出现日期",
    "筛选前一个月每周是否出现",
]
MH_PD = MH_PD[stand_cols]
MH_PD.insert(0, "No.", range(1, len(MH_PD) + 1))

lc = len(MH_PD)
ls = len(MH_PD.drop_duplicates(subset = "筛选号"))

export_to_excel_with_format(
    MH_PD,
    f"{output_path}/listing/表47 帕金森病史清单.xlsx",
    "表47 帕金森病史清单",
    f"表47 帕金森病史清单（{lc}例次{ls}例）"
)
