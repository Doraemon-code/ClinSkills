# %%
# %run ../../env.py

# %% [markdown]
# ## 表12 中心层面方案偏离情况

# %%
PD = pd.read_excel(pd_path, sheet_name = "方案偏离", usecols = ["中心编号", "筛选号", "严重程度", "分类"], header = 4, dtype = str)
PD = PD[PD["筛选号"].isna()]
df = PD.drop_duplicates()

df = df.rename(columns={"中心编号":"中心"}).fillna("")
stand_cols = ["中心", "严重程度", "分类"]

notes = []
save_table_to_docx_threeline(
        df,
        f'{output_path}/table/表12 中心层面方案偏离情况.docx',
        '表12 中心层面方案偏离情况',
        notes,
        row_height_cm=0.6,
        auto_width=True
    )
