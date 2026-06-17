# %%
# %run ../../env.py

# %% [markdown]
# # 受试者实际用药天数

# %%
index = ["受试者"]
cols = ["服药日期", "本日是否服药_TXT"]
EC = pd.read_excel(raw_path, sheet_name = "EC", header = 0, skiprows = [1], usecols = index + cols)
EC = EC[EC["本日是否服药_TXT"] == "是"]

# %%
dose_days = EC.groupby(index).agg(
    用药天数=("本日是否服药_TXT", "count")
).reset_index()
dose_days

export_to_excel_with_format(
    dose_days,
    f"{output_path}/listing/受试者实际用药天数清单.xlsx",
    "受试者实际用药天数清单",
    f"受试者实际用药天数清单"
)
