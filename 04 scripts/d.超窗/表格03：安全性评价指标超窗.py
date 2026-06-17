# %%
# %run ../../env.py
from utils.loaders import load_first_dose
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
TW = pd.read_excel(timewin_path, sheet_name = "时间窗", usecols = ["类别", "访视名称", "时间窗下限", "时间窗上限"])
TW["时间窗下限"] = TW["时间窗下限"].astype("Int32")
TW["时间窗上限"] = TW["时间窗上限"].astype("Int32")

# %%
index = ["受试者", "受试者状态", "访视名称","页面名称"]

# %% [markdown]
# ## 重算：访视超窗（用于剔除已计入访视超窗的行 visit_drop）

# %%
SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = index + ["访视日期"]).rename(columns={"访视日期":"评估日期"})
df = SV.sort_values(by = ["受试者", "访视名称", "页面名称", "评估日期"])
df = df.drop_duplicates()

df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "其他指标超窗"

RAND = load_rand(cols=['受试者', '随机日期'])

df = (df.merge(TW, left_on = ["类别", "访视名称"], right_on = ["类别", "访视名称"], how = "left")
        .merge(RAND, on = "受试者", how = "left")
     )

df["随机日期"] = pd.to_datetime(df["随机日期"], errors='coerce')
df["评估日期"] = pd.to_datetime(df["评估日期"], errors='coerce')
df["时间窗上限"] = pd.to_numeric(df["时间窗上限"], errors='coerce')
df["时间窗下限"] = pd.to_numeric(df["时间窗下限"], errors='coerce')

condition = df["访视名称"] == "筛选期（V1，D-15~-13）"

df.loc[~condition, "上限"] = df.loc[~condition, "随机日期"] + pd.to_timedelta(df.loc[~condition, "时间窗上限"], unit='D')
df.loc[~condition, "下限"] = df.loc[~condition, "随机日期"] + pd.to_timedelta(df.loc[~condition, "时间窗下限"], unit='D')

df.loc[condition, "上限"] = df.loc[condition, "随机日期"] - pd.to_timedelta(df.loc[condition, "时间窗上限"], unit='D')
df.loc[condition, "下限"] = df.loc[condition, "随机日期"] - pd.to_timedelta(df.loc[condition, "时间窗下限"], unit='D')

df["超窗"] = np.where((df["评估日期"] > df["上限"]) | (df["评估日期"] < df["下限"]), "超窗", "未超窗")
df = df[df["超窗"] == "超窗"]

visit_table = df.copy()

# %% [markdown]
# ## 表格：安全性评价指标超窗

# %%
VS = pd.read_excel(raw_path, sheet_name = "VS", header = 0, skiprows = [1], usecols = index + ["检查日期"]).rename(columns={"检查日期":"评估日期"})
PE = pd.read_excel(raw_path, sheet_name = "PE", header = 0, skiprows = [1], usecols = index + ["检查日期"]).rename(columns={"检查日期":"评估日期"})
EG = pd.read_excel(raw_path, sheet_name = "EG", header = 0, skiprows = [1], usecols = index + ["检查日期"]).rename(columns={"检查日期":"评估日期"})

