"""
convert_gos_to_long.py  (fixed, position-based)

Reads the GOS XLSX extracts with an explicit header row per file,
accesses columns by position, and writes tidy long-format CSVs.
"""

import os
import re
import traceback
import pandas as pd

INPUT_DIR = "Data"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------

def clean_number(x):
    """'77,000 (76,600, 77,400)' -> (77000, 76600, 77400)
       '80.3' -> (80.3, None, None)
       'n/a' -> (None, None, None)"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return (None, None, None)
    s = str(x).strip()
    if s.lower() in ("n/a", "", "na", "-", "nan"):
        return (None, None, None)
    m = re.match(r"^([\d,\.]+)\s*(?:\(([\d,\.]+)\s*,\s*([\d,\.]+)\))?", s)
    if not m:
        return (None, None, None)
    def to_num(v):
        if v is None:
            return None
        v = v.replace(",", "").strip()
        try:
            return float(v)
        except ValueError:
            return None
    return (to_num(m.group(1)), to_num(m.group(2)), to_num(m.group(3)))


def to_year(v):
    """Return 4-digit year from header cell, else None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        y = int(v)
        return y if 2015 <= y <= 2030 else None
    except (ValueError, TypeError):
        pass
    m = re.match(r"^(\d{4})(\.0)?$", str(v).strip())
    if m:
        y = int(m.group(1))
        return y if 2015 <= y <= 2030 else None
    return None


def gender_year_of(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    m = re.match(r"^(Male|Female|Total)\s+(\d{4})$", str(v).strip())
    if m:
        return m.group(1), int(m.group(2))
    return None


def measure_year_of(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    m = re.match(r"^(.+?)\s+(\d{4})$", str(v).strip())
    if m:
        return m.group(1).strip(), int(m.group(2))
    return None


# ---------------------------------------------------------------
# Generic reader
# ---------------------------------------------------------------

def load_sheet(path, header_row):
    """Read the sheet, use row `header_row` as header, keep every column.
    Returns (header_list, DataFrame with columns renamed c0, c1, ...)."""
    raw = pd.read_excel(path, header=None)
    if header_row >= len(raw):
        raise ValueError(f"header_row={header_row} beyond end of {path}")
    header = raw.iloc[header_row].tolist()
    data = raw.iloc[header_row + 1:].reset_index(drop=True)
    data.columns = [f"c{i}" for i in range(data.shape[1])]
    return header, data


def write_csv(df, name):
    if df is None or len(df) == 0:
        print(f"  [WARN] {name}: 0 rows, not written")
        return
    path = os.path.join(OUTPUT_DIR, name)
    df.to_csv(path, index=False)
    print(f"  [OK]   {name}: {len(df)} rows -> {path}")


# ---------------------------------------------------------------
# Converters
# ---------------------------------------------------------------

def convert_salary_area(path, course_level, level, header_row=1, area_col=0):
    header, data = load_sheet(path, header_row)
    col_specs = []
    for i, v in enumerate(header):
        if i == area_col:
            continue
        gy = gender_year_of(v)
        if gy:
            col_specs.append((i, gy[0], gy[1]))
    print(f"    header row {header_row}: {len(col_specs)} gender/year columns")

    records = []
    for _, row in data.iterrows():
        area = row[f"c{area_col}"]
        if not isinstance(area, str):
            continue
        area = area.strip()
        if area.lower() in ("total", "standard deviation", "nan", ""):
            continue
        for i, gender, year in col_specs:
            value, _, _ = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "course_level": course_level,
                "study_area": area,
                "study_area_level": level,
                "gender": gender,
                "median_salary": value,
            })
    return pd.DataFrame(records)


def convert_employment(path, course_level, header_row=1, area_col=0):
    header, data = load_sheet(path, header_row)
    measure_map = {
        "Full-time employment": "FTE",
        "Overall employment": "OE",
        "Labour force participation rate": "LF",
    }
    col_specs = []
    for i, v in enumerate(header):
        if i == area_col:
            continue
        my = measure_year_of(v)
        if my and my[0] in measure_map:
            col_specs.append((i, measure_map[my[0]], my[1]))
    print(f"    header row {header_row}: {len(col_specs)} measure/year columns")

    records = []
    for _, row in data.iterrows():
        area = row[f"c{area_col}"]
        if not isinstance(area, str):
            continue
        area = area.strip()
        if area.lower() in ("total", "standard deviation", "nan", ""):
            continue
        for i, measure, year in col_specs:
            value, _, _ = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "course_level": course_level,
                "study_area": area,
                "measure": measure,
                "value": value,
                "unit": "percent",
            })
    return pd.DataFrame(records)


