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
# # 重算：访视缺失 -> visit 汇总

# %%
cols = ["访视OID","页面名称", "访视日期"]
SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = index + cols).rename(columns={"访视日期":"评估日期"})
df = SV.sort_values(by = ["受试者", "访视名称", "页面名称", "评估日期"])
df = df.drop_duplicates()

df = df[(df["受试者状态"] != "筛选失败") & (df["访视OID"] != "V90")]
df["类别"] = "访视缺失"

df = (df.merge(RAND, on = "受试者", how = "left")
        .merge(DS_END, on = "受试者", how = "left")
     )

visit = df.copy()
visit = visit[visit["评估日期"].isna()]

visit = visit.rename(columns = {
    "受试者":"筛选号",
    "是否完成试验_TXT":"是否完成试验",
    "访视名称":"缺失的访视名称"
})

cols = ["筛选号", "随机号", "缺失的访视名称", "是否完成试验", "评估日期"]
visit = visit[cols]
visit.insert(0, "No.", range(1, len(visit) + 1))

lc = len(visit)
ls = len(visit.drop_duplicates(subset = ["筛选号"]))

visit = pd.DataFrame({
    "表单名称":"访视缺失",
    "例次":[lc],
    "例数":[ls]
})

# %% [markdown]
# # 重算：疗效评价指标缺失 -> efficacy / efficacy_summary

# %%
cols = ["是否进行SAPS量表评估_TXT", "条目_TXT", "严重程度评分"]
QS_SAPS1 = (pd.read_excel(raw_path, sheet_name = "QS_SAPS", header = 0, skiprows = [1], usecols = index + cols)
              .rename(columns = {
                  "是否进行SAPS量表评估_TXT":"是否评估",
                  "条目_TXT":"项目",
                  "严重程度评分":"结果"
              }))
cols = ["SAPS-PD评分", "GSAPS-H评分", "GSAPS-D评分", "GSAPS-H+D评分", "SAPS-H评分", "SAPS-D评分"]
QS_SAPS2 = (pd.read_excel(raw_path, sheet_name = "QS_SAPS", header = 0, skiprows = [1], usecols = index + cols + ["是否进行SAPS量表评估_TXT"])
              .rename(columns = {
                  "是否进行SAPS量表评估_TXT":"是否评估"
              }
           ))
QS_SAPS2 = QS_SAPS2.melt(id_vars= index + ["是否评估"], value_vars=cols, var_name='项目', value_name='结果')
QS_SAPS = pd.concat([QS_SAPS1, QS_SAPS2])

QS_SAPS1 = QS_SAPS[((QS_SAPS["是否评估"] == "是") & (QS_SAPS["结果"].isna()))]
QS_SAPS2 = QS_SAPS[(QS_SAPS["是否评估"] == "否")]
QS_SAPS2.loc[:, "项目"] = QS_SAPS2["页面名称"]
QS_SAPS2 = QS_SAPS2.drop_duplicates(subset = ["受试者", "受试者状态", "访视名称","页面名称", "项目"])
QS_SAPS = pd.concat([QS_SAPS1, QS_SAPS2])

cols = ["是否进行疾病严重程度量表（CGI-S）评估_TXT", "分值"]
QS_CGIS = pd.read_excel(raw_path, sheet_name = "QS_CGIS", header = 0, skiprows = [1], usecols = index + cols)
QS_CGIS = QS_CGIS.rename(columns = {"分值":"结果", "是否进行疾病严重程度量表（CGI-S）评估_TXT":"是否评估"})
QS_CGIS1 = QS_CGIS[((QS_CGIS["是否评估"] == "是") & (QS_CGIS["结果"].isna()))]
QS_CGIS2 = QS_CGIS[(QS_CGIS["是否评估"] == "否")].copy()
QS_CGIS2["项目"] = QS_CGIS2["页面名称"]
QS_CGIS2 = QS_CGIS2.drop_duplicates(subset = index + ["项目"])
QS_CGIS = pd.concat([QS_CGIS1, QS_CGIS2])

cols = ["是否进行总体进步量表（CGI-I）评估_TXT", "分值"]
QS_CGII = pd.read_excel(raw_path, sheet_name = "QS_CGII", header = 0, skiprows = [1], usecols = index + cols)
QS_CGII = QS_CGII.rename(columns = {"分值":"结果", "是否进行总体进步量表（CGI-I）评估_TXT":"是否评估"})
QS_CGII1 = QS_CGII[((QS_CGII["是否评估"] == "是") & (QS_CGII["结果"].isna()))]
QS_CGII2 = QS_CGII[(QS_CGII["是否评估"] == "否")].copy()
QS_CGII2["项目"] = QS_CGII2["页面名称"]
QS_CGII2 = QS_CGII2.drop_duplicates(subset = index + ["项目"])
QS_CGII = pd.concat([QS_CGII1, QS_CGII2])

