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
# ## 表格：疗效评价指标超窗

# %%
cols = ["评估日期"]
QS_SAPS = pd.read_excel(raw_path, sheet_name = "QS_SAPS", header = 0, skiprows = [1], usecols = index + cols)
QS_SAPS = QS_SAPS.drop_duplicates()
QS_CGIS = pd.read_excel(raw_path, sheet_name = "QS_CGIS", header = 0, skiprows = [1], usecols = index + cols)
QS_CGII = pd.read_excel(raw_path, sheet_name = "QS_CGII", header = 0, skiprows = [1], usecols = index + cols)
QS_MDS = pd.read_excel(raw_path, sheet_name = "QS_MDS", header = 0, skiprows = [1], usecols = index + cols)
df = pd.concat([QS_SAPS, QS_CGIS, QS_CGII, QS_MDS]).sort_values(by = index + cols)
df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "疗效评价指标超窗"

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

# 删除已经被视为访视超窗的数据
# efficacy_drop = visit_table[["受试者", "访视名称", "超窗", "评估日期"]].rename(columns = {"超窗":"访视超窗", "评估日期":"访视日期"})
# df = df.merge(efficacy_drop, on = ["受试者", "访视名称"], how = "left")
# df = df[(df["访视超窗"].isna()) | (df["访视日期"] != df["评估日期"])]

# %%
efficacy = df.copy()
efficacy["超窗时间（天）"] = np.where(
    efficacy["评估日期"] > efficacy["上限"],
    (efficacy["评估日期"] - efficacy["上限"]).dt.days,
    (efficacy["评估日期"] - efficacy["下限"]).dt.days
)

efficacy["计划时间窗"] = efficacy["下限"].astype(str) + "-" + efficacy["上限"].astype(str)

EC = load_first_dose()

cols = ["受试者", "页面名称", "是否完成试验_TXT"]
DS_END = load_completion()

RAND = load_rand(cols=['受试者', '受试者状态', '随机号'])
RAND = RAND[RAND["受试者状态"] != "筛选失败"].drop(columns = "受试者状态")

#是否完成访视5
cols = ["受试者", "访视OID", "是否进行本次访视_TXT"]
SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = cols)
SV= SV[(SV["访视OID"] == "V50")]

efficacy = (efficacy.merge(DS_END, on = "受试者", how = "left")
         .merge(EC, on = "受试者", how = "left")
         .merge(RAND, on = "受试者", how = "left")
         .merge(SV, on = "受试者", how = "left")
     )

efficacy = efficacy.rename(columns = {
    "受试者":"筛选号",
    "页面名称":"表单名称",
    "是否完成试验_TXT":"是否完成试验",
    "是否进行本次访视_TXT":"是否完成访视5"
                         })

stand_cols = [
    "筛选号",
    "随机号",
    "访视名称",
    "表单名称",
    "评估日期",
    "首次用药日期",
    "计划时间窗",
    "超窗时间（天）",
    "是否完成访视5",
    "是否完成试验"]

efficacy = efficacy[stand_cols].fillna("")

efficacy["评估日期"] = efficacy["评估日期"].dt.strftime('%Y-%m-%d')
efficacy["首次用药日期"] = efficacy["首次用药日期"].dt.strftime('%Y-%m-%d')
efficacy = efficacy.reindex( efficacy["超窗时间（天）"].abs().sort_values(ascending=False).index)

notes = []

table_no = 16
for visit_name, sub_df in efficacy.groupby("访视名称", sort=False, dropna=False):
    visit_disp = "未知访视" if pd.isna(visit_name) else str(visit_name)

    lc = len(sub_df)
    ls = len(sub_df.drop_duplicates(subset = ["筛选号"]))
    sub_df.insert(0, "No.", range(1, len(sub_df) + 1))

    file_path = f"{output_path}/table/表{table_no} 疗效评价指标超窗清单（{visit_disp}）.docx"
    title = f"表{table_no} 疗效评价指标超窗清单（{visit_disp}）（{lc}例次{ls}例）"

    save_table_to_docx_threeline(
        sub_df,
        str(file_path),
        title,
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
    )

    table_no += 1