def convert_further_study(path, header_row=1, area_col=1, year_col=8):
    header, data = load_sheet(path, header_row)
    print(f"    header row {header_row}, area col {area_col}")

    gender_cols = []
    for i, v in enumerate(header):
        m = re.match(r"^In full-time study\s*[–-]\s*(Male|Female|Total)$",
                     str(v).strip())
        if m:
            gender_cols.append((i, m.group(1)))
    print(f"    gender columns: {[g for _, g in gender_cols]}")

    records = []
    for _, row in data.iterrows():
        area = row[f"c{area_col}"]
        if not isinstance(area, str):
            continue
        area = area.strip()
        if area.lower() in ("total", "nan", ""):
            continue
        year = 2025
        yv, _, _ = clean_number(row[f"c{year_col}"])
        if yv:
            year = int(yv)
        for i, gender in gender_cols:
            value, _, _ = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "study_area": area,
                "gender": gender,
                "further_study_rate": value,
            })
    return pd.DataFrame(records)


def convert_overqualification(path, header_row=1, area_col=0):
    header, data = load_sheet(path, header_row)
    print(f"    header row {header_row}: {header}")

    # locate columns by header text
    col_map = {}
    for i, v in enumerate(header):
        if i == area_col:
            continue
        key = str(v).strip() if v is not None else ""
        if key == "Employed full-time":
            col_map[i] = "FTE_overqualified"
        elif key == "Overall employed":
            col_map[i] = "Overall_overqualified"
        elif key == "Year":
            col_map[i] = "year"

    records = []
    for _, row in data.iterrows():
        area = row[f"c{area_col}"]
        if not isinstance(area, str):
            continue
        area = area.strip()
        if area.lower() in ("total", "nan", ""):
            continue
        year = 2025
        for i, name in col_map.items():
            if name == "year":
                yv, _, _ = clean_number(row[f"c{i}"])
                if yv:
                    year = int(yv)
                continue
            value, _, _ = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "study_area": area,
                "measure": name,
                "value": value,
            })
    return pd.DataFrame(records)


def convert_institution(path, metric, course_level, header_row=1, area_col=0):
    header, data = load_sheet(path, header_row)
    year_cols = []
    for i, v in enumerate(header):
        if i == area_col:
            continue
        y = to_year(v)
        if y:
            year_cols.append((i, y))
    print(f"    header row {header_row}: {len(year_cols)} year columns: "
          f"{[y for _, y in year_cols]}")

    records = []
    for _, row in data.iterrows():
        inst = row[f"c{area_col}"]
        if not isinstance(inst, str):
            continue
        inst = inst.strip()
        if inst.lower() in ("total", "standard deviation", "nan",
                            "all universities", ""):
            continue
        for i, year in year_cols:
            value, low, high = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "course_level": course_level,
                "institution": inst,
                "metric": metric,
                "value": value,
                "ci_low": low,
                "ci_high": high,
            })
    return pd.DataFrame(records)


def convert_international(path, course_level, header_row=1,
                          citizenship_col=0, year_start_col=2):
    header, data = load_sheet(path, header_row)
    year_cols = []
    for i in range(year_start_col, len(header)):
        y = to_year(header[i])
        if y:
            year_cols.append((i, y))
    print(f"    header row {header_row}: {len(year_cols)} year columns: "
          f"{[y for _, y in year_cols]}")

    records = []
    for _, row in data.iterrows():
        cit = row[f"c{citizenship_col}"]
        if not isinstance(cit, str):
            continue
        cit = cit.strip()
        if cit.lower() not in ("domestic", "international"):
            continue
        for i, year in year_cols:
            value, _, _ = clean_number(row[f"c{i}"])
            if value is None:
                continue
            records.append({
                "year": year,
                "course_level": course_level,
                "citizenship": cit,
                "median_salary": value,
            })
    return pd.DataFrame(records)


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

SALARY_AREA_FILES = [
    ("GOS_SAL_UG_ALL_AREA_E315 .xlsx",   "UG",  "broad"),
    ("GOS_SAL_UG_ALL_AREA45_E315.xlsx",  "UG",  "detail45"),
    ("GOS_SAL_PGC_ALL_AREA_E315.xlsx",   "PGC", "broad"),
    ("GOS_SAL_PGC_ALL_AREA45_E315.xlsx", "PGC", "detail45"),
    ("GOS_SAL_PGR_ALL_AREA.xlsx",        "PGR", "broad"),
]