usecols = ["受试者", "受试者状态", "访视名称","页面名称", "是否进行MDS统一帕金森病评定量表（MDS-UPDRS）评估_TXT"]
usecols1 = ["受试者", "受试者状态", "访视名称","页面名称", "是否评估"]
cols =  [
 '2.1 言语', '2.2 唾液和流涎', '2.3 咀嚼和吞咽', '2.4 进食', '2.5 穿衣', '2.6 卫生清洁', '2.7 书写',
 '2.8 嗜好和其他活动', '2.9 翻身', '2.10 震颤', '2.11 起床、下车或从较低椅子上站起来', '2.12 行走和平衡', '2.13 僵住',
 '3a 目前患者是否在服用治疗帕金森病的药物',
 '3b 如果患者正在服用治疗帕金森病的药物，请依据下面的定义标明患者所处的临床状态',
 '3c 患者是否在服用左旋多巴',
 '3.C1如果是，请注明自上次服药到现在有多少分钟',
 '3.1 言语', '3.2 面部表情', '3.3 僵直（颈部）', '3.3 僵直（左上肢）', '3.3 僵直（右上肢）', '3.3 僵直（左下肢）', '3.3 僵直（右下肢）',
 '3.4 对指试验（左手）', '3.4 对指试验（右手）', '3.5 手部运动（握拳试验）（左手）', '3.5 手部运动（握拳试验）（右手）',
 '3.6 手部旋前旋后（轮替试验）(左手)', '3.6 手部旋前旋后（轮替试验）(右手)', '3.7 脚趾拍地运动（左脚）', '3.7 脚趾拍地运动（右脚）',
 '3.8 腿部灵活性（左腿）', '3.8 腿部灵活性（右腿）', '3.9 从椅子上站起来（站立平衡试验）', '3.10 步态', '3.11 冻结步态',
 '3.12 姿势的稳定性', '3.13 姿势', '3.14 全身自发性的运动（身体动作迟缓）', '3.15 手部的姿势性震颤（左手）', '3.15 手部的姿势性震颤（右手）',
 '3.16 手部的动作性震颤（左手）', '3.16 手部的动作性震颤（右手）', '3.17 静止性震颤的幅度（左上肢）', '3.17 静止性震颤的幅度（右上肢）',
 '3.17 静止性震颤的幅度（左下肢）', '3.17 静止性震颤的幅度（右下肢）', '3.17 静止性震颤的幅度（嘴唇/下颌）', '3.18 静止性震颤的持续性',
 'A. 异动症（舞蹈样动作或肌张力障碍）是否在检查过程中出现', 'B. 如果有的话，这些运动是否干扰了运动功能的评分', '侯氏与叶氏（Hoehn & Yahr）分期法']

QS_MDS = pd.read_excel(raw_path, sheet_name = "QS_MDS", header = 0, skiprows = [1], usecols = cols + usecols)
QS_MDS = QS_MDS.rename(columns = {"是否进行MDS统一帕金森病评定量表（MDS-UPDRS）评估_TXT":"是否评估"})
QS_MDS = QS_MDS.melt(id_vars=usecols1, value_vars=cols, var_name='项目', value_name='结果')

QS_MDS1 = QS_MDS[((QS_MDS["是否评估"] == "是") & (QS_MDS["结果"].isna()))]
valid = QS_MDS[["受试者", "受试者状态", "访视名称", "页面名称", "项目", "结果"]]
valid = valid[(valid ["项目"] == "3a 目前患者是否在服用治疗帕金森病的药物") |
(valid ["项目"] == "3c 患者是否在服用左旋多巴") |
(valid ["项目"] == "A. 异动症（舞蹈样动作或肌张力障碍）是否在检查过程中出现")]
valid = valid[(valid ["结果"] == 2.0)]
valid = valid.pivot(index = index, columns = "项目", values = "结果").reset_index()
QS_MDS1 = QS_MDS1.merge(valid, on = index, how = "left")
QS_MDS1 = QS_MDS1[~((QS_MDS1['项目'] == "3b 如果患者正在服用治疗帕金森病的药物，请依据下面的定义标明患者所处的临床状态") & (QS_MDS1['3a 目前患者是否在服用治疗帕金森病的药物'] == 2.0)|
                    (QS_MDS1['项目'] == "3c 患者是否在服用左旋多巴") & (QS_MDS1['3a 目前患者是否在服用治疗帕金森病的药物'] == 2.0) |
                    (QS_MDS1['项目'] == "3.C1如果是，请注明自上次服药到现在有多少分钟") & (QS_MDS1['3a 目前患者是否在服用治疗帕金森病的药物'] == 2.0) |
                    (QS_MDS1['项目'] == "B. 如果有的话，这些运动是否干扰了运动功能的评分") & (QS_MDS1['A. 异动症（舞蹈样动作或肌张力障碍）是否在检查过程中出现'] == 2.0))
                   ]
