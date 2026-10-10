"""
ABS_data_converter.py
=====================
Extract useful long-format CSVs from the two ABS Personal Income in Australia
Excel files (Table 1 and Table 3).

Reads Excel from  : Data/             (this script's folder)
Writes CSV to     : ../processedData/ (sibling of Data/)

Outputs:
    abs_sa4_salary_timeseries.csv    SA4 × year × metric (earners, median, mean)
    abs_sa4_inequality_2023.csv      SA4 × 2022-23 distribution metrics
    abs_gccsa_salary_timeseries.csv  GCCSA × year × metric
    abs_gccsa_inequality_2023.csv    GCCSA × 2022-23 distribution metrics
    abs_sa4_wide_2023.csv            One row per SA4, one column per metric
    abs_sa4_median_by_year.csv       One row per SA4, one column per year

Requirements: pip install pandas openpyxl
"""

import re
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent          # .../FIT3179DataVisualization2/Data
REPO_DIR = DATA_DIR.parent                          # .../FIT3179DataVisualization2
OUT_DIR  = REPO_DIR / "processedData"
OUT_DIR.mkdir(exist_ok=True)

def find_excel(keyword: str) -> Path:
    matches = [p for p in DATA_DIR.glob("*.xls*") if keyword.lower() in p.name.lower()]
    if not matches:
        listing = [p.name for p in DATA_DIR.glob("*.xls*")]
        raise FileNotFoundError(
            f"No Excel file containing '{keyword}' found in {DATA_DIR}.\n"
            f"Files present: {listing}"
        )
    if len(matches) > 1:
        print(f"WARNING: multiple matches for '{keyword}': {[m.name for m in matches]}")
    return matches[0]

TABLE1_FILE = find_excel("Table 1")
TABLE3_FILE = find_excel("Table 3")
print(f"Table 1 -> {TABLE1_FILE.name}")
print(f"Table 3 -> {TABLE3_FILE.name}")
print(f"Output   -> {OUT_DIR}\n")

YEARS = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_number(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if s in {"np", "-", ""}:
        return np.nan
    s = s.replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def is_sa4(code):
    return bool(re.fullmatch(r"\d{3}", str(code).strip()))


def is_gccsa(code):
    return bool(re.fullmatch(r"\d[A-Z]{3,}", str(code).strip()))


# ---------------------------------------------------------------------------
# Table 1 — time series
# ---------------------------------------------------------------------------
def extract_table1(sheet_name, kind, out_filename):
    print(f"[Table 1] reading {sheet_name}")
    raw = pd.read_excel(TABLE1_FILE, sheet_name=sheet_name, header=None)

    data = raw.iloc[7:].copy()
    data.columns = range(data.shape[1])
    data = data.rename(columns={0: "code", 1: "name"})

    metric_cols = {
        "earners":    list(range(2, 7)),
        "median_age": list(range(7, 12)),
        "sum":        list(range(12, 17)),
        "median":     list(range(17, 22)),
        "mean":       list(range(22, 27)),
    }

    records = []
    for _, row in data.iterrows():
        code = row["code"]
        if kind == "sa4" and not is_sa4(code):
            continue
        if kind == "gccsa" and not is_gccsa(code):
            continue
        for metric, cols in metric_cols.items():
            for i, year in enumerate(YEARS):
                records.append({
                    "code": str(code).strip(),
                    "name": str(row["name"]).strip(),
                    "year": year,
                    "metric": metric,
                    "value": clean_number(row[cols[i]]),
                })

    out = pd.DataFrame(records)
    path = OUT_DIR / out_filename
    out.to_csv(path, index=False)
    print(f"           -> {path.name}  ({len(out):,} rows)")
    return out


# ---------------------------------------------------------------------------
# Table 3 — 2022-23 distribution
# ---------------------------------------------------------------------------
def extract_table3(sheet_name, kind, out_filename):
    print(f"[Table 3] reading {sheet_name}")
    raw = pd.read_excel(TABLE3_FILE, sheet_name=sheet_name, header=None)

    data = raw.iloc[9:].copy()
    data.columns = range(data.shape[1])
    data = data.rename(columns={0: "code", 1: "name"})

    col_map = {
        "earners":           2,
        "median_age":        3,
        "sum":               4,
        "median":            5,
        "mean":              6,
        "p80_p20":           7,
        "p80_p50":           8,
        "p20_p50":           9,
        "p10_p50":          10,
        "gini":             11,
        "top_1pct_share":   12,
        "top_5pct_share":   13,
        "top_10pct_share":  14,
        "lowest_quartile":  15,
        "second_quartile":  16,
        "third_quartile":   17,
        "highest_quartile": 18,
    }

    records = []
    for _, row in data.iterrows():
        code = row["code"]
        if kind == "sa4" and not is_sa4(code):
            continue
        if kind == "gccsa" and not is_gccsa(code):
            continue
        for metric, col in col_map.items():
            records.append({
                "code": str(code).strip(),
                "name": str(row["name"]).strip(),
                "year": "2022-23",
                "metric": metric,
                "value": clean_number(row[col]),
            })

    out = pd.DataFrame(records)
    path = OUT_DIR / out_filename
    out.to_csv(path, index=False)
    print(f"           -> {path.name}  ({len(out):,} rows)")
    return out


# ---------------------------------------------------------------------------
# Convenience wide files
# ---------------------------------------------------------------------------
def wide_sa4_median_2023(sa4_long):
    latest = sa4_long[sa4_long["year"] == "2022-23"]
    wide = latest.pivot_table(
        index=["code", "name"], columns="metric", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    path = OUT_DIR / "abs_sa4_wide_2023.csv"
    wide.to_csv(path, index=False)
    print(f"[wide]    -> {path.name}  ({len(wide)} rows)")
    return wide


def median_by_sa4_by_year(sa4_long):
    med = sa4_long[sa4_long["metric"] == "median"]
    wide = med.pivot_table(
        index=["code", "name"], columns="year", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    path = OUT_DIR / "abs_sa4_median_by_year.csv"
    wide.to_csv(path, index=False)
    print(f"[wide]    -> {path.name}  ({len(wide)} rows)")
    return wide


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sa4_salary = extract_table1("Table 1.2", "sa4", "abs_sa4_salary_timeseries.csv")
    sa4_ineq   = extract_table3("Table 3.2", "sa4", "abs_sa4_inequality_2023.csv")

    extract_table1("Table 1.1", "gccsa", "abs_gccsa_salary_timeseries.csv")
    extract_table3("Table 3.1", "gccsa", "abs_gccsa_inequality_2023.csv")

    wide_sa4_median_2023(sa4_salary)
    median_by_sa4_by_year(sa4_salary)

    print(f"\nAll done. Files written to: {OUT_DIR}")