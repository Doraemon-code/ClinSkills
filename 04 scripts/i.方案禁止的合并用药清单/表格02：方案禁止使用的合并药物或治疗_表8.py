# %%
# %run ../../env.py
from utils.loaders import load_rand

# %% [markdown]
# ## 表 8 方案禁止使用的合并药物或治疗
# #### 1. CRF中没有明确的"因疗效不佳而发生的提前终止治疗"选项，只有"受试者自觉疗效不佳"和"研究者认为受试者继续用药不能获益"，是否均考虑在内
# #### 2. 需确认是否仅考虑治疗结束页面？
# #### 3. 脚注使用表8脚注的第一个?

# %%
DS_END1 = pd.read_excel(raw_path, sheet_name = "DS_END", header = 0, skiprows = [1], usecols = ["受试者", "页面名称", "受试者自行退出原因_TXT"], dtype = str).fillna("")
DS_END1 = DS_END1[(DS_END1["页面名称"] == "治疗结束页") & (DS_END1["受试者自行退出原因_TXT"] == "受试者自觉疗效不佳")]  #如果需要考虑研究者判断，这里需要补充条件
DS_END1 = DS_END1.drop(columns = ["页面名称"], axis = 1)

RAND = load_rand(cols=['受试者', '随机号'])

EC = pd.read_excel(raw_path, sheet_name = "EC", header = 0, skiprows = [1], usecols = ["受试者", "服药日期"], dtype = str).fillna("")
EC["服药日期"] = pd.to_datetime(EC["服药日期"], errors="coerce")
EC = (
    EC.groupby("受试者", dropna=False)["服药日期"]
      .agg(["min", "max"])
      .rename(columns={"min": "首次用药日期", "max": "末次用药日期"})
)

EC["首次用药日期"] = pd.to_datetime(EC["首次用药日期"], errors="coerce")
EC["末次用药日期"] = pd.to_datetime(EC["末次用药日期"], errors="coerce")

EC["治疗天数（天）"] = (EC["末次用药日期"] - EC["首次用药日期"]).dt.days + 1
EC["治疗天数（天）"] = (EC["治疗天数（天）"].astype("Int64").astype("string").fillna(""))

EC["首次用药日期"] = EC["首次用药日期"].dt.strftime("%Y-%m-%d")
EC["末次用药日期"] = EC["末次用药日期"].dt.strftime("%Y-%m-%d")

DS_END2 = pd.read_excel(raw_path, sheet_name = "DS_END", header = 0, skiprows = [1], usecols = ["受试者", "页面名称", "是否完成试验_TXT"], dtype = str).fillna("")
DS_END2 = DS_END2[DS_END2["页面名称"] == "试验完成情况总结"]
DS_END2 = DS_END2.drop(columns = ["页面名称"], axis = 1)

SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = ["受试者", "访视OID", "访视日期"], dtype = str).fillna("")
SV = SV[SV["访视OID"] == "V50"]

df = (DS_END1.merge(RAND, on = "受试者", how = "left")
        .merge(EC, on = "受试者", how = "left")
        .merge(DS_END2, on = "受试者", how = "left")
     )

df = df.rename(columns = {
    "受试者":"筛选号",
    "受试者自行退出原因_TXT":"提前终止治疗的原因",
    "是否完成试验_TXT":"是否完成试验"})

df = df[[
 '筛选号',
 '随机号',
 '首次用药日期',
 '末次用药日期',
 '治疗天数（天）',
 '提前终止治疗的原因',
 '是否完成试验'
]]

df.insert(0, "No.", range(1, len(df) + 1))

notes = [
    "治疗天数（天）=试验药物末次用药日期-试验药物首次用药日期+1；"
]

# save_table_to_docx_threeline(
#         df,
#         f'{output_path}/table/表7 方案禁止使用的合并药物或治疗.docx',
#         '表7 方案禁止使用的合并药物或治疗',
#         notes,
#         row_height_cm=0.6,
#         auto_width=True
#     )