EMPLOYMENT_FILES = [
    ("GOS_EMP_UG_ALL_AREA.xlsx",  "UG"),
    ("GOS_EMP_PGC_ALL_AREA.xlsx", "PGC"),
]

INSTITUTION_FILES = [
    ("GOS_SAL_UG_UNI_INST_FIG.xlsx",  "salary", "UG"),
    ("GOS_SAL_PGC_UNI_INST_FIG.xlsx", "salary", "PGC"),
    ("GOS_FTE_UG_UNI_INST_FIG.xlsx",  "fte",    "UG"),
    ("GOS_FTE_PGC_UNI_INST.xlsx",     "fte",    "PGC"),
]

INTERNATIONAL_FILES = [
    ("GOS_INTERNATIONAL_SAL_UG_ALL.xlsx",  "UG"),
    ("GOS_INTERNATIONAL_SAL_PGC_ALL.xlsx", "PGC"),
    ("GOS_INTERNATIONAL_SAL_PGR_ALL.xlsx", "PGR"),
]


def main():
    print(f"Working dir: {os.getcwd()}")
    print(f"Input dir:   {os.path.abspath(INPUT_DIR)}")
    print(f"Output dir:  {os.path.abspath(OUTPUT_DIR)}")

    if not os.path.isdir(INPUT_DIR):
        print(f"\n[ERROR] no '{INPUT_DIR}' folder here.")
        return

    all_files = sorted(os.listdir(INPUT_DIR))
    xlsx = [f for f in all_files if f.lower().endswith(".xlsx")]
    print(f"\nXLSX files found ({len(xlsx)}):")
    for f in xlsx:
        print(f"  - {f}")

    # --- salary by area ---
    print("\n=== Salary by area ===")
    parts = []
    for fname, level, gran in SALARY_AREA_FILES:
        path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {fname}")
            continue
        print(f"-> {fname}")
        try:
            parts.append(convert_salary_area(path, level, gran))
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    if parts:
        write_csv(pd.concat(parts, ignore_index=True), "salary_by_area.csv")

    # --- employment ---
    print("\n=== Employment outcomes ===")
    parts = []
    for fname, level in EMPLOYMENT_FILES:
        path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {fname}")
            continue
        print(f"-> {fname}")
        try:
            parts.append(convert_employment(path, level))
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    if parts:
        write_csv(pd.concat(parts, ignore_index=True), "employment_by_area.csv")

    # --- further study ---
    print("\n=== Further study ===")
    fts = os.path.join(INPUT_DIR, "GOS_FTS_ALL_AREA_E315.xlsx")
    if os.path.exists(fts):
        print(f"-> {os.path.basename(fts)}")
        try:
            write_csv(convert_further_study(fts), "further_study_by_area.csv")
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    else:
        print("[SKIP] GOS_FTS_ALL_AREA_E315.xlsx")

    # --- overqualification ---
    print("\n=== Overqualification ===")
    oq = os.path.join(INPUT_DIR, "GOS_SP0QSCL_ALL_AREA.xlsx")
    if os.path.exists(oq):
        print(f"-> {os.path.basename(oq)}")
        try:
            write_csv(convert_overqualification(oq), "overqualification_by_area.csv")
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    else:
        print("[SKIP] GOS_SP0QSCL_ALL_AREA.xlsx")

    # --- institution ---
    print("\n=== Institution outcomes ===")
    parts = []
    for fname, metric, level in INSTITUTION_FILES:
        path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {fname}")
            continue
        print(f"-> {fname}")
        try:
            parts.append(convert_institution(path, metric, level))
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    if parts:
        write_csv(pd.concat(parts, ignore_index=True), "institution_outcomes.csv")

    # --- international ---
    print("\n=== International salary trend ===")
    parts = []
    for fname, level in INTERNATIONAL_FILES:
        path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {fname}")
            continue
        print(f"-> {fname}")
        try:
            parts.append(convert_international(path, level))
        except Exception:
            print("  [ERROR]")
            traceback.print_exc()
    if parts:
        write_csv(pd.concat(parts, ignore_index=True), "international_trend.csv")

    print("\nDone.")


if __name__ == "__main__":
    main()