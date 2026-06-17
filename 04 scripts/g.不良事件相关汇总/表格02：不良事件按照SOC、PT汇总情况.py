# %%
# %run ../../env.py

# %% [markdown]
# ## 表格： 不良事件按照SOC、PT汇总情况

# %%
cols = ["Page", "SOCTerm", "PTTerm", "Subject"]
code = pd.read_excel(code_path, sheet_name = "MedDRA", usecols = cols, dtype=str)
code = code[code["Page"] == "不良事件"]
code = code[cols].sort_values(by = cols).drop(columns = "Page")

code = code.groupby(["SOCTerm", "PTTerm"]).agg(
    例数=("Subject", "nunique"),
    例次=("Subject", "size")
)

code = code.reset_index().rename(columns = {
    "SOCTerm":"SOC",
    "PTTerm":"PT"
})

notes = []

save_table_to_docx_threeline(
        code,
        f'{output_path}/table/表29 不良事件按照SOC、PT汇总情况.docx',
        '表29 不良事件按照SOC、PT汇总情况',
        notes,
        row_height_cm=0.6,
        auto_width=True,
        include_notes=False,
        merge_columns=["SOC"],
        alignment = WD_TABLE_ALIGNMENT.CENTER
    )
