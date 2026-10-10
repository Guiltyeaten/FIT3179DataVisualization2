"""
extract_abs_income.py
=====================
Extract useful long-format CSVs from the two ABS Personal Income in Australia
Excel files (Table 1 and Table 3) for a Vega-Lite data visualisation.

Outputs (written to ./Data/):
    abs_sa4_salary_timeseries.csv    SA4 × year × metric (earners, median, mean, ...)
    abs_sa4_inequality_2023.csv      SA4 × 2022-23 distribution metrics (Gini, quartiles)
    abs_gccsa_salary_timeseries.csv  GCCSA (state / capital city) × year × metric
    abs_gccsa_inequality_2023.csv    GCCSA × 2022-23 distribution metrics

Requirements:
    pip install pandas openpyxl
"""

import re
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Config — adjust the filenames if yours are slightly different
# ---------------------------------------------------------------------------
TABLE1_FILE = (
    "Table 1 - Total income, earners and summary statistics "
    "by geography, 2018-19 to 2022-23.xlsx"
)
TABLE3_FILE = "Table 3 - Total income distribution by geography, 2022-23.xlsx"
OUT_DIR = Path("output")
OUT_DIR.mkdir(exist_ok=True)

YEARS = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_number(x):
    """Turn '58,216', '58216', 'np', '' into float or NaN."""
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
    """SA4 codes are 3 digits, e.g. 101, 201, 801."""
    return bool(re.fullmatch(r"\d{3}", str(code).strip()))


def is_gccsa(code):
    """GCCSA codes look like 1GSYD, 2GMEL, 3GBRI, ..."""
    return bool(re.fullmatch(r"\d[A-Z]{3,}", str(code).strip()))


# ---------------------------------------------------------------------------
# Table 1 — time series of earners / median age / sum / median / mean
# ---------------------------------------------------------------------------
def extract_table1(sheet_name, kind, out_filename):
    """
    sheet_name: 'Table 1.1' (GCCSA) or 'Table 1.2' (SA4)
    kind:       'gccsa' or 'sa4'
    """
    print(f"[Table 1] reading {sheet_name}")
    raw = pd.read_excel(TABLE1_FILE, sheet_name=sheet_name, header=None)

    # Header row is row index 6; data starts at row index 7
    header_row = raw.iloc[6].tolist()
    data = raw.iloc[7:].copy()
    data.columns = range(data.shape[1])
    data = data.rename(columns={0: "code", 1: "name"})

    # Column groups (5 years each)
    metric_cols = {
        "earners":    list(range(2, 7)),    # C–G
        "median_age": list(range(7, 12)),   # H–L
        "sum":        list(range(12, 17)),  # M–Q
        "median":     list(range(17, 22)),  # R–V
        "mean":       list(range(22, 27)),  # W–AA
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
                records.append(
                    {
                        "code": str(code).strip(),
                        "name": str(row["name"]).strip(),
                        "year": year,
                        "metric": metric,
                        "value": clean_number(row[cols[i]]),
                    }
                )

    out = pd.DataFrame(records)
    path = OUT_DIR / out_filename
    out.to_csv(path, index=False)
    print(f"           → {path}  ({len(out):,} rows)")
    return out


# ---------------------------------------------------------------------------
# Table 3 — 2022-23 distribution (Gini, percentile ratios, income share)
# ---------------------------------------------------------------------------
def extract_table3(sheet_name, kind, out_filename):
    """
    sheet_name: 'Table 3.1' (GCCSA) or 'Table 3.2' (SA4)
    kind:       'gccsa' or 'sa4'
    """
    print(f"[Table 3] reading {sheet_name}")
    raw = pd.read_excel(TABLE3_FILE, sheet_name=sheet_name, header=None)

    # Header at row index 7; data starts at row index 9
    data = raw.iloc[9:].copy()
    data.columns = range(data.shape[1])
    data = data.rename(columns={0: "code", 1: "name"})

    col_map = {
        "earners":           2,   # C
        "median_age":        3,   # D
        "sum":               4,   # E
        "median":            5,   # F
        "mean":              6,   # G
        "p80_p20":           7,   # H
        "p80_p50":           8,   # I
        "p20_p50":           9,   # J
        "p10_p50":          10,   # K
        "gini":             11,   # L
        "top_1pct_share":   12,   # M
        "top_5pct_share":   13,   # N
        "top_10pct_share":  14,   # O
        "lowest_quartile":  15,   # P
        "second_quartile":  16,   # Q
        "third_quartile":   17,   # R
        "highest_quartile": 18,   # S
    }

    records = []
    for _, row in data.iterrows():
        code = row["code"]
        if kind == "sa4" and not is_sa4(code):
            continue
        if kind == "gccsa" and not is_gccsa(code):
            continue

        for metric, col in col_map.items():
            records.append(
                {
                    "code": str(code).strip(),
                    "name": str(row["name"]).strip(),
                    "year": "2022-23",
                    "metric": metric,
                    "value": clean_number(row[col]),
                }
            )

    out = pd.DataFrame(records)
    path = OUT_DIR / out_filename
    out.to_csv(path, index=False)
    print(f"           → {path}  ({len(out):,} rows)")
    return out


# ---------------------------------------------------------------------------
# Extras — small, wide-format files that are easy to join to your TopoJSON
# ---------------------------------------------------------------------------
def wide_sa4_median_2023(sa4_long):
    """Wide file: one row per SA4, one column per metric (2022-23 only)."""
    latest = sa4_long[sa4_long["year"] == "2022-23"]
    wide = latest.pivot_table(
        index=["code", "name"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    path = OUT_DIR / "abs_sa4_wide_2023.csv"
    wide.to_csv(path, index=False)
    print(f"[wide]    → {path}  ({len(wide)} rows)")
    return wide


def median_by_sa4_by_year(sa4_long):
    """Wide file: SA4 × year, one column per year, only the median metric."""
    med = sa4_long[sa4_long["metric"] == "median"]
    wide = med.pivot_table(
        index=["code", "name"],
        columns="year",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    path = OUT_DIR / "abs_sa4_median_by_year.csv"
    wide.to_csv(path, index=False)
    print(f"[wide]    → {path}  ({len(wide)} rows)")
    return wide


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # ---- SA4 level (use these for your choropleth + inequality maps) ----
    sa4_salary = extract_table1("Table 1.2", "sa4", "abs_sa4_salary_timeseries.csv")
    sa4_ineq   = extract_table3("Table 3.2", "sa4", "abs_sa4_inequality_2023.csv")

    # ---- GCCSA level (state / capital-city summaries) ----
    extract_table1("Table 1.1", "gccsa", "abs_gccsa_salary_timeseries.csv")
    extract_table3("Table 3.1", "gccsa", "abs_gccsa_inequality_2023.csv")

    # ---- Convenience wide files ----
    wide_sa4_median_2023(sa4_salary)
    median_by_sa4_by_year(sa4_salary)

    print("\nAll done. CSVs are in:", OUT_DIR.resolve())