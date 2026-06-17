# %%
# %run ../../env.py
from utils.loaders import load_rand

# %% [markdown]
# # 用药依从性汇总
# #### 注：本表依赖"用药依从性违背清单(表26)"产出的 df，拆分后在本文件内重算得到该 df（不重复导出表26）

# %%
# ===== 重算表26：用药依从性违背清单的 df =====
# 实际单个受试者总用药量
index = ["受试者"]
cols = ["日服药剂量_TXT", "其他剂量"]
EC = pd.read_excel(raw_path, sheet_name = "EC", header = 0, skiprows = [1], usecols = index + cols)
EC["日服药剂量"] = np.where(
    EC["其他剂量"].notna(),
    EC["其他剂量"],
    EC["日服药剂量_TXT"]
)

prx = "\d"
EC["实际日服药剂量"] = EC["日服药剂量"].str.extract(r"(\d+)").astype("Int32")
EC = EC[EC["实际日服药剂量"].notna()].drop(columns = cols + ["日服药剂量"])
EC = EC.groupby(index).agg(
    实际总服药量 = ("实际日服药剂量", "sum")
).reset_index()

# 通过计算首末次服药日期来计算治疗天数
cols = ["受试者", "服药日期"]
EC1 = pd.read_excel(raw_path, sheet_name = "EC", header = 0, skiprows = [1], usecols = cols, dtype = str).fillna("")
EC1["服药日期"] = pd.to_datetime(EC1["服药日期"], errors="coerce")

EC1 = (
    EC1.groupby("受试者", dropna=False)["服药日期"]
      .agg(["min", "max"])
      .rename(columns={"min": "首次用药日期", "max": "末次用药日期"})
).reset_index()

# 随机日期
RAND = load_rand(cols=['受试者', '随机日期', '随机号'])

# 是否完成治疗
cols = ["受试者", "页面名称", "是否提前终止治疗_TXT", "提前终止治疗原因_TXT"]
DS_END = pd.read_excel(raw_path, sheet_name = "DS_END", header = 0, skiprows = [1], usecols = cols)
DS_END = DS_END[(DS_END["页面名称"] == "治疗结束页")].drop(columns = "页面名称")

# 是否完成试验
cols = ["受试者", "页面名称", "是否完成试验_TXT"]
DS_END1 = pd.read_excel(raw_path, sheet_name = "DS_END", header = 0, skiprows = [1], usecols = cols)
DS_END1 = DS_END1[DS_END1["页面名称"] == "试验完成情况总结"]

# 访视5日期
cols = ["受试者", "访视名称", "访视日期"]
SV = pd.read_excel(raw_path, sheet_name = "SV", header = 0, skiprows = [1], usecols = cols)
SV = SV[SV["访视名称"] == "访视5（V5，D43±3）"].drop(columns = "访视名称").rename(columns = {"访视日期":"访视5日期"})

# 理论访视5日期
cols = ["受试者编号", "页面", "备注内容"]
SV_plan = pd.read_excel(remark_path, sheet_name = "备注清单", header = 4, usecols = cols)
SV_plan = SV_plan[SV_plan["页面"] == "治疗结束页"].drop(columns = "页面")
SV_plan[["日期类型", "日期"]] = SV_plan["备注内容"].str.split("是", expand=True)
SV_plan["日期"] = pd.to_datetime(SV_plan["日期"], format="%Y年%m月%d日")
SV_plan = SV_plan.pivot(index = "受试者编号", columns = "日期类型", values = "日期").reset_index()
SV_plan = SV_plan.rename(columns = {"受试者编号":"受试者"})


df = (EC.merge(RAND, on = "受试者", how = "left")
         .merge(DS_END, on = "受试者", how = "left")
         .merge(SV, on = "受试者", how = "left")
         .merge(SV_plan, on = "受试者", how = "left")
         .merge(EC1, on = "受试者", how = "left")
         .merge(DS_END1, on = "受试者", how = "left")
      )

df['随机日期'] = pd.to_datetime(df['随机日期'])
df['访视5日期'] = pd.to_datetime(df['访视5日期'], errors='coerce')
df['理论V5日期'] = pd.to_datetime(df['理论V5日期'])
df['退出日期'] = pd.to_datetime(df['退出日期'], errors='coerce')

def calculate_end_date(row):
    if pd.notna(row['访视5日期']):
        return row['访视5日期'] - pd.Timedelta(days=1)
    elif pd.notna(row['理论V5日期']):
        return row['理论V5日期'] - pd.Timedelta(days=1)
    elif pd.notna(row['退出日期']):
        return row['退出日期'] - pd.Timedelta(days=1)
    else:
        return None

df['末次应服药日期'] = df.apply(calculate_end_date, axis=1)
df["应用药量"] = (df["末次应服药日期"] - df["随机日期"]).dt.days + 1
df["用药依从性（%）"] = ((df["实际总服药量"] / df["应用药量"]) * 100).round(1).astype(str) + '%'

df.columns = [col.replace("_TXT", "") for col in df.columns]
df = df.rename(columns = {
    "受试者":"筛选号",
    "实际总服药量":"实际用药量（粒）",
    "应用药量":"应用药量（粒）",
})

stand_cols = [
    "筛选号",
    "随机号",
    "首次用药日期",
    "末次用药日期",
    "实际用药量（粒）",
    "应用药量（粒）",
    "用药依从性（%）",
    "是否提前终止治疗",
    "提前终止治疗原因",
    "是否完成试验",
     ]
df = df[stand_cols]

df["首次用药日期"] = df["首次用药日期"].dt.strftime('%Y-%m-%d')
df["末次用药日期"] = df["末次用药日期"].dt.strftime('%Y-%m-%d')

df.insert(0, "No.", range(1, len(df) + 1))

# %%
# 受试者状态
RAND = load_rand(cols=['受试者', '受试者状态'])

df_summary = df.merge(RAND, left_on = "筛选号", right_on = "受试者", how = "left")
df_summary = df_summary[cols + ["用药依从性（%）"]]

df_summary["用药依从性（%）"] = df_summary["用药依从性（%）"].str.replace('%', '').astype(float)
# 计算用药依从性区间
def categorize_adherence(x):
    if pd.isna(x):
        return '未知'
    elif x < 80:
        return '依从性<80%'
    elif 80 <= x <= 120:
        return '依从性80%-120%'
    else:
        return '依从性>120%'

# 应用该分类规则
df_summary['依从性区间'] = df_summary['用药依从性（%）'].apply(categorize_adherence)
all_adherence_categories = ['依从性<80%', '依从性80%-120%', '依从性>120%', "依从性未知"]
all_statuses = df_summary['受试者状态'].unique()

# 按受试者状态和依从性区间分组，计算每组的数量
df_summary = df_summary.groupby(['受试者状态', '依从性区间']).size().unstack(fill_value=0)
df_summary = df_summary.reindex(columns=all_adherence_categories, fill_value=0).reset_index()
df_summary["受试者状态"] = df_summary["受试者状态"].replace("中止退出", "提前退出")
df_summary = df_summary.sort_values(by="受试者状态", ascending=True)

df_summary.insert(0, "No.", range(1, len(df_summary) + 1))
export_to_excel_with_format(
    df_summary,
    f"{output_path}/listing/表25 用药依从性汇总清单.xlsx",
    "表25 用药依从性汇总清单",
    f"表25 用药依从性汇总清单"
)
