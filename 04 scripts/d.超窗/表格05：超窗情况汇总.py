# %%
# %run ../../env.py
from utils.loaders import load_rand

# %%
TW = pd.read_excel(timewin_path, sheet_name = "时间窗", usecols = ["类别", "访视名称", "时间窗下限", "时间窗上限"])
TW["时间窗下限"] = TW["时间窗下限"].astype("Int32")
TW["时间窗上限"] = TW["时间窗上限"].astype("Int32")

# %%
index = ["受试者", "受试者状态", "访视名称","页面名称"]

# %% [markdown]
# ## 重算：访视超窗 -> visit_table

# %%
SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = index + ["访视日期"]).rename(columns={"访视日期":"评估日期"})
df = SV.sort_values(by = ["受试者", "访视名称", "页面名称", "评估日期"])
df = df.drop_duplicates()
df = df[(df["受试者状态"] != "筛选失败")]
df["类别"] = "其他指标超窗"

RAND = load_rand(cols=['受试者', '随机日期'])

df = (df.merge(TW, left_on = ["类别", "访视名称"], right_on = ["类别", "访视名称"], how = "left")
        .merge(RAND, on = "受试者", how = "left"))

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
# ## 重算：疗效评价指标超窗 -> efficacy_table

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
        .merge(RAND, on = "受试者", how = "left"))

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

efficacy_table = df.copy()

# %% [markdown]
# ## 重算：安全性评价指标超窗 -> safe_table

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
        .merge(RAND, on = "受试者", how = "left"))

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

visit_drop = visit_table[["受试者", "访视名称", "超窗", "评估日期"]].rename(columns = {"超窗":"访视超窗", "评估日期":"访视日期"})
df = df.merge(visit_drop, on = ["受试者", "访视名称"], how = "left")
df = df[(df["访视超窗"].isna()) | (df["访视日期"] != df["评估日期"])]

safe_table = df.copy()

# %% [markdown]
# ## 重算：其他指标超窗 -> oth_table

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
        .merge(RAND, on = "受试者", how = "left"))

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

visit_drop = visit_table[["受试者", "访视名称", "超窗", "评估日期"]].rename(columns = {"超窗":"访视超窗", "评估日期":"访视日期"})
df = df.merge(visit_drop, on = ["受试者", "访视名称"], how = "left")
df = df[(df["访视超窗"].isna()) | (df["访视日期"] != df["评估日期"])]

oth_table = df.copy()

# %% [markdown]
# ## 表格：超窗情况汇总

# %%
df = pd.concat([efficacy_table, safe_table, oth_table, visit_table])

df["超窗时间（天）"] = np.where(
    df["评估日期"] > df["上限"],
    (df["评估日期"] - df["上限"]).dt.days,
    (df["下限"] - df["评估日期"]).dt.days
)

page_stats = df.groupby(["类别", "页面名称"]).agg(
    例次=("受试者", "count"),           # 总记录数
    例数=("受试者", "nunique"),         # 去重后的受试者数
    最小超窗时间=("超窗时间（天）", "min"),  # 最小超窗时间
    最大超窗时间=("超窗时间（天）", "max")   # 最大超窗时间
).reset_index()

# 步骤2：计算每个类别的汇总数据
category_stats = df.groupby("类别").agg(
    例次=("受试者", "count"),
    例数=("受试者", "nunique"),
    最小超窗时间=("超窗时间（天）", "min"),
    最大超窗时间=("超窗时间（天）", "max")
).reset_index()

# 为类别汇总行添加空的页面名称列
category_stats["页面名称"] = ""
category_page_order = {
    "疗效评价指标超窗": ["SAPS量表", "疾病严重程度量表（CGI-S）", "总体进步量表（CGI-I）", "MDS统一帕金森病评定量表（MDS-UPDRS）"],
    "安全性评价指标超窗": ["生命体征", "体格检查", "血常规", "肝功能", "肾功能", "电解质", "空腹血糖", "尿常规", "血妊娠", "尿妊娠", "12导联心电图"],
    "其他指标超窗": ["体重", "访视日期", "身高体重", "神经精神量表（NPI）", "哥伦比亚-自杀严重程度评定量表（C-SSRS）", "简易精神状态检查量表（MMSE）", "试验药物发放记录", "试验药物回收记录"]
}
result_rows = []

for category, page_list in category_page_order.items():
    # 检查该类别是否存在
    if category not in category_stats["类别"].values:
        continue

    # 添加类别汇总行
    category_row = category_stats[category_stats["类别"] == category].iloc[0]
    result_rows.append({
        "未遵循研究方案时间窗子类别": category_row["类别"],
        "例次": category_row["例次"],
        "例数": category_row["例数"],
        "最小超窗时间（天）": category_row["最小超窗时间"],
        "最大超窗时间（天）": category_row["最大超窗时间"],
        "层级": "类别"
    })

    # 按照指定顺序添加页面行
    pages = page_stats[page_stats["类别"] == category]
    for page_name in page_list:
        page_row = pages[pages["页面名称"] == page_name]
        if len(page_row) > 0:
            page_row = page_row.iloc[0]
            result_rows.append({
                "未遵循研究方案时间窗子类别": f"        {page_row['页面名称']}",
                "例次": page_row["例次"],
                "例数": page_row["例数"],
                "最小超窗时间（天）": page_row["最小超窗时间"],
                "最大超窗时间（天）": page_row["最大超窗时间"],
                "层级": "页面"
            })

# %%
df = pd.DataFrame(result_rows)
df = df[["未遵循研究方案时间窗子类别", "例次", "例数", "最小超窗时间（天）", "最大超窗时间（天）"]]
df["最小超窗时间（天）"] = df["最小超窗时间（天）"].astype("Int32")
df["最大超窗时间（天）"] = df["最大超窗时间（天）"].astype("Int32")
notes = []
save_table_to_docx_threeline(
        df,
        f'{output_path}/table/表18 超窗情况汇总.docx',
        f'表18 超窗情况汇总',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
        alignment = WD_TABLE_ALIGNMENT.LEFT
    )
