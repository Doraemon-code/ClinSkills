# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

# %% [markdown]
# # 清单：过敏史

# %%
cols = ["受试者", "过敏原_TXT", "其他过敏原", "严重程度_TXT"]
cols1 = [
 '疼痛',
 '脱皮',
 '发红',
 '发痒',
 '长疹子',
 '长痘',
 '红肿']
cols2 = ['其他过敏症状']

MH_ALLE = pd.read_excel(raw_path, sheet_name = "MH_ALLE", header = 0, skiprows = [1], usecols = cols + cols1 + cols2)

MH_ALLE["过敏原_TXT"] = np.where(
    MH_ALLE["其他过敏原"].notna(),
    MH_ALLE["其他过敏原"],
    MH_ALLE["过敏原_TXT"],
)
MH_ALLE = MH_ALLE[MH_ALLE["过敏原_TXT"].notna()]
MH_ALLE = MH_ALLE.merge(RAND, on = "受试者", how = "left")

# 将字段下的"√"变成具体的值
for index, row in MH_ALLE.iterrows():
    for col in cols1:
        if pd.notna(row[col]):
            MH_ALLE.at[index, col] = col

# 拼接对试验药物采取的措施、严重不良事件定义等多选字段
MH_ALLE["过敏症状"] = MH_ALLE[cols1 + cols2].apply(lambda row: ";".join(row.dropna()), axis=1)

MH_ALLE.columns = [col.replace("_TXT", "") for col in MH_ALLE.columns]
MH_ALLE = MH_ALLE.rename(columns = {
    "受试者":"筛选号",
})

stand_cols = ["筛选号", "随机号", "过敏原", "过敏症状", "严重程度"]
MH_ALLE = MH_ALLE[stand_cols]

MH_ALLE.insert(0, "No.", range(1, len(MH_ALLE) + 1))

lc = len(MH_ALLE)

export_to_excel_with_format(
    MH_ALLE,
    f"{output_path}/listing/表45 过敏史清单.xlsx",
    "表45 过敏史清单",
    f"表45 过敏史清单（{lc}例）"
)
