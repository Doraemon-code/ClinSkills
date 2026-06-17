# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

DS_END = load_completion()

# %% [markdown]
# ## 不良事件预处理
# - 这里只列出了3个AE严重程度变化，实际设计了6组收集字段，但是后面均无数据

# %%
cols1 = [
    "受试者",
    "不良事件名称",
    "发生日期",
    "转归日期",
    "试验结束时，转归_TXT",
    "初始严重程度_TXT",
    "严重程度是否有变化_TXT",
    "严重程度变化日期-1",
    "严重程度-1_TXT",
    "严重程度变化日期-2",
    "严重程度-2_TXT",
    "严重程度变化日期-3",
    "严重程度-3_TXT",
    "对试验药物采取的措施_TXT",
    "与试验药物的关系_TXT",
    "是否符合严重不良事件定义_TXT",
    "严重不良事件开始日期",
    "是否因此不良事件退出试验_TXT",
    "是否为特别关注不良事件_TXT",
    "PT术语",
    "SOC术语",
]

cols2 = ["未采取措施", "药物治疗", "非药物治疗"]
cols4 = ["其他，请描述"]
cols3 = ["导致死亡", "危及生命", "导致住院或延长住院时间", "永久或严重的残疾或者功能丧失", "先天性异常或者出生缺陷", "其他重要的医学事件"]

AE = pd.read_excel(raw_path, sheet_name = "AE", header = 0, skiprows = [1], usecols = cols1 + cols2 + cols3 + cols4)
AE = AE[AE["不良事件名称"].notna()]
m = AE["其他，请描述"].notna() & AE["其他，请描述"].astype(str).str.strip().ne("")
AE.loc[m, "其他，请描述"] = "其他:" + AE.loc[m, "其他，请描述"].astype(str)

# 将字段下的"√"变成具体的值
for index, row in AE.iterrows():
    for col in cols2 + cols3:
        if pd.notna(row[col]):
            AE.at[index, col] = col

# 拼接对试验药物采取的措施、严重不良事件定义等多选字段
AE["是否采取治疗措施"] = AE[cols2 + cols4].apply(lambda row: ";".join(row.dropna()), axis=1)
AE["严重不良事件定义"] = AE[cols3].apply(lambda row: ";".join(row.dropna()), axis=1)
AE = AE.drop(columns = cols2 + cols3 + cols4)

AE = (AE.merge(RAND, on = "受试者", how = "left").merge(DS_END, on = "受试者", how = "left"))

AE.columns = [col.replace("_TXT", "") for col in AE.columns]
AE = AE.rename(columns = {
    "受试者":"筛选号",
    "PT术语":"PT",
    "SOC术语":"SOC",
})

stand_cols = [
    "筛选号",
    "随机号",
    "不良事件名称",
    "SOC",
    "PT",
    "发生日期",
    "转归日期",
    "试验结束时，转归",
    "初始严重程度",
    "严重程度是否有变化",
    "严重程度变化日期-1",
    "严重程度-1",
    "严重程度变化日期-2",
    "严重程度-2",
    "严重程度变化日期-3",
    "严重程度-3",
    "是否采取治疗措施",
    "对试验药物采取的措施",
    "与试验药物的关系",
    "是否符合严重不良事件定义",
    "严重不良事件定义",
    "严重不良事件开始日期",
    "是否因此不良事件退出试验",
    "是否为特别关注不良事件",
    "是否完成试验"
     ]
AE = AE[stand_cols]
AE.insert(0, "No.", range(1, len(AE) + 1))

# %% [markdown]
# ##  清单：特别关注不良事件（XXX例次 XXX例）

# %%
AE_special = AE[(AE["是否为特别关注不良事件"] == "是")]

lc = len(AE_special)
ls = len(AE_special.drop_duplicates(subset = "筛选号"))

export_to_excel_with_format(
    AE_special,
    f"{output_path}/listing/表42 特别关注不良事件清单.xlsx",
    "表42 特别关注不良事件清单",
    f"表42 特别关注不良事件清单（{lc}例次{ls}例）"
)