QS_MDS1 = QS_MDS1[['受试者', '受试者状态', '访视名称', '页面名称', '是否评估', '项目', '结果']]
QS_MDS2 = QS_MDS[(QS_MDS["是否评估"] == "否")].copy()
QS_MDS2["项目"] = QS_MDS2["页面名称"]
QS_MDS2 = QS_MDS2.drop_duplicates(subset = ["受试者", "受试者状态", "访视名称","页面名称", "项目"])
QS_MDS = pd.concat([QS_MDS1, QS_MDS2])

df = pd.concat([QS_SAPS, QS_CGIS, QS_CGII, QS_MDS]).sort_values(by = index)
df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "疗效评价指标超窗"
df = (df.merge(RAND, on = "受试者", how = "left").merge(DS_END, on = "受试者", how = "left"))
df["项目"] = np.where(df["项目"].isna(), df["页面名称"], df["项目"])
df = df[df["结果"].isna()]
df = df.rename(columns = {
    "受试者":"筛选号", "页面名称":"表单名称", "项目":"缺失项", "是否完成试验_TXT":"是否完成试验"
})
df = df[["筛选号", "随机号", "访视名称", "表单名称", "缺失项", "是否完成试验"]]
df.insert(0, "No.", range(1, len(df) + 1))
efficacy_missing = df.copy()

efficacy = df.groupby("表单名称").agg(
    例次=('筛选号', lambda x: df.loc[x.index, ['筛选号', '访视名称']].drop_duplicates().shape[0]),
    例数=('筛选号', 'nunique')
).reset_index()

lc = len(efficacy_missing.drop_duplicates(subset = ["筛选号", "访视名称", "表单名称"]))
ls = len(efficacy_missing.drop_duplicates(subset = ["筛选号"]))
efficacy_summary = pd.DataFrame({
    "缺失子类别": ["疗效评价指标缺失"],
    "例次": [lc],
    "例数": [ls],
})

# %% [markdown]
# # 重算：安全性评价指标缺失 -> safe / safe_summary

# %%
usecols = index + ["是否检查生命体征_TXT", "项目_TXT", "结果"]
VS = pd.read_excel(raw_path, sheet_name = "VS", header = 0, skiprows = [1], usecols = usecols, dtype = str)
VS = VS.rename(columns={"是否检查生命体征_TXT":"是否评估", "项目_TXT":"项目"})

usecols = index + ["是否进行体格检查_TXT", "检查部位_TXT", "临床意义_TXT"]
PE = pd.read_excel(raw_path, sheet_name = "PE", header = 0, skiprows = [1], usecols = usecols, dtype = str)
PE = PE.rename(columns={"是否进行体格检查_TXT":"是否评估", "检查部位_TXT":"项目", "临床意义_TXT":"结果"})

