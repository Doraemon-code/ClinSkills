# %%
# %run ../../env.py

# %% [markdown]
# ## 表格： 医学编码情况

# %%
# MedDRA汇总
cols = ["Page", "Subject"]
code1 = pd.read_excel(code_path, sheet_name = "MedDRA", usecols = cols, dtype=str)
n1 =len(code1)
code1 = code1.groupby(["Page"]).agg(
    编码数量=("Subject", "size"),
    例数=("Subject", "nunique"),
    例次=("Subject", "size"),
)
code1 = code1.reset_index()
code1["编码字典"] = "MedDRA28.1"
code1 = code1.rename(columns = {
    "Page":"编码数据（表单名称）"
})

# %%
# WHODrug汇总
cols = ["Page", "Subject"]
code2 = pd.read_excel(code_path, sheet_name = "WHODrug", usecols = cols, dtype=str)
n2 = len(code2)
code2 = code2.groupby(["Page"]).agg(
    编码数量=("Subject", "size"),
    例数=("Subject", "nunique"),
    例次=("Subject", "size"),
)
code2 = code2.reset_index()
code2["编码字典"] = "WHODrug Global Chinese B3/C3-format September 1, 2025"
code2 = code2.rename(columns = {
    "Page":"编码数据（表单名称）"
})

# %%
code =pd.concat([code1, code2])
code = code[["编码数据（表单名称）", "编码字典", "编码数量", "例次", "例数"]]

order = ["既往史及现病史", "过敏史", "不良事件", "既往/合并用药", "既往/合并非药物治疗"]
code['编码数据（表单名称）'] = pd.Categorical(code['编码数据（表单名称）'], categories=order, ordered=True)
code = code.sort_values("编码数据（表单名称）").reset_index(drop=True)

notes = [
    f"本试验医学编码总条目数为{n1+n2}条"
]
save_table_to_docx_threeline(
        code,
        f'{output_path}/table/表30 医学编码情况.docx',
        f'表30 医学编码情况',
        notes,
        row_height_cm=0.6,
        auto_width=False,
        include_notes=True,
        alignment = WD_TABLE_ALIGNMENT.CENTER
    )