LB_HEM = pd.read_excel(raw_path, sheet_name = "LB_HEM", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_LFT = pd.read_excel(raw_path, sheet_name = "LB_LFT", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_RFT = pd.read_excel(raw_path, sheet_name = "LB_RFT", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_ELECT = pd.read_excel(raw_path, sheet_name = "LB_ELECT", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_FBG = pd.read_excel(raw_path, sheet_name = "LB_FBG", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_URI = pd.read_excel(raw_path, sheet_name = "LB_URI", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_HCG1 = pd.read_excel(raw_path, sheet_name = "LB_HCG1", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})
LB_HCG2 = pd.read_excel(raw_path, sheet_name = "LB_HCG2", header = 0, skiprows = [1], usecols = index + ["采样日期"]).rename(columns={"采样日期":"评估日期"})

df = pd.concat([VS, PE, EG, LB_HEM, LB_LFT, LB_RFT, LB_ELECT, LB_FBG, LB_URI, LB_HCG1, LB_HCG2]).sort_values(by = ["受试者", "访视名称", "页面名称", "评估日期"])
df = df.drop_duplicates()

df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "安全性评价指标超窗"

RAND = load_rand(cols=['受试者', '随机日期'])

df = (df.merge(TW, left_on = ["类别", "访视名称"], right_on = ["类别", "访视名称"], how = "left")
        .merge(RAND, on = "受试者", how = "left")
     )

# 确保日期列是 datetime 格式
df["随机日期"] = pd.to_datetime(df["随机日期"], errors='coerce')
df["评估日期"] = pd.to_datetime(df["评估日期"], errors='coerce')

# 确保时间窗列是数值型
df["时间窗上限"] = pd.to_numeric(df["时间窗上限"], errors='coerce')
df["时间窗下限"] = pd.to_numeric(df["时间窗下限"], errors='coerce')

# 定义条件：访视名称为"筛选期（V1，D-15~-13）"
condition = df["访视名称"] == "筛选期（V1，D-15~-13）"

df.loc[~condition, "上限"] = df.loc[~condition, "随机日期"] + pd.to_timedelta(df.loc[~condition, "时间窗上限"], unit='D')
df.loc[~condition, "下限"] = df.loc[~condition, "随机日期"] + pd.to_timedelta(df.loc[~condition, "时间窗下限"], unit='D')

df.loc[condition, "上限"] = df.loc[condition, "随机日期"] - pd.to_timedelta(df.loc[condition, "时间窗上限"], unit='D')
df.loc[condition, "下限"] = df.loc[condition, "随机日期"] - pd.to_timedelta(df.loc[condition, "时间窗下限"], unit='D')

# 比较评估日期与上下限，判断超窗与否
df["超窗"] = np.where((df["评估日期"] > df["上限"]) | (df["评估日期"] < df["下限"]), "超窗", "未超窗")
df = df[df["超窗"] == "超窗"]

# 移除访视超窗的情况
visit_drop = visit_table[["受试者", "访视名称", "超窗", "评估日期"]].rename(columns = {"超窗":"访视超窗", "评估日期":"访视日期"})
df = df.merge(visit_drop, on = ["受试者", "访视名称"], how = "left")
df = df[(df["访视超窗"].isna()) | (df["访视日期"] != df["评估日期"])]

# %%
safe = df.copy()
safe["超窗时间（天）"] = np.where(
    safe["评估日期"] > safe["上限"],
    (safe["评估日期"] - safe["上限"]).dt.days,
    (safe["评估日期"] - safe["下限"]).dt.days
)

safe["计划时间窗"] = safe["下限"].astype(str) + "-" + safe["上限"].astype(str)

cols = ["受试者", "服药日期"]
EC = load_first_dose()

cols = ["受试者", "页面名称", "是否完成试验_TXT"]
DS_END = load_completion()

RAND = load_rand(cols=['受试者', '受试者状态', '随机号'])
RAND = RAND[RAND["受试者状态"] != "筛选失败"]

safe = (safe.merge(DS_END, on = "受试者", how = "left")
            .merge(EC, on = "受试者", how = "left")
            .merge(RAND, on = "受试者", how = "left")
     )


safe["评估日期"] = safe["评估日期"].dt.strftime('%Y-%m-%d')
safe["首次用药日期"] = safe["首次用药日期"].dt.strftime('%Y-%m-%d')
safe = safe.reindex(safe["超窗时间（天）"].abs().sort_values(ascending=False).index)

safe = safe.rename(columns = {
    "受试者":"筛选号",
    "页面名称":"表单名称",
    "是否完成试验_TXT":"是否完成试验",
    "评估日期":"采样/检查/测量日期",
                         })

lc = len(safe)
ls = len(safe.drop_duplicates(subset = ["筛选号"]))

stand_cols = [
    "筛选号",
    "随机号",
    "访视名称",
    "表单名称",
    "采样/检查/测量日期",
    "首次用药日期",
    "计划时间窗",
    "超窗时间（天）",
    "是否完成试验"]

safe = safe[stand_cols]
safe.insert(0, "No.", range(1, len(safe) + 1))

export_to_excel_with_format(
    safe,
    f"{output_path}/listing/表34 安全性评价指标超窗清单.xlsx",
    "表34 安全性评价指标超窗清单",
    f"表34 安全性评价指标超窗清单（{lc}例次{ls}例）"
)
