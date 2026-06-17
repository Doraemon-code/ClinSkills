# %%
# %run ../../env.py

# %% [markdown]
# ## 表13 受试者层面方案偏离情况

# %%
PD = pd.read_excel(pd_path, sheet_name = "方案偏离", usecols = ["筛选号", "严重程度", "分类"], header = 4, dtype = str)
# 按"严重程度"和"分类"分组，计算例次和例数
df = PD.groupby(["严重程度", "分类"]).agg(
    例次=("筛选号", "count"),      # 每个分组内的总记录数
    例数=("筛选号", "nunique")     # 每个分组内去重后的筛选号数量
).reset_index()

# 调整列的顺序
df = df[["严重程度", "分类", "例次", "例数"]]

# 注：原脚本此处依赖上一张表残留的 notes 变量，拆分后在本文件补充定义
notes = []
save_table_to_docx_threeline(
        df,
        f'{output_path}/table/表13 受试者层面方案偏离情况.docx',
        '表13 受试者层面方案偏离情况',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
        merge_columns=['严重程度']
    )
