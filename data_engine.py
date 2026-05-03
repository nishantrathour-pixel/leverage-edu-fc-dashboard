import random
import datetime
import calendar
import pandas as pd

# ── Constants ──────────────────────────────────────────────────────────────
CENTRES = [
    {"id": "C01", "name": "Mumbai",    "state": "Maharashtra", "area": 700},
    {"id": "C02", "name": "Delhi",     "state": "Delhi",       "area": 750},
    {"id": "C03", "name": "Bangalore", "state": "Karnataka",   "area": 600},
    {"id": "C04", "name": "Hyderabad", "state": "Telangana",   "area": 550},
    {"id": "C05", "name": "Chennai",   "state": "Tamil Nadu",  "area": 650},
    {"id": "C06", "name": "Pune",      "state": "Maharashtra", "area": 500},
]

MONTHS = [
    (4,2025,"Apr-25","Q1"),(5,2025,"May-25","Q1"),(6,2025,"Jun-25","Q1"),
    (7,2025,"Jul-25","Q2"),(8,2025,"Aug-25","Q2"),(9,2025,"Sep-25","Q2"),
    (10,2025,"Oct-25","Q3"),(11,2025,"Nov-25","Q3"),(12,2025,"Dec-25","Q3"),
    (1,2026,"Jan-26","Q4"),(2,2026,"Feb-26","Q4"),(3,2026,"Mar-26","Q4"),
]

DEFAULT_ASSUMPTIONS = {
    "ticket_size":      150000,
    "fl_pct":           0.07,
    "ff_pct":           0.02,
    "fh_pct":           0.12,
    "l1_pct":           0.60,
    "walkin_min":       10,
    "walkin_max":       12,
    "sa_rate":          0.30,
    "fl_rate":          0.40,
    "ff_rate":          0.40,
    "fh_rate":          0.40,
    "l1_rate":          0.10,
    "mgr_salary":       80000,
    "coach_salary":     45000,
    "n_coaches":        3,
    "bda_salary":       40000,
    "admin_salary":     25000,
    "rent_per_sqft":    120,
    "utilities":        15000,
    "marketing":        20000,
    "misc":             10000,
}

SERVICES = ["Study Abroad", "Fly Loans", "Fly Forex", "Fly Homes", "Leverage 1"]
SVC_COLS  = ["sa", "fl", "ff", "fh", "l1"]
REV_COLS  = ["sa_rev", "fl_rev", "ff_rev", "fh_rev", "l1_rev"]

# ── Data generation ────────────────────────────────────────────────────────
def get_workdays(month, year):
    days = []
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        dt = datetime.date(year, month, d)
        if dt.weekday() < 6:
            days.append(dt)
    return days

def generate_raw(assumptions=None):
    a = assumptions or DEFAULT_ASSUMPTIONS
    random.seed(42)
    rows = []
    for mn, yr, mlbl, qtr in MONTHS:
        for dt in get_workdays(mn, yr):
            for c in CENTRES:
                wi = random.randint(a["walkin_min"], a["walkin_max"])
                def conv(rate):
                    return max(0, round(wi * rate * random.uniform(0.65, 1.35)))
                sa = conv(a["sa_rate"])
                fl = conv(a["fl_rate"])
                ff = conv(a["ff_rate"])
                fh = conv(a["fh_rate"])
                l1 = conv(a["l1_rate"])
                X  = a["ticket_size"]
                sa_rev = sa * X
                fl_rev = fl * X * a["fl_pct"]
                ff_rev = ff * X * a["ff_pct"]
                fh_rev = fh * X * a["fh_pct"]
                l1_rev = l1 * X * a["l1_pct"]
                rows.append({
                    "date":      dt,
                    "month_num": mn,
                    "year":      yr,
                    "month_lbl": mlbl,
                    "quarter":   qtr,
                    "ctr_id":    c["id"],
                    "centre":    c["name"],
                    "state":     c["state"],
                    "area":      c["area"],
                    "walk_ins":  wi,
                    "sa":  sa, "fl":  fl, "ff":  ff, "fh":  fh, "l1":  l1,
                    "sa_rev": sa_rev, "fl_rev": fl_rev, "ff_rev": ff_rev,
                    "fh_rev": fh_rev, "l1_rev": l1_rev,
                    "total_rev": sa_rev + fl_rev + ff_rev + fh_rev + l1_rev,
                })
    return pd.DataFrame(rows)

# ── Cost calculations ──────────────────────────────────────────────────────
def get_centre_costs(assumptions=None):
    a = assumptions or DEFAULT_ASSUMPTIONS
    monthly_salary = (a["mgr_salary"] + a["coach_salary"] * a["n_coaches"]
                      + a["bda_salary"] + a["admin_salary"])
    other_fixed    = a["utilities"] + a["marketing"] + a["misc"]
    staff_count    = 1 + a["n_coaches"] + 1 + 1
    rows = []
    for c in CENTRES:
        rent     = c["area"] * a["rent_per_sqft"]
        monthly  = rent + monthly_salary + other_fixed
        annual   = monthly * 12
        rows.append({
            "ctr_id":         c["id"],
            "centre":         c["name"],
            "area":           c["area"],
            "monthly_rent":   rent,
            "monthly_salary": monthly_salary,
            "other_fixed":    other_fixed,
            "monthly_cost":   monthly,
            "annual_cost":    annual,
            "staff":          staff_count,
        })
    return pd.DataFrame(rows)

# ── Aggregations ───────────────────────────────────────────────────────────
def monthly_by_centre(df):
    return (df.groupby(["month_lbl", "month_num", "year", "quarter", "centre"])
              ["total_rev"].sum().reset_index()
              .sort_values(["year", "month_num"]))

def quarterly_by_centre(df):
    return (df.groupby(["quarter", "centre"])["total_rev"]
              .sum().reset_index())

def service_mix(df):
    totals = {svc: df[col].sum() for svc, col in zip(SERVICES, REV_COLS)}
    grand  = sum(totals.values())
    conv   = {svc: df[cc].sum() for svc, cc in zip(SERVICES, SVC_COLS)}
    return pd.DataFrame([{
        "service":     svc,
        "revenue":     totals[svc],
        "pct":         totals[svc] / grand if grand else 0,
        "conversions": conv[svc],
        "avg_ticket":  totals[svc] / conv[svc] if conv[svc] else 0,
    } for svc in SERVICES])

def day_report(df, date):
    return df[df["date"] == date]

def mtd_report(df, date):
    return df[(df["month_num"] == date.month) &
              (df["year"] == date.year) &
              (df["date"] <= date)]