usecols = index + ["是否进行12导联心电图检查_TXT", "临床意义_TXT"]
cols = ["心率", "QT", "QTcF", "PR间期"]
EG = pd.read_excel(raw_path, sheet_name = "EG", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
EG = EG.melt(id_vars=usecols, value_vars=cols, var_name='项目', value_name='结果')
EG = EG.rename(columns = {"是否进行12导联心电图检查_TXT":"是否评估", "临床意义_TXT":"临床意义"})

usecols = index + ["是否检查血常规_TXT", "项目.1", "测定值"]
LB_HEM = pd.read_excel(raw_path, sheet_name = "LB_HEM", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HEM = LB_HEM.rename(columns={"是否检查血常规_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查肝功能_TXT", "项目.1", "测定值"]
LB_LFT = pd.read_excel(raw_path, sheet_name = "LB_LFT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_LFT = LB_LFT.rename(columns={"是否检查肝功能_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查肾功能_TXT", "项目.1", "测定值"]
LB_RFT = pd.read_excel(raw_path, sheet_name = "LB_RFT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_RFT = LB_RFT.rename(columns={"是否检查肾功能_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})
groups = LB_RFT.groupby(['受试者', '受试者状态', '访视名称'])
grouped = []
for _, group in groups:
    urea_group = group[group['项目'].isin(['尿素氮', '尿素'])]
    if urea_group['结果'].notna().sum() == 1:
        urea_group = urea_group.dropna(subset=['结果'], how='any')
    grouped.append(pd.concat([group[~group['项目'].isin(['尿素氮', '尿素'])], urea_group]))
LB_RFT = pd.concat(grouped).reset_index(drop=True)

usecols = index + ["是否检查电解质_TXT", "项目.1", "测定值"]
LB_ELECT = pd.read_excel(raw_path, sheet_name = "LB_ELECT", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_ELECT = LB_ELECT.rename(columns={"是否检查电解质_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查空腹血糖_TXT", "项目.1", "测定值"]
LB_FBG = pd.read_excel(raw_path, sheet_name = "LB_FBG", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_FBG = LB_FBG.rename(columns={"是否检查空腹血糖_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查尿常规_TXT", "项目.1", "测定值"]
LB_URI = pd.read_excel(raw_path, sheet_name = "LB_URI", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_URI = LB_URI.rename(columns={"是否检查尿常规_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查血妊娠_TXT", "项目.1", "测定值"]
LB_HCG1 = pd.read_excel(raw_path, sheet_name = "LB_HCG1", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HCG1 = LB_HCG1.rename(columns={"是否检查血妊娠_TXT":"是否评估", "测定值":"结果", "项目.1":"项目"})

usecols = index + ["是否检查尿妊娠_TXT", "尿妊娠_TXT", "临床意义_TXT"]
LB_HCG2 = pd.read_excel(raw_path, sheet_name = "LB_HCG2", header = 0, skiprows = [1], usecols = usecols, dtype=str)
LB_HCG2 = LB_HCG2.rename(columns={"是否检查尿妊娠_TXT":"是否评估", "临床意义_TXT":"结果", "尿妊娠_TXT":"项目"})

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
df = (df.merge(RAND, on = "受试者", how = "left").merge(DS_END, on = "受试者", how = "left"))
df = df.rename(columns = {
    "受试者":"筛选号", "项目":"缺失项", "页面名称":"表单名称", "是否完成试验_TXT":"是否完成试验"
})
df.insert(0, "No.", range(1, len(df) + 1))
df = df[["筛选号", "随机号", "访视名称", "表单名称", "缺失项", "是否完成试验"]]
df = df[~df['访视名称'].str.contains('计划外访视')]
safe_missing = df.copy()

safe = df.groupby("表单名称").agg(
    例次=('筛选号', lambda x: df.loc[x.index, ['筛选号', '访视名称']].drop_duplicates().shape[0]),
    例数=('筛选号', 'nunique')
).reset_index()
order = ["生命体征", "体格检查", "血常规", "肝功能", "肾功能", "电解质", "空腹血糖", "尿常规", "血妊娠", "尿妊娠", "12导联心电图"]
safe['表单名称'] = pd.Categorical(safe['表单名称'], categories=order, ordered=True)
safe = safe.sort_values(by='表单名称')

lc = len(safe_missing.drop_duplicates(subset = ["筛选号", "访视名称", "表单名称"]))
ls = len(safe_missing.drop_duplicates(subset = ["筛选号"]))
safe_summary = pd.DataFrame({
    "缺失子类别": ["安全性评价指标缺失"],
    "例次": [lc],
    "例数": [ls],
})

# %% [markdown]
# # 重算：其他指标缺失 -> other / oth_summary

# %%
usecols = index + ["是否进行体重检查_TXT"]
cols = ["体重"]
WT = pd.read_excel(raw_path, sheet_name = "VS_W_1", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
WT = WT.rename(columns = {"是否进行体重检查_TXT":"是否评估", "体重":"结果"})
WT["项目"] = WT["页面名称"]

usecols = index + ["是否进行身高体重检查_TXT"]
cols = ["体重", "身高"]
HW = pd.read_excel(raw_path, sheet_name = "VS_HW", header = 0, skiprows = [1], usecols = usecols + cols, dtype=str)
HW = HW.melt(id_vars=usecols, value_vars=cols, var_name='项目', value_name='结果')
HW = HW.rename(columns = {"是否进行身高体重检查_TXT":"是否评估"})

usecols = index + [ "是否进行神经精神量表（NPI）评估_TXT"]
cols1 = [
 '患者有什么你知道是不真实的信念吗？', '患者坚信自己处境危险，其他人正计划伤害自己吗？', '患者坚信其他人要偷自己的东西吗？',
 '患者坚信自己的配偶有外遇吗？', '患者坚信自己的房子里住着不受欢迎的外人吗？', '患者坚信自己的配偶或其他人不是他们所说的人吗？',
 '患者坚信自己住的房子不是自己的家吗？', '患者坚信自己的家庭成员要抛弃自己吗？', '患者坚信家里实际上有电视或杂志上的人物吗？',
 '患者坚信什么异常的事情而我又没有问到吗？', '频率', '严重程度', '评分']
cols2 = [
 '患者有错误的视觉或声音等幻觉吗？', '患者说过听到了声音，或者其表现好像是听到了声音吗？', '患者与实际上并不存在的人对过话吗？',
 '患者说看到过别人没有看到的东西，或者其表现好像见到了别人看不见的东西吗？', '患者称闻到了气味，而别人并没有闻到吗？',
 '患者说过感觉有东西在自己的皮肤上吗？', '患者说过什么原因不明的味道吗？', '患者讲过其他不寻常的感觉体验吗？',
 '频率.1', '严重程度.1', '评分.1']
NPI = pd.read_excel(raw_path, sheet_name = "QS_NPI", header = 0, skiprows = [1], usecols = usecols + cols1 + cols2, dtype=str)
NPI = NPI.melt(id_vars=usecols, value_vars=cols1+cols2, var_name='项目', value_name='结果')
NPI = NPI.rename(columns = {"是否进行神经精神量表（NPI）评估_TXT":"是否评估"})
NPI["类别"] = ""
for i in cols1:
    NPI.loc[NPI["项目"] == i, "类别"] = "妄想部分"
NPI.loc[~NPI["项目"].isin(cols1), "类别"] = "幻觉部分"
groups = NPI.groupby(['受试者', '受试者状态', '访视名称', '类别'])
grouped = []
for _, group in groups:
    category = group['类别'].iloc[0] if len(group) > 0 else None
    if category == "妄想部分":
        target_row = group[group['项目'] == "患者有什么你知道是不真实的信念吗？"]
        if len(target_row) > 0 and target_row['结果'].iloc[0] == "2":
            group = target_row
    elif category == "幻觉部分":
        target_row = group[group['项目'] == "患者有错误的视觉或声音等幻觉吗？"]
        if len(target_row) > 0 and target_row['结果'].iloc[0] == "2":
            group = target_row
    grouped.append(group)
NPI = pd.concat(grouped, ignore_index=True)

cols1 = [
 '“皮球”', '“国旗”', '“树木”', '93', '86', '79', '72', '65', '“皮球”.1', '“国旗”.1', '“树木”.1',
 '14.（主动出示手表）请问这是什么？', '14.（出示铅笔）请问这是什么？',
 '15.现在我说一句话，请您按照我说的话原样地重复一遍（只说一遍，完成正确的记1分），这句话是“四十四只石狮子”',
 '16.请阅读这张卡片所写的句子并照着去做（主试出示写有“闭上您的眼睛”大字的卡片，如果受试者闭上眼睛，记1分）“闭上您的眼睛”',
 '请用右手拿这张纸', '把纸对折', '将纸放在腿上', '18.请您写一句完整的的句子。（句子必须有主语、动词）', '19.请您按样子画图', 'MMSE总分'
]
usecols = index + cols1
MMSE1 = pd.read_excel(raw_path, sheet_name = "QS_MMSE", header = 0, skiprows = [1], usecols = usecols , dtype=str)
MMSE1 = MMSE1.melt(id_vars=index, value_vars=cols1, var_name='项目', value_name='结果')
cols2 = ['请受试者说出下列各题答案_TXT', '得分']
usecols = index + cols2
MMSE2 = pd.read_excel(raw_path, sheet_name = "QS_MMSE", header = 0, skiprows = [1], usecols = usecols , dtype=str)
MMSE2 = MMSE2.rename(columns = {"得分":"结果", "请受试者说出下列各题答案_TXT":"项目"})
MMSE = pd.concat([MMSE1, MMSE2])

cols = ["发药日期", "发药量"]
DA_DD = pd.read_excel(raw_path, sheet_name = "DA_DD", header = 0, skiprows = [1], usecols = index + cols + ["是否发放药物_TXT"], dtype=str)
DA_DD = DA_DD.melt(id_vars=index + ["是否发放药物_TXT"], value_vars=cols, var_name='项目', value_name='结果')
DA_DD = DA_DD.rename(columns={"是否发放药物_TXT":"是否评估"})

cols = ["未回收原因", "回收日期", "返还药量", "损坏或遗失药量", "实际服用药量"]
DA_DR = pd.read_excel(raw_path, sheet_name = "DA_DR", header = 0, skiprows = [1], usecols = index + cols + ["是否回收药物_TXT"], dtype=str)
DA_DR = DA_DR.melt(id_vars=index + ["是否回收药物_TXT"], value_vars=cols, var_name='项目', value_name='结果')
DA_DR = DA_DR.rename(columns={"是否回收药物_TXT":"是否评估"})

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
    "受试者":"筛选号", "项目":"缺失项", "页面名称":"表单名称", "是否完成试验_TXT":"是否完成试验"
})
df.insert(0, "No.", range(1, len(df) + 1))
df = df[["筛选号", "随机号", "访视名称", "表单名称", "缺失项", "是否完成试验"]]
df = df[~df['访视名称'].str.contains('计划外访视')]
oth_missing = df.copy()

other = df.groupby("表单名称").agg(
    例次=('筛选号', lambda x: df.loc[x.index, ['筛选号', '访视名称']].drop_duplicates().shape[0]),
    例数=('筛选号', 'nunique')
).reset_index()
order = ["体重", "身高体重", "神经精神量表（NPI）", "哥伦比亚-自杀严重程度评定量表（C-SSRS）", "简易精神状态检查量表（MMSE）", "试验药物发放记录", "试验药物回收记录"]
other['表单名称'] = pd.Categorical(other['表单名称'], categories=order, ordered=True)
other = other.sort_values(by='表单名称')

lc = len(oth_missing.drop_duplicates(subset = ["筛选号", "访视名称", "表单名称"]))
ls = len(oth_missing.drop_duplicates(subset = ["筛选号"]))
oth_summary = pd.DataFrame({
    "缺失子类别": ["其他指标缺失"],
    "例次": [lc],
    "例数": [ls],
})

# %% [markdown]
# # 汇总
# ## 缺失汇总结果

# %%
miss = pd.concat([visit, efficacy, safe, other])

category_page_order = {
    "访视缺失":["访视日期"],
    "疗效评价指标缺失": ["SAPS量表", "疾病严重程度量表（CGI-S）", "总体进步量表（CGI-I）", "MDS统一帕金森病评定量表（MDS-UPDRS）"],
    "安全性评价指标缺失": ["生命体征", "体格检查", "血常规", "肝功能", "肾功能", "电解质", "空腹血糖", "尿常规", "血妊娠", "尿妊娠", "12导联心电图"],
    "其他指标缺失": ["体重", "身高体重", "神经精神量表（NPI）", "哥伦比亚-自杀严重程度评定量表（C-SSRS）", "简易精神状态检查量表（MMSE）", "试验药物发放记录", "试验药物回收记录"]
}

# 创建反向映射：表单名称 -> 类别
page_to_category = {}
for category, pages in category_page_order.items():
    for page in pages:
        page_to_category[page] = category

# 使用map添加类别列
# miss['类别'] = miss['表单名称'].map(page_to_category)

# miss_ex = miss.groupby('类别').agg({
#     '例次': 'sum',
#     '例数': 'sum'
# }).reset_index()

miss_ex = pd.concat([efficacy_summary, safe_summary, oth_summary])

miss_ex = miss_ex.rename(columns = {"缺失子类别":"表单名称"})
miss = pd.concat([miss, miss_ex])

order = []
for key, values in category_page_order.items():
    order.append(key)
    order.extend(values)

order_map = {name: i for i, name in enumerate(order)}
miss = miss.sort_values( by="表单名称", key=lambda col: col.map(order_map) )

# 所有大类名称（键）
category_keys = list(category_page_order.keys())

miss["表单名称"] = miss["表单名称"].apply(
    lambda x: x if x in category_keys else f"    {x}"
)


notes = [
    "不包括受试者失访/退出试验/死亡导致的缺失；",
    "例次（表单）：如缺失项为表单中的字段，将按照表单去重计数。"
]

save_table_to_docx_threeline(
        miss,
        f"{output_path}/table/表21 缺失情况汇总.docx",
        f'表21 缺失情况汇总',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
    )
