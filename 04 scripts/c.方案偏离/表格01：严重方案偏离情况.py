# %%
# %run ../../env.py
from utils.loaders import load_completion
from utils.loaders import load_rand

# %% [markdown]
# ## 表14 严重方案偏离情况 （XXX例次XXX例）

# %%
PD = pd.read_excel(pd_path, sheet_name = "方案偏离", usecols = ["中心编号", "筛选号", "严重程度", "分类", "详述"], header = 4, dtype = str)
PD = PD[PD["严重程度"] == "严重方案偏离(Major PD)"]
RAND = load_rand(cols=['受试者', '随机号', '随机日期'])
DS_END = load_completion()

df = (PD.merge(RAND, left_on = "筛选号", right_on = "受试者", how = "left")
       .merge(DS_END, left_on = "筛选号", right_on = "受试者", how = "left"))

df = df.rename(columns = {
    "是否完成试验_TXT":"是否完成试验"
})

df =df[["中心编号", "筛选号", "随机号", "随机日期", "是否完成试验", "分类", "详述"]]
df.insert(0, "No.", range(1, len(df) + 1))

lc = len(df)
ls = len(df.drop_duplicates(subset = ["筛选号"]))

# 注：原脚本此处依赖上一张表残留的 notes 变量，拆分后在本文件补充定义
notes = []
save_table_to_docx_threeline(
        df,
        f'{output_path}/table/表14 严重方案偏离情况.docx',
        f'表14 严重方案偏离情况 （{lc}例次{ls}例）',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False
    )
