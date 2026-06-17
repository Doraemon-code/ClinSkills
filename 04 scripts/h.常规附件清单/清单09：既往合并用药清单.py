# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

# %% [markdown]
# # 清单：既往/合并用药

# %%
index = ["受试者"]
cols1 = [
        "药物名称（通用名）",
        "单次给药剂量",
        "单位_TXT",
        "其他单位，请注明",
        "给药频率_TXT",
        "其他频率，请注明",
        "给药途径_TXT",
        "其他途径，请注明",
        "该用药开始日期",
        "试验结束时，是否持续_TXT",
        "该用药结束日期",
       ]
cols2 = ["帕金森病"]
cols3 = ["病史名称", "不良事件名称", "预防用药，请说明", "其他，请说明"]

CM = pd.read_excel(raw_path, sheet_name = "CM", header = 0, skiprows = [1], usecols = index + cols1 + cols2 + cols3)
CM = CM[CM["药物名称（通用名）"].notna()]

for index, row in CM.iterrows():
    for col in cols2:
        if pd.notna(row[col]):
            CM.at[index, col] = col

CM["给药原因"] = CM[cols2 + cols3].apply(lambda row: ";".join(row.dropna()), axis=1)
CM["单位_TXT"] = np.where(CM["其他单位，请注明"].notna(), CM["其他单位，请注明"], CM["单位_TXT"])
CM["给药频率_TXT"] = np.where(CM["其他频率，请注明"].notna(), CM["其他频率，请注明"], CM["给药频率_TXT"])
CM["给药途径_TXT"] = np.where(CM["其他途径，请注明"].notna(), CM["其他途径，请注明"], CM["给药途径_TXT"])

CM = CM.merge(RAND, on = "受试者", how = "left")
CM.columns = [col.replace("_TXT", "") for col in CM.columns]

CM = CM.rename(columns = {
    "受试者":"筛选号",
})

stand_cols = [
    "筛选号",
    "随机号",
    "药物名称（通用名）",
    "给药原因",
    "单次给药剂量",
    "单位",
    "给药频率",
    "给药途径",
    "该用药开始日期",
    "试验结束时，是否持续",
    "该用药结束日期",
]
CM = CM[stand_cols]
CM.insert(0, "No.", range(1, len(CM) + 1))

lc = len(CM)
ls = len(CM.drop_duplicates(subset = "筛选号"))

export_to_excel_with_format(
    CM,
    f"{output_path}/listing/表48 既往合并用药清单.xlsx",
    "表48 既往合并用药清单",
    f"表48 既往合并用药清单（{lc}例次{ls}例）"
)
