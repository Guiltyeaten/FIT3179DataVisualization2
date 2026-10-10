"""
combineScatter.py
Builds salary_vs_fte_timeseries.csv: one row per (study_area, year)
with both median_salary AND fte, ready for a connected scatter plot.
"""

import pandas as pd

sal = pd.read_csv("processedData/salary_by_area.csv")
emp = pd.read_csv("processedData/employment_by_area.csv")

# Salary: UG, broad, Total only, all years
sal_ts = sal[
    (sal.course_level == "UG") &
    (sal.study_area_level == "broad") &
    (sal.gender == "Total")
][["study_area", "year", "median_salary"]].copy()

# FTE: UG only, all years
fte_ts = emp[
    (emp.course_level == "UG") &
    (emp.measure == "FTE")
][["study_area", "year", "value"]].rename(columns={"value": "fte"}).copy()

# Join on (study_area, year)
ts = sal_ts.merge(fte_ts, on=["study_area", "year"], how="inner")
ts = ts.sort_values(["study_area", "year"]).reset_index(drop=True)

ts.to_csv("processedData/salary_vs_fte_timeseries.csv", index=False)
print(f"Wrote {len(ts)} rows to processedData/salary_vs_fte_timeseries.csv")
print(ts.head(12).to_string(index=False))