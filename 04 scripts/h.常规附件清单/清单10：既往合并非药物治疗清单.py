# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

# %% [markdown]
# # 清单：既往/合并非药物治疗

# %%
index = ["受试者"]
cols1 = [
        "治疗名称",
        "治疗频率_TXT",
        "其他频率，请注明",
        "该治疗开始日期",
        "试验结束时，是否持续_TXT",
        "该治疗结束日期",
       ]
cols2 = ["帕金森病"]
cols3 = ["病史名称", "不良事件名称", "预防治疗，请说明", "其他，请说明"]

PR = pd.read_excel(raw_path, sheet_name = "PR", header = 0, skiprows = [1], usecols = index + cols1 + cols2 + cols3)
PR = PR[PR["治疗名称"].notna()]

for index, row in PR.iterrows():
    for col in cols2:
        if pd.notna(row[col]):
            PR.at[index, col] = col

PR["治疗原因"] = PR[cols2 + cols3].apply(lambda row: ";".join(row.dropna()), axis=1)
PR["治疗频率_TXT"] = np.where(PR["其他频率，请注明"].notna(), PR["其他频率，请注明"], PR["治疗频率_TXT"])

PR = PR.merge(RAND, on = "受试者", how = "left")
PR.columns = [col.replace("_TXT", "") for col in PR.columns]

PR = PR.rename(columns = {
    "受试者":"筛选号",
})

stand_cols = [
    "筛选号",
    "随机号",
    "治疗名称",
    "治疗原因",
    "治疗频率",
    "该治疗开始日期",
    "试验结束时，是否持续",
    "该治疗结束日期",
]
PR = PR[stand_cols]
PR.insert(0, "No.", range(1, len(PR) + 1))

lc = len(PR)
ls = len(PR.drop_duplicates(subset = "筛选号"))

export_to_excel_with_format(
    PR,
    f"{output_path}/listing/表49 既往合并非药物治疗清单.xlsx",
    "表49 既往合并非药物治疗清单",
    f"表49 既往合并非药物治疗清单（{lc}例次{ls}例）"
)
