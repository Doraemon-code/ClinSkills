# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
index = ["受试者", "受试者状态", "访视名称","页面名称"]

# %% [markdown]
# # 安全性指标

# %% [markdown]
# ## 表格：安全性评价指标缺失
# -  这里没有计算不良事件的缺失

# %%
usecols = index + ["是否检查生命体征_TXT", "项目_TXT", "结果"]
VS = pd.read_excel(raw_path, sheet_name = "VS", header = 0, skiprows = [1], usecols = usecols, dtype = str)
VS = VS.rename(columns={
    "是否检查生命体征_TXT":"是否评估",
    "项目_TXT":"项目",
})

# %%
usecols = index + ["是否进行体格检查_TXT", "检查部位_TXT", "临床意义_TXT"]
PE = pd.read_excel(raw_path, sheet_name = "PE", header = 0, skiprows = [1], usecols = usecols, dtype = str)
PE = PE.rename(columns={
    "是否进行体格检查_TXT":"是否评估",
    "检查部位_TXT":"项目",
    "临床意义_TXT":"结果",
})

# %%
usecols = index + ["是否进行12导联心电图检查_TXT", "临床意义_TXT"]
cols = ["心率", "QT", "QTcF", "PR间期"]
EG = pd.read_excel(raw_path, sheet_name = "EG", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
EG = EG.melt(id_vars=usecols, value_vars=cols, var_name='项目', value_name='结果')
EG = EG.rename(columns = {
    "是否进行12导联心电图检查_TXT":"是否评估",
    "临床意义_TXT":"临床意义"
})

# %%
usecols = index + ["是否检查血常规_TXT", "项目.1", "测定值"]
LB_HEM = pd.read_excel(raw_path, sheet_name = "LB_HEM", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HEM = LB_HEM.rename(columns={
    "是否检查血常规_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查肝功能_TXT", "项目.1", "测定值"]
LB_LFT = pd.read_excel(raw_path, sheet_name = "LB_LFT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_LFT = LB_LFT.rename(columns={
    "是否检查肝功能_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查肾功能_TXT", "项目.1", "测定值"]
LB_RFT = pd.read_excel(raw_path, sheet_name = "LB_RFT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_RFT = LB_RFT.rename(columns={
    "是否检查肾功能_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})
groups = LB_RFT.groupby(['受试者', '受试者状态', '访视名称'])
grouped = []
# 遍历每个分组
for _, group in groups:
    # 过滤出项目是'尿素氮'和'尿素'的行
    urea_group = group[group['项目'].isin(['尿素氮', '尿素'])]

    # 判断'尿素氮'和'尿素'的结果是否有空值
    if urea_group['结果'].notna().sum() == 1:
        # 删除结果为空的行
        urea_group = urea_group.dropna(subset=['结果'], how='any')

    # 如果两个值都为空或者都不为空，保留两个值
    grouped.append(pd.concat([group[~group['项目'].isin(['尿素氮', '尿素'])], urea_group]))

LB_RFT = pd.concat(grouped).reset_index(drop=True)

# %%
usecols = index + ["是否检查电解质_TXT", "项目.1", "测定值"]
LB_ELECT = pd.read_excel(raw_path, sheet_name = "LB_ELECT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_ELECT = LB_ELECT.rename(columns={
    "是否检查电解质_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查空腹血糖_TXT", "项目.1", "测定值"]
LB_FBG = pd.read_excel(raw_path, sheet_name = "LB_FBG", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_FBG = LB_FBG.rename(columns={
    "是否检查空腹血糖_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查尿常规_TXT", "项目.1", "测定值"]
LB_URI = pd.read_excel(raw_path, sheet_name = "LB_URI", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_URI = LB_URI.rename(columns={
    "是否检查尿常规_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查血妊娠_TXT", "项目.1", "测定值"]
LB_HCG1 = pd.read_excel(raw_path, sheet_name = "LB_HCG1", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HCG1 = LB_HCG1.rename(columns={
    "是否检查血妊娠_TXT":"是否评估",
    "测定值":"结果",
    "项目.1":"项目"
})

# %%
usecols = index + ["是否检查尿妊娠_TXT", "尿妊娠_TXT", "临床意义_TXT"]
LB_HCG2 = pd.read_excel(raw_path, sheet_name = "LB_HCG2", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HCG2 = LB_HCG2.rename(columns={
    "是否检查尿妊娠_TXT":"是否评估",
    "临床意义_TXT":"结果",
    "尿妊娠_TXT":"项目"
})

# %%
df = pd.concat([VS, PE, EG, LB_HEM, LB_LFT, LB_RFT, LB_ELECT, LB_FBG, LB_URI, LB_HCG1, LB_HCG2])
df = df.sort_values(by = ["受试者", "访视名称", "页面名称"])
df = df.drop_duplicates()

df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "安全性评价指标超窗"

all1 = df[((df["是否评估"] == "是") & ((df["结果"].isna()) | (df["结果"] == "未查")) )]

df = df[(df["是否评估"] == "否")].copy()
df["项目"] = df["页面名称"]
all2 = df.drop_duplicates(subset = ["受试者", "受试者状态", "访视名称","页面名称", "项目"])
df = pd.concat([all1, all2])

RAND = load_rand(cols=['受试者', '随机号'])

DS_END = load_completion()

df = (df.merge(RAND, on = "受试者", how = "left")
        .merge(DS_END, on = "受试者", how = "left")
     )

df = df.rename(columns = {
    "受试者":"筛选号",
    "项目":"缺失项",
    "页面名称":"表单名称",
    "是否完成试验_TXT":"是否完成试验"
})
df.insert(0, "No.", range(1, len(df) + 1))
df = df[["筛选号", "随机号", "访视名称", "表单名称", "缺失项", "是否完成试验"]]

df = df[~df['访视名称'].str.contains('计划外访视')]

# %%
safe_missing = df.copy()

lc = len(safe_missing)
ls = len(safe_missing.drop_duplicates(subset = ["筛选号"]))

export_to_excel_with_format(
    safe_missing,
    f"{output_path}/listing/表37 安全性评价指标缺失清单.xlsx",
    "表37 安全性评价指标缺失清单",
    f"表37 安全性评价指标缺失清单（{lc}例次{ls}例）"
)
