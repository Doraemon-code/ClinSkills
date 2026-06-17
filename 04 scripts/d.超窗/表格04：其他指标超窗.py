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
# ## 表格：其他指标

# %%
VS_HW = pd.read_excel(raw_path, sheet_name = "VS_HW", header = 0, skiprows = [1], usecols = index + ["测量日期"]).rename(columns={"测量日期":"评估日期"})
VS_W_1 = pd.read_excel(raw_path, sheet_name = "VS_W_1", header = 0, skiprows = [1], usecols = index + ["测量日期"]).rename(columns={"测量日期":"评估日期"})
QS_NPI = pd.read_excel(raw_path, sheet_name = "QS_NPI", header = 0, skiprows = [1], usecols = index + ["评估日期"])
QS_SSRS = pd.read_excel(raw_path, sheet_name = "QS_SSRS", header = 0, skiprows = [1], usecols = index + ["评估日期"])
QS_MMSE = pd.read_excel(raw_path, sheet_name = "QS_MMSE", header = 0, skiprows = [1], usecols = index + ["评估日期"])
DA_DD = pd.read_excel(raw_path, sheet_name = "DA_DD", header = 0, skiprows = [1], usecols = index + ["发药日期"]).rename(columns={"发药日期":"评估日期"})
DA_DR = pd.read_excel(raw_path, sheet_name = "DA_DR", header = 0, skiprows = [1], usecols = index + ["回收日期"]).rename(columns={"回收日期":"评估日期"})

df = pd.concat([VS_HW, VS_W_1, QS_NPI, QS_SSRS, QS_MMSE, DA_DD, DA_DR]).sort_values(by = ["受试者", "访视名称", "页面名称", "评估日期"])
df = df.drop_duplicates()

df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "其他指标超窗"

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
oth = df.copy()
oth["超窗时间（天）"] = np.where(
    oth["评估日期"] > oth["上限"],
    (oth["评估日期"] - oth["上限"]).dt.days,
    (oth["评估日期"] - oth["下限"]).dt.days
)

oth["计划时间窗"] = oth["下限"].astype(str) + "-" + oth["上限"].astype(str)

cols = ["受试者", "服药日期"]
EC = load_first_dose()

cols = ["受试者", "页面名称", "是否完成试验_TXT"]
DS_END = load_completion()

RAND = load_rand(cols=['受试者', '受试者状态', '随机号'])
RAND = RAND[RAND["受试者状态"] != "筛选失败"]

oth = (oth.merge(DS_END, on = "受试者", how = "left")
            .merge(EC, on = "受试者", how = "left")
            .merge(RAND, on = "受试者", how = "left")
     )

oth["评估日期"] = oth["评估日期"].dt.strftime('%Y-%m-%d')
oth["首次用药日期"] = oth["首次用药日期"].dt.strftime('%Y-%m-%d')
oth = oth.reindex(oth["超窗时间（天）"].abs().sort_values(ascending=False).index)

oth = oth.rename(columns = {
    "受试者":"筛选号",
    "页面名称":"表单名称",
    "是否完成试验_TXT":"是否完成试验",
    "评估日期":"发生日期",
                         })
stand_cols = [
    "筛选号",
    "随机号",
    "访视名称",
    "表单名称",
    "发生日期",
    "首次用药日期",
    "计划时间窗",
    "超窗时间（天）",
    "是否完成试验"]

oth = oth[stand_cols]
oth.insert(0, "No.", range(1, len(oth) + 1))

lc = len(oth)
ls = len(oth.drop_duplicates(subset = ["筛选号"]))

export_to_excel_with_format(
    oth,
    f"{output_path}/listing/表35 其他指标超窗清单.xlsx",
    "表35 其他指标超窗清单",
    f"表35 其他指标超窗清单（{lc}例次{ls}例）"
)
