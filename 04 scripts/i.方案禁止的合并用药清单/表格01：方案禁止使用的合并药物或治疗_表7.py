# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %%
RAND = load_rand(cols=['受试者', '随机号'])

DS_END = load_completion()

# %% [markdown]
# ## 表 7 方案禁止使用的合并药物或治疗
# #### 1. 是否为伴发事件，CRF中没有相应字段，需要进一步判断逻辑
# #### 2. 治疗天数（天）表中没有列出，但是脚注中列出了，需进一步确认？

# %%
cols = [
    "受试者",
    "药物名称（通用名）",
    "该用药开始日期",
    "该用药结束日期",
    "单次给药剂量",
    "单位_TXT",
    "其他单位，请注明",
    "给药频率_TXT",
    "其他频率，请注明",
    "给药途径_TXT",
    "其他途径，请注明",
    "病史名称",
    "不良事件名称",
    "帕金森病",
    "预防用药，请说明",
    "其他，请说明"
]
CM = pd.read_excel(raw_path, sheet_name = "CM", header = 0, skiprows = [1], usecols = cols, dtype = str).fillna("")
CM["用药途径"] = np.where(
    CM["给药途径_TXT"] != "其他",
    CM["给药途径_TXT"],
    CM["其他途径，请注明"],
)

CM["给药频率"] = np.where(
    CM["给药频率_TXT"] != "其他",
    CM["给药频率_TXT"],
    CM["其他频率，请注明"],
)

CM["单位"] = np.where(
    CM["单位_TXT"] != "其他",
    CM["单位_TXT"],
    CM["其他单位，请注明"],
)

CM = CM.drop(columns = [
    "单位_TXT",
    "其他单位，请注明",
    "给药频率_TXT",
    "其他频率，请注明",
    "给药途径_TXT",
    "其他途径，请注明",])


# 正则模式：只捕获"名称"那一段，日期部分用非捕获组
pattern = r"\d+(.+?)\s(?:\d{4}|UK|uk)-(?:\d{2}|UK|uk)-(?:\d{2}|UK|uk)"

# 病史名称：提取所有匹配的第 1 捕获组，用 "，" 连接，并在前面加 MH:
def extract_mh(text: str) -> str:
    matches = re.findall(pattern, text)
    if not matches:
        return ""
    # 去掉两端空白再拼接
    names = ["".join(m).strip() if isinstance(m, tuple) else str(m).strip() for m in matches]
    return "MH:" + "，".join(names)

# 不良事件名称：同理，前面加 AE:
def extract_ae(text: str) -> str:
    matches = re.findall(pattern, text)
    if not matches:
        return ""
    names = ["".join(m).strip() if isinstance(m, tuple) else str(m).strip() for m in matches]
    return "AE:" + "，".join(names)

CM["病史名称"] = CM["病史名称"].apply(extract_mh)
CM["不良事件名称"] = CM["不良事件名称"].apply(extract_ae)

# 按规则拼接为"用药原因"，分隔符为 "；"
def build_reason(row):
    parts = []

    # MH 部分
    if row["病史名称"]:
        parts.append(row["病史名称"])

    # AE 部分
    if row["不良事件名称"]:
        parts.append(row["不良事件名称"])

    # 帕金森病列不为空，则拼接固定文案"帕金森病"
    if row["帕金森病"].strip() != "":
        parts.append("帕金森病")

    # 预防用药，请说明
    if row["预防用药，请说明"].strip() != "":
        parts.append(row["预防用药，请说明"].strip())

    # 其他，请说明
    if row["其他，请说明"].strip() != "":
        parts.append(row["其他，请说明"].strip())

    return "；".join(parts)

CM["用药原因"] = CM.apply(build_reason, axis=1)

CM = CM.drop(columns=["病史名称", "不良事件名称", "帕金森病", "预防用药，请说明", "其他，请说明"])
CM["用药开始日期"] = pd.to_datetime(CM["该用药开始日期"], errors="coerce")
CM["用药结束日期"] = pd.to_datetime(CM["该用药结束日期"], errors="coerce")

CM["合并用药时长（天）"] = (CM["用药结束日期"] - CM["用药开始日期"]).dt.days + 1
CM["合并用药时长（天）"] = (CM["合并用药时长（天）"].astype("Int64").astype("string").fillna(""))

EC = pd.read_excel(raw_path, sheet_name = "EC", header = 0, skiprows = [1], usecols = ["受试者", "服药日期"], dtype = str).fillna("")
EC["服药日期"] = pd.to_datetime(EC["服药日期"], errors="coerce")
EC = (
    EC.groupby("受试者", dropna=False)["服药日期"]
      .agg(["min", "max"])
      .rename(columns={"min": "试验药物首次用药日期", "max": "试验药物末次用药日期"})
)
EC["试验药物首次用药日期"] = EC["试验药物首次用药日期"].dt.strftime("%Y-%m-%d")
EC["试验药物末次用药日期"] = EC["试验药物末次用药日期"].dt.strftime("%Y-%m-%d")


SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = ["受试者", "访视OID", "访视日期"], dtype = str).fillna("")
SV = SV[SV["访视OID"] == "V50"]

df = (CM.merge(RAND, on = "受试者", how = "left")
        .merge(EC, on = "受试者", how = "left")
        .merge(SV, on = "受试者", how = "left")
        .merge(DS_END, on = "受试者", how = "left")
     )

df["是否为伴发事件"] = "是/否"

df = df[[
 '受试者',
 '随机号',
 '试验药物首次用药日期',
 '试验药物末次用药日期',
 '药物名称（通用名）',
 '该用药开始日期',
 '该用药结束日期',
 '访视日期',
 '合并用药时长（天）',
 '单次给药剂量',
 '单位',
 '给药频率',
 '用药途径',
 '用药原因',
 '是否为伴发事件',
 '是否完成试验_TXT'
]]

df = df.rename(columns = {
    "受试者":"筛选号",
    "该用药开始日期":"开始日期",
    "该用药结束日期":"结束日期",
    "访视日期":"访视5访视日",
    "是否完成试验_TXT":"是否完成试验"})

df.insert(0, "No.", range(1, len(df) + 1))
df

notes = [
    "治疗天数（天）=试验药物末次用药日期-试验药物首次用药日期+1；",
    "合并用药时长（天）=结束日期-开始日期+1。"
]

# save_table_to_docx_threeline(
#         df,
#         f'{output_path}/table/表7 方案禁止使用的合并药物或治疗.docx',
#         '表7 方案禁止使用的合并药物或治疗',
#         notes,
#         row_height_cm=0.6,
#         auto_width=True
#     )
