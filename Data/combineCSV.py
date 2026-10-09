import pandas as pd

# --- scatter: salary vs FTE by broad field, UG, 2025 ---
sal = pd.read_csv("output/salary_by_area.csv")
emp = pd.read_csv("output/employment_by_area.csv")

sal25 = sal[(sal.course_level=="UG") & (sal.study_area_level=="broad")
            & (sal.gender=="Total") & (sal.year==2025)][["study_area","median_salary"]]
fte25 = emp[(emp.course_level=="UG") & (emp.measure=="FTE")
            & (emp.year==2025)][["study_area","value"]].rename(columns={"value":"fte"})
scatter = sal25.merge(fte25, on="study_area")
scatter.to_csv("output/salary_vs_fte.csv", index=False)

# --- parallel coords: min-max normalise per measure ---
sal = sal[(sal.course_level=="UG") & (sal.study_area_level=="broad")
          & (sal.gender=="Total") & (sal.year==2025)][["study_area","median_salary"]]
fts = pd.read_csv("output/further_study_by_area.csv")
fts = fts[(fts.gender=="Total") & (fts.year==2025)][["study_area","further_study_rate"]]
oq  = pd.read_csv("output/overqualification_by_area.csv")
oq  = oq[(oq.measure=="Overall_overqualified") & (oq.year==2025)][["study_area","value"]]
oq  = oq.rename(columns={"value":"overqualified"})
fte = fte25

df = sal.merge(fte, on="study_area").merge(fts, on="study_area").merge(oq, on="study_area")

def norm(s): return (s - s.min()) / (s.max() - s.min())
long = []
for col, label in [("median_salary","Salary"), ("fte","FTE"),
                   ("further_study_rate","FurtherStudy"),
                   ("overqualified","Overqualified")]:
    for _, r in df.iterrows():
        long.append({"study_area": r.study_area, "measure": label,
                     "raw": r[col], "norm": norm(df[col])[r.name]})
pd.DataFrame(long).to_csv("output/parallel_combined.csv", index=False)