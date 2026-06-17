# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

# %% [markdown]
# # 清单：个人生活史

# %%
cols = ["受试者", "既往月经是否规律_TXT", "末次月经开始时间", "页面名称"]
RP = pd.read_excel(raw_path, sheet_name = "RP", header = 0, skiprows = [1], usecols = cols)
RP = RP[RP["页面名称"] == "个人生活史"]

cols = ["受试者", "是否吸烟_TXT", "是否饮酒_TXT"]
SU = pd.read_excel(raw_path, sheet_name = "SU", header = 0, skiprows = [1], usecols = cols)

cols = ["受试者", "性别_TXT"]
DM = pd.read_excel(raw_path, sheet_name = "DM", header = 0, skiprows = [1], usecols = cols)

SU = (SU.merge(RP, on = "受试者", how = "left")
        .merge(RAND, on = "受试者", how = "left")
        .merge(DM, on = "受试者", how = "left")
     )

SU.columns = [col.replace("_TXT", "") for col in SU.columns]

SU = SU.rename(columns = {
    "受试者":"筛选号",
})

stand_cols = ["筛选号", "随机号", "性别", "是否吸烟", "是否饮酒", "既往月经是否规律", "末次月经开始时间"]
SU = SU[stand_cols]
SU.insert(0, "No.", range(1, len(SU) + 1))

lc = len(SU)

export_to_excel_with_format(
    SU,
    f"{output_path}/listing/表44 个人生活史清单.xlsx",
    "表44 个人生活史清单",
    f"表44 个人生活史清单（{lc}例）"
)
