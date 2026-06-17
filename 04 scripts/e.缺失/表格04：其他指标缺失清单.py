# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

DS_END = load_completion()

SV_N = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = ["受试者", "访视名称", "是否进行本次访视_TXT"])
SV_N = SV_N[SV_N["是否进行本次访视_TXT"] == "否"]

# %%
index = ["受试者", "受试者状态", "访视名称","页面名称"]

# %% [markdown]
# # 其他指标

# %% [markdown]
# ## 清单：其他指标缺失
# - 这里差一个没计算试验药物发放记录和试验药物回收记录

# %%
usecols = index + ["是否进行体重检查_TXT"]
cols = ["体重"]
WT = pd.read_excel(raw_path, sheet_name = "VS_W_1", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
WT = WT.rename(columns = {
    "是否进行体重检查_TXT":"是否评估",
    "体重":"结果"
               })
WT["项目"] = WT["页面名称"]

# %%
usecols = index + ["是否进行身高体重检查_TXT"]
cols = ["体重", "身高"]
HW = pd.read_excel(raw_path, sheet_name = "VS_HW", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
HW = HW.melt(id_vars=usecols, value_vars=cols, var_name='项目', value_name='结果')
HW = HW.rename(columns = {
    "是否进行身高体重检查_TXT":"是否评估",
               })

# %%
usecols = index + [ "是否进行神经精神量表（NPI）评估_TXT"]
cols1 = [
 '患者有什么你知道是不真实的信念吗？',
 '患者坚信自己处境危险，其他人正计划伤害自己吗？',
 '患者坚信其他人要偷自己的东西吗？',
 '患者坚信自己的配偶有外遇吗？',
 '患者坚信自己的房子里住着不受欢迎的外人吗？',
 '患者坚信自己的配偶或其他人不是他们所说的人吗？',
 '患者坚信自己住的房子不是自己的家吗？',
 '患者坚信自己的家庭成员要抛弃自己吗？',
 '患者坚信家里实际上有电视或杂志上的人物吗？',
 '患者坚信什么异常的事情而我又没有问到吗？',
 '频率',
 '严重程度',
 '评分']

cols2 = [
 '患者有错误的视觉或声音等幻觉吗？',
 '患者说过听到了声音，或者其表现好像是听到了声音吗？',
 '患者与实际上并不存在的人对过话吗？',
 '患者说看到过别人没有看到的东西，或者其表现好像见到了别人看不见的东西吗？',
 '患者称闻到了气味，而别人并没有闻到吗？',
 '患者说过感觉有东西在自己的皮肤上吗？',
 '患者说过什么原因不明的味道吗？',
 '患者讲过其他不寻常的感觉体验吗？',
 '频率.1',
 '严重程度.1',
 '评分.1']

NPI = pd.read_excel(raw_path, sheet_name = "QS_NPI", header = 0, skiprows = [1], usecols = usecols + cols1 + cols2, dtype=str)
NPI = NPI.melt(id_vars=usecols, value_vars=cols1+cols2, var_name='项目', value_name='结果')
NPI = NPI.rename(columns = {
    "是否进行神经精神量表（NPI）评估_TXT":"是否评估",
               })

NPI["类别"] = ""
for i in cols1:
    NPI.loc[NPI["项目"] == i, "类别"] = "妄想部分"

NPI.loc[~NPI["项目"].isin(cols1), "类别"] = "幻觉部分"

groups = NPI.groupby(['受试者', '受试者状态', '访视名称', '类别'])
grouped = []

# 遍历每个分组
for _, group in groups:

    # 获取当前分组的类别
    category = group['类别'].iloc[0] if len(group) > 0 else None

    # 处理"妄想部分"的逻辑
    if category == "妄想部分":
        # 查找"患者有什么你知道是不真实的信念吗？"这一项
        target_row = group[group['项目'] == "患者有什么你知道是不真实的信念吗？"]
        if len(target_row) > 0 and target_row['结果'].iloc[0] == "2":
            # 如果结果等于2，只保留这一行
            group = target_row

    # 处理"幻觉部分"的逻辑
    elif category == "幻觉部分":
        # 查找"患者有错误的视觉或声音等幻觉吗？"这一项
        target_row = group[group['项目'] == "患者有错误的视觉或声音等幻觉吗？"]
        if len(target_row) > 0 and target_row['结果'].iloc[0] == "2":
            # 如果结果等于2，只保留这一行
            group = target_row

    grouped.append(group)

# 合并所有分组
NPI = pd.concat(grouped, ignore_index=True)

# %%
cols1 = [
 '“皮球”',
 '“国旗”',
 '“树木”',
 '93',
 '86',
 '79',
 '72',
 '65',
 '“皮球”.1',
 '“国旗”.1',
 '“树木”.1',
 '14.（主动出示手表）请问这是什么？',
 '14.（出示铅笔）请问这是什么？',
 '15.现在我说一句话，请您按照我说的话原样地重复一遍（只说一遍，完成正确的记1分），这句话是“四十四只石狮子”',
 '16.请阅读这张卡片所写的句子并照着去做（主试出示写有“闭上您的眼睛”大字的卡片，如果受试者闭上眼睛，记1分）“闭上您的眼睛”',
 '请用右手拿这张纸',
 '把纸对折',
 '将纸放在腿上',
 '18.请您写一句完整的的句子。（句子必须有主语、动词）',
 '19.请您按样子画图',
 'MMSE总分'
]

usecols = index + cols1
MMSE1 = pd.read_excel(raw_path, sheet_name = "QS_MMSE", header = 0, skiprows = [1], usecols = usecols , dtype=str)
MMSE1 = MMSE1.melt(id_vars=index, value_vars=cols1, var_name='项目', value_name='结果')

cols2 = ['请受试者说出下列各题答案_TXT', '得分']
usecols = index + cols2
MMSE2 = pd.read_excel(raw_path, sheet_name = "QS_MMSE", header = 0, skiprows = [1], usecols = usecols , dtype=str)
MMSE2 = MMSE2.rename(columns = {
    "得分":"结果",
    "请受试者说出下列各题答案_TXT":"项目"
})
MMSE = pd.concat([MMSE1, MMSE2])

# %%
cols = ["发药日期", "发药量"]
DA_DD = pd.read_excel(raw_path, sheet_name = "DA_DD", header = 0, skiprows = [1], usecols = index + cols + ["是否发放药物_TXT"], dtype=str)
DA_DD = DA_DD.melt(id_vars=index + ["是否发放药物_TXT"], value_vars=cols, var_name='项目', value_name='结果')
DA_DD = DA_DD.rename(columns={
    "是否发放药物_TXT":"是否评估"
})

# %%
cols = ["未回收原因", "回收日期", "返还药量", "损坏或遗失药量", "实际服用药量"]
DA_DR = pd.read_excel(raw_path, sheet_name = "DA_DR", header = 0, skiprows = [1], usecols = index + cols + ["是否回收药物_TXT"], dtype=str)
DA_DR = DA_DR.melt(id_vars=index + ["是否回收药物_TXT"], value_vars=cols, var_name='项目', value_name='结果')
DA_DR = DA_DR.rename(columns={
    "是否回收药物_TXT":"是否评估"
})

# %%
df = pd.concat([HW, WT, NPI, MMSE, DA_DD, DA_DR])
test = df[(df["是否评估"] == "否") & (df["结果"].isna()) & (df["页面名称"] == "试验药物回收记录") & (df["项目"] == "未回收原因")]
df

# %%
df = pd.concat([HW, WT, NPI, MMSE, DA_DD, DA_DR])

df1 = df[((df["是否评估"] == "是") & (df["结果"].isna()) & (df["项目"] != "未回收原因")) |
         ((df["是否评估"] == "否") & (df["结果"].isna()) & (df["页面名称"] == "试验药物回收记录") & (df["项目"] == "未回收原因"))]

df2 = df[(df["是否评估"] == "否")].copy()
df2["项目"] = df2["页面名称"]
df2 = df2.drop_duplicates(subset = ["受试者", "受试者状态", "访视名称","页面名称", "项目"])

df = pd.concat([df1, df2])

df = (df.merge(RAND, on = "受试者", how = "left")
        .merge(DS_END, on = "受试者", how = "left")
        .merge(SV_N, on = ["受试者", "访视名称"], how = "left")
     )

df = df[df["是否进行本次访视_TXT"] != "否"]

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
oth_missing =df.copy()
oth_missing.insert(0, "No.", range(1, len(oth_missing) + 1))

lc = len(oth_missing)
ls = len(oth_missing.drop_duplicates(subset = ["筛选号"]))

export_to_excel_with_format(
    oth_missing,
    f"{output_path}/listing/表38 其他指标缺失清单.xlsx",
    "表38 其他指标缺失清单",
    f"表38 其他指标缺失清单（{lc}例次{ls}例）"
)
