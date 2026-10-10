"""
combineTernary.py

Builds a ternary plot dataset from three raw GOS XLSX files:
  - GOS_SAL_UG_ALL_AREA_E315 .xlsx   -> median salary (Total 2025)
  - GOS_EMP_UG_ALL_AREA.xlsx         -> full-time employment rate (FTE 2025)
  - GOS_SP0QSCL_ALL_AREA.xlsx        -> overqualification rate (Overall employed 2025)

Measures are each min-max normalised to their own observed range, then
renormalised so the three sum to 1 (ternary weights), then mapped to
2D triangle coordinates.

Triangle vertices:
  Bottom-left  = 100% FTE      (0, 0)
  Bottom-right = 100% NotOver  (1, 0)
  Top          = 100% Salary   (0.5, sqrt(3)/2)

Overqualification is reversed (NotOver = 100 - Overqualified) so that
all three axes read "higher = better".

Output: processedData/ternary_data.csv
"""

import numpy as np
import pandas as pd

INPUT_DIR  = "Data"
OUTPUT_DIR = "processedData"

# ---------------------------------------------------------------
# Load raw XLSX files (header is on row index 1 for all three)
# ---------------------------------------------------------------
sal = pd.read_excel(f"{INPUT_DIR}/GOS_SAL_UG_ALL_AREA_E315 .xlsx", header=1)
emp = pd.read_excel(f"{INPUT_DIR}/GOS_EMP_UG_ALL_AREA.xlsx",           header=1)
oq  = pd.read_excel(f"{INPUT_DIR}/GOS_SP0QSCL_ALL_AREA.xlsx",          header=1)

# ---------------------------------------------------------------
# Extract (study_area, value) by POSITION to avoid duplicate
# header names in the salary file ("Total 2022" appears twice).
# ---------------------------------------------------------------
# Salary file: col 0 = study area, col 13 = "Total 2025"
sal_df = sal.iloc[:, [0, 13]].copy()
sal_df.columns = ["study_area", "Salary"]

# Employment file: col 0 = study area, col 1 = "Full-time employment 2025"
emp_df = emp.iloc[:, [0, 1]].copy()
emp_df.columns = ["study_area", "FTE"]

# Overqualification file: col 0 = study area, col 2 = "Overall employed"
oq_df = oq.iloc[:, [0, 2]].copy()
oq_df.columns = ["study_area", "Overqualified"]

# ---------------------------------------------------------------
# Clean
# ---------------------------------------------------------------
DROP_LABELS = {"total", "standard deviation", "nan", ""}

def clean(df, value_col):
    df = df.copy()
    df["study_area"] = df["study_area"].astype(str).str.strip()
    df = df[~df["study_area"].str.lower().isin(DROP_LABELS)]
    # Strip commas from numbers like "75,000"
    df[value_col] = (
        df[value_col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace({"n/a": None, "nan": None, "": None})
    )
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[value_col])
    return df.reset_index(drop=True)

sal_df = clean(sal_df, "Salary")
emp_df = clean(emp_df, "FTE")
oq_df  = clean(oq_df,  "Overqualified")

# ---------------------------------------------------------------
# Merge into one wide table
# ---------------------------------------------------------------
df = sal_df.merge(emp_df, on="study_area", how="inner").merge(
    oq_df, on="study_area", how="inner"
)

# Reverse overqualification polarity: high NotOver = good
df["NotOver"] = 100 - df["Overqualified"]

# ---------------------------------------------------------------
# Min-max normalise each measure to its own observed range
# ---------------------------------------------------------------
def norm(s):
    return (s - s.min()) / (s.max() - s.min())

df["nSalary"]  = norm(df["Salary"])
df["nFTE"]     = norm(df["FTE"])
df["nNotOver"] = norm(df["NotOver"])

# ---------------------------------------------------------------
# Renormalise so the three components sum to 1
# ---------------------------------------------------------------
df["total"]    = df["nSalary"] + df["nFTE"] + df["nNotOver"]
df["sSalary"]  = df["nSalary"]  / df["total"]
df["sFTE"]     = df["nFTE"]     / df["total"]
df["sNotOver"] = df["nNotOver"] / df["total"]

# ---------------------------------------------------------------
# Ternary coordinates
# ---------------------------------------------------------------
df["tx"] = 0.5 * df["sSalary"] + df["sNotOver"]
df["ty"] = (np.sqrt(3) / 2) * df["sSalary"]

# ---------------------------------------------------------------
# Round + save
# ---------------------------------------------------------------
out = df[[
    "study_area",
    "Salary", "FTE", "Overqualified", "NotOver",
    "sSalary", "sFTE", "sNotOver",
    "tx", "ty",
]].round(4)

out.to_csv(f"{OUTPUT_DIR}/ternary_data.csv", index=False)

# ---------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------
print(f"Wrote {len(out)} rows to {OUTPUT_DIR}/ternary_data.csv\n")
print(out.to_string(index=False))

print("\nRanges used for scaling (each axis scaled to its own min/max):")
print(f"  Salary:  ${df.Salary.min():>8,.0f}  ->  ${df.Salary.max():>8,.0f}")
print(f"  FTE:     {df.FTE.min():>7.1f}%  ->  {df.FTE.max():>7.1f}%")
print(f"  NotOver: {df.NotOver.min():>7.1f}%  ->  {df.NotOver.max():>7.1f}%")