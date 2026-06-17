# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

DS_END = load_completion()

# %%
index = ["受试者", "受试者状态", "访视名称","页面名称"]

# %% [markdown]
# # 疗效缺失

# %% [markdown]
# ## 表格：疗效评价指标缺失

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

# %%
cols = ["是否进行疾病严重程度量表（CGI-S）评估_TXT", "分值"]
QS_CGIS = pd.read_excel(raw_path, sheet_name = "QS_CGIS", header = 0, skiprows = [1], usecols = index + cols)
QS_CGIS = QS_CGIS.rename(columns = {"分值":"结果", "是否进行疾病严重程度量表（CGI-S）评估_TXT":"是否评估"})

QS_CGIS1 = QS_CGIS[((QS_CGIS["是否评估"] == "是") & (QS_CGIS["结果"].isna()))]

QS_CGIS2 = QS_CGIS[(QS_CGIS["是否评估"] == "否")].copy()
QS_CGIS2["项目"] = QS_CGIS2["页面名称"]
QS_CGIS2 = QS_CGIS2.drop_duplicates(subset = index + ["项目"])
QS_CGIS = pd.concat([QS_CGIS1, QS_CGIS2])

# %%
cols = ["是否进行总体进步量表（CGI-I）评估_TXT", "分值"]
QS_CGII = pd.read_excel(raw_path, sheet_name = "QS_CGII", header = 0, skiprows = [1], usecols = index + cols)
QS_CGII = QS_CGII.rename(columns = {"分值":"结果", "是否进行总体进步量表（CGI-I）评估_TXT":"是否评估"})

QS_CGII1 = QS_CGII[((QS_CGII["是否评估"] == "是") & (QS_CGII["结果"].isna()))]

QS_CGII2 = QS_CGII[(QS_CGII["是否评估"] == "否")].copy()
QS_CGII2["项目"] = QS_CGII2["页面名称"]
QS_CGII2 = QS_CGII2.drop_duplicates(subset = index + ["项目"])
QS_CGII = pd.concat([QS_CGII1, QS_CGII2])

# %%

usecols = ["受试者", "受试者状态", "访视名称","页面名称", "是否进行MDS统一帕金森病评定量表（MDS-UPDRS）评估_TXT"]
usecols1 = ["受试者", "受试者状态", "访视名称","页面名称", "是否评估"]
cols =  [
 '2.1 言语',
 '2.2 唾液和流涎',
 '2.3 咀嚼和吞咽',
 '2.4 进食',
 '2.5 穿衣',
 '2.6 卫生清洁',
 '2.7 书写',
 '2.8 嗜好和其他活动',
 '2.9 翻身',
 '2.10 震颤',
 '2.11 起床、下车或从较低椅子上站起来',
 '2.12 行走和平衡',
 '2.13 僵住',
 '3a 目前患者是否在服用治疗帕金森病的药物',
 '3b 如果患者正在服用治疗帕金森病的药物，请依据下面的定义标明患者所处的临床状态',
 '3c 患者是否在服用左旋多巴',
 '3.C1如果是，请注明自上次服药到现在有多少分钟',
 '3.1 言语',
 '3.2 面部表情',
 '3.3 僵直（颈部）',
 '3.3 僵直（左上肢）',
 '3.3 僵直（右上肢）',
 '3.3 僵直（左下肢）',
 '3.3 僵直（右下肢）',
 '3.4 对指试验（左手）',
 '3.4 对指试验（右手）',
 '3.5 手部运动（握拳试验）（左手）',
 '3.5 手部运动（握拳试验）（右手）',
 '3.6 手部旋前旋后（轮替试验）(左手)',
 '3.6 手部旋前旋后（轮替试验）(右手)',
 '3.7 脚趾拍地运动（左脚）',
 '3.7 脚趾拍地运动（右脚）',
 '3.8 腿部灵活性（左腿）',
 '3.8 腿部灵活性（右腿）',
 '3.9 从椅子上站起来（站立平衡试验）',
 '3.10 步态',
 '3.11 冻结步态',
 '3.12 姿势的稳定性',
 '3.13 姿势',
 '3.14 全身自发性的运动（身体动作迟缓）',
 '3.15 手部的姿势性震颤（左手）',
 '3.15 手部的姿势性震颤（右手）',
 '3.16 手部的动作性震颤（左手）',
 '3.16 手部的动作性震颤（右手）',
 '3.17 静止性震颤的幅度（左上肢）',
 '3.17 静止性震颤的幅度（右上肢）',
 '3.17 静止性震颤的幅度（左下肢）',
 '3.17 静止性震颤的幅度（右下肢）',
 '3.17 静止性震颤的幅度（嘴唇/下颌）',
 '3.18 静止性震颤的持续性',
 'A. 异动症（舞蹈样动作或肌张力障碍）是否在检查过程中出现',
 'B. 如果有的话，这些运动是否干扰了运动功能的评分',
 '侯氏与叶氏（Hoehn & Yahr）分期法']

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
                    # (QS_MDS1['项目'] == "3.C1如果是，请注明自上次服药到现在有多少分钟") & (QS_MDS1['3c 患者是否在服用左旋多巴'] == 2.0) |
                    (QS_MDS1['项目'] == "B. 如果有的话，这些运动是否干扰了运动功能的评分") & (QS_MDS1['A. 异动症（舞蹈样动作或肌张力障碍）是否在检查过程中出现'] == 2.0))
                   ]
QS_MDS1 = QS_MDS1[['受试者', '受试者状态', '访视名称', '页面名称', '是否评估', '项目', '结果']]

QS_MDS2 = QS_MDS[(QS_MDS["是否评估"] == "否")].copy()
QS_MDS2["项目"] = QS_MDS2["页面名称"]
QS_MDS2 = QS_MDS2.drop_duplicates(subset = ["受试者", "受试者状态", "访视名称","页面名称", "项目"])
QS_MDS = pd.concat([QS_MDS1, QS_MDS2])

# %% [markdown]
# ## 清单：疗效评价指标

# %%
df = pd.concat([QS_SAPS, QS_CGIS, QS_CGII, QS_MDS]).sort_values(by = index)
df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "疗效评价指标超窗"

df = (df
        .merge(RAND, on = "受试者", how = "left")
        .merge(DS_END, on = "受试者", how = "left")
     )
df["项目"] = np.where(
  df["项目"].isna(),
    df["页面名称"],
    df["项目"]
)

df = df[df["结果"].isna()]

df = df.rename(columns = {
    "受试者":"筛选号",
    "页面名称":"表单名称",
    "项目":"缺失项",
    "是否完成试验_TXT":"是否完成试验"
})

df = df[["筛选号", "随机号", "访视名称", "表单名称", "缺失项", "是否完成试验"]]
df.insert(0, "No.", range(1, len(df) + 1))

# %%
efficacy_missing = df.copy()

lc = len(efficacy_missing)
ls = len(efficacy_missing.drop_duplicates(subset = ["筛选号"]))

notes = [
    "确认受试者访视缺失，该访视相关检查缺失不在此处重复罗列；",
    "整个表单缺失时，缺失项为表单名称。"
]

save_table_to_docx_threeline(
        efficacy_missing,
        f"{output_path}/table/表23 疗效性评价指标缺失清单.docx",
        f'表23 疗效性评价指标缺失清单（{lc}例次{ls}例）',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
    )
