import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from data_engine import (
    generate_raw, get_centre_costs, monthly_by_centre,
    quarterly_by_centre, service_mix, day_report, mtd_report,
    CENTRES, MONTHS, SERVICES, SVC_COLS, REV_COLS, DEFAULT_ASSUMPTIONS
)

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Leverage Edu | FC Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme colours ──────────────────────────────────────────────────────────
DARK_BLUE  = "#1F3864"
MED_BLUE   = "#2E75B6"
LIGHT_BLUE = "#D6E4F0"
ORANGE     = "#FFC000"
GREEN      = "#70AD47"
RED        = "#FF0000"
CENTRE_COLORS = px.colors.qualitative.Set2

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .stMetric { background: white; border-radius: 10px; padding: 12px; 
                box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    .kpi-card { background: white; border-radius: 10px; padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
    .kpi-label { font-size: 13px; color: #666; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #1F3864; margin: 6px 0 0; }
    .kpi-sub   { font-size: 12px; color: #999; }
    .section-header { background: #1F3864; color: white; padding: 8px 16px;
                      border-radius: 6px; font-weight: 700; margin: 16px 0 8px; }
    div[data-testid="metric-container"] { background: white; border-radius: 10px;
        padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
    .sidebar-section { font-size: 12px; color: #888; text-transform: uppercase;
                       font-weight: 700; margin: 16px 0 4px; letter-spacing: 0.5px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar – Assumptions ─────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Leverage_Edu_logo.png/320px-Leverage_Edu_logo.png",
             use_column_width=True)
    st.markdown("## ⚙️ Assumptions")

    st.markdown('<p class="sidebar-section">Revenue</p>', unsafe_allow_html=True)
    ticket_size = st.number_input("Ticket Size – Study Abroad (X) ₹",
                                  value=150000, step=5000, format="%d")
    fl_pct = st.slider("Fly Loans % of X", 1, 20, 7) / 100
    ff_pct = st.slider("Fly Forex % of X", 1, 10, 2) / 100
    fh_pct = st.slider("Fly Homes % of X", 1, 25, 12) / 100
    l1_pct = st.slider("Leverage 1 % of X", 10, 100, 60) / 100

    st.markdown('<p class="sidebar-section">Conversions</p>', unsafe_allow_html=True)
    sa_rate = st.slider("Study Abroad conv %", 5, 60, 30) / 100
    fl_rate = st.slider("Fly Loans conv %",    5, 80, 40) / 100
    ff_rate = st.slider("Fly Forex conv %",    5, 80, 40) / 100
    fh_rate = st.slider("Fly Homes conv %",    5, 80, 40) / 100
    l1_rate = st.slider("Leverage 1 conv %",   2, 30, 10) / 100

    st.markdown('<p class="sidebar-section">Costs</p>', unsafe_allow_html=True)
    mgr_sal   = st.number_input("Manager Salary ₹",  value=80000, step=2000, format="%d")
    cch_sal   = st.number_input("Coach Salary ₹",    value=45000, step=2000, format="%d")
    bda_sal   = st.number_input("BDA Salary ₹",      value=40000, step=2000, format="%d")
    adm_sal   = st.number_input("Admin Salary ₹",    value=25000, step=2000, format="%d")
    rent_sqft = st.number_input("Rent/sqft/month ₹", value=120,   step=10,   format="%d")
    utilities = st.number_input("Utilities ₹/month", value=15000, step=1000, format="%d")
    marketing = st.number_input("Marketing ₹/month", value=20000, step=1000, format="%d")
    misc      = st.number_input("Misc ₹/month",      value=10000, step=1000, format="%d")

assumptions = {
    "ticket_size": ticket_size, "fl_pct": fl_pct, "ff_pct": ff_pct,
    "fh_pct": fh_pct, "l1_pct": l1_pct,
    "walkin_min": 10, "walkin_max": 12,
    "sa_rate": sa_rate, "fl_rate": fl_rate, "ff_rate": ff_rate,
    "fh_rate": fh_rate, "l1_rate": l1_rate,
    "mgr_salary": mgr_sal, "coach_salary": cch_sal, "n_coaches": 3,
    "bda_salary": bda_sal, "admin_salary": adm_sal,
    "rent_per_sqft": rent_sqft, "utilities": utilities,
    "marketing": marketing, "misc": misc,
}

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data(assumptions_key):
    a = dict(zip(DEFAULT_ASSUMPTIONS.keys(), assumptions_key))
    df   = generate_raw(a)
    cost = get_centre_costs(a)
    return df, cost

assumptions_key = tuple(assumptions.values())
df, cost_df = load_data(assumptions_key)

# ── Helper formatters ──────────────────────────────────────────────────────
def inr(v):
    if abs(v) >= 1e7:
        return f"₹{v/1e7:.2f} Cr"
    elif abs(v) >= 1e5:
        return f"₹{v/1e5:.2f} L"
    return f"₹{v:,.0f}"

def fmt_num(v):
    if v >= 1e6: return f"{v/1e6:.1f}M"
    if v >= 1e3: return f"{v/1e3:.1f}K"
    return f"{v:,.0f}"

# ── Navigation ─────────────────────────────────────────────────────────────
pages = ["📊 Executive Dashboard", "📅 Day Report", "📆 MTD Report",
         "📈 FY / Quarterly", "🔬 Granular Metrics"]
page  = st.sidebar.radio("Navigation", pages, index=0)
st.sidebar.markdown("---")
st.sidebar.caption("FY 2025-26  |  6 Experience Centres  |  Leverage Edu FC Model")

# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 – Executive Dashboard
# ══════════════════════════════════════════════════════════════════════════
if page == pages[0]:
    st.markdown(f'<div class="section-header">🎓 LEVERAGE EDU — EXPERIENCE CENTRES | EXECUTIVE DASHBOARD | FY 2025-26</div>',
                unsafe_allow_html=True)

    total_rev  = df["total_rev"].sum()
    total_cost = cost_df["annual_cost"].sum()
    gross_pft  = total_rev - total_cost
    ebitda_pct = gross_pft / total_rev * 100 if total_rev else 0
    total_wi   = df["walk_ins"].sum()
    total_conv = df[SVC_COLS].sum().sum()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Revenue",  inr(total_rev))
    k2.metric("Total Cost",     inr(total_cost))
    k3.metric("Gross Profit",   inr(gross_pft))
    k4.metric("EBITDA Margin",  f"{ebitda_pct:.1f}%",
              delta=f"{ebitda_pct - 30:.1f}pp vs 30% target" if ebitda_pct != 0 else None)
    k5.metric("Total Walk-Ins", fmt_num(total_wi))
    k6.metric("Total Conversions", fmt_num(total_conv))

    st.markdown("---")

    # ── Monthly Revenue Chart ──────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### Month-on-Month Revenue by Centre")
        mon_df = monthly_by_centre(df)
        fig = px.bar(mon_df, x="month_lbl", y="total_rev", color="centre",
                     color_discrete_sequence=CENTRE_COLORS,
                     labels={"total_rev": "Revenue (₹)", "month_lbl": "Month", "centre": "Centre"},
                     barmode="stack")
        fig.update_layout(height=360, plot_bgcolor="white", paper_bgcolor="white",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02),
                          xaxis_tickangle=-30, margin=dict(t=30, b=40))
        fig.update_yaxes(tickprefix="₹", tickformat=",")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Service Revenue Mix")
        svc_df = service_mix(df)
        fig2 = px.pie(svc_df, names="service", values="revenue",
                      color_discrete_sequence=CENTRE_COLORS, hole=0.45)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(height=360, showlegend=False,
                           margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Centre P&L Table ───────────────────────────────────────────────
    st.markdown("#### Centre-wise Annual P&L")
    ctr_rev = df.groupby("centre")["total_rev"].sum().reset_index()
    ctr_rev.columns = ["centre", "annual_rev"]
    pl = ctr_rev.merge(cost_df[["centre","area","annual_cost","staff"]], on="centre")
    pl["gross_profit"] = pl["annual_rev"] - pl["annual_cost"]
    pl["ebitda_pct"]   = pl["gross_profit"] / pl["annual_rev"] * 100
    pl["rev_per_sqft"] = pl["annual_rev"] / pl["area"]
    pl["rev_per_member"] = pl["annual_rev"] / pl["staff"]

    display = pl.copy()
    display["Annual Revenue"]   = display["annual_rev"].apply(inr)
    display["Annual Cost"]      = display["annual_cost"].apply(inr)
    display["Gross Profit"]     = display["gross_profit"].apply(inr)
    display["EBITDA %"]         = display["ebitda_pct"].apply(lambda x: f"{x:.1f}%")
    display["Rev/Sqft"]         = display["rev_per_sqft"].apply(inr)
    display["Rev/Member"]       = display["rev_per_member"].apply(inr)
    display = display.rename(columns={"centre": "Centre"})
    st.dataframe(
        display[["Centre","Annual Revenue","Annual Cost","Gross Profit","EBITDA %","Rev/Sqft","Rev/Member"]],
        use_container_width=True, hide_index=True
    )

    # ── Centre comparison bar ─────────────────────────────────────────
    st.markdown("#### Centre Revenue Comparison")
    fig3 = px.bar(pl.sort_values("annual_rev", ascending=True),
                  x="annual_rev", y="centre", orientation="h",
                  color="ebitda_pct", color_continuous_scale="Blues",
                  labels={"annual_rev": "Annual Revenue (₹)", "centre": "", "ebitda_pct": "EBITDA %"})
    fig3.update_layout(height=280, plot_bgcolor="white", paper_bgcolor="white",
                       margin=dict(t=10, b=10))
    fig3.update_xaxes(tickprefix="₹", tickformat=",")
    st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 – Day Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[1]:
    st.markdown('<div class="section-header">📅 DAILY PERFORMANCE REPORT</div>',
                unsafe_allow_html=True)

    all_dates = sorted(df["date"].unique())
    selected  = st.date_input("Select Date", value=datetime.date(2025, 9, 15),
                               min_value=all_dates[0], max_value=all_dates[-1])

    day_df = day_report(df, selected)
    if day_df.empty:
        st.warning(f"No data for {selected} — it may be a Sunday. Please select a working day.")
        st.stop()

    total_rev_day  = day_df["total_rev"].sum()
    total_wi_day   = day_df["walk_ins"].sum()
    total_conv_day = day_df[SVC_COLS].sum().sum()

    k1, k2, k3 = st.columns(3)
    k1.metric("Day Revenue",     inr(total_rev_day))
    k2.metric("Total Walk-Ins",  fmt_num(total_wi_day))
    k3.metric("Total Conversions", fmt_num(int(total_conv_day)))

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### Centre-wise Performance")
        ctr_day = day_df.groupby("centre").agg(
            Walk_Ins=("walk_ins", "sum"),
            SA=("sa","sum"), FL=("fl","sum"), FF=("ff","sum"),
            FH=("fh","sum"), L1=("l1","sum"),
            Revenue=("total_rev","sum")
        ).reset_index()
        ctr_day["Revenue"] = ctr_day["Revenue"].apply(inr)
        st.dataframe(ctr_day, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Service Revenue")
        svc_day = pd.DataFrame({
            "Service": SERVICES,
            "Revenue": [day_df[c].sum() for c in REV_COLS],
            "Conversions": [day_df[c].sum() for c in SVC_COLS],
        })
        svc_day["Avg Ticket"] = svc_day.apply(
            lambda r: r["Revenue"]/r["Conversions"] if r["Conversions"] else 0, axis=1)
        fig = px.bar(svc_day, x="Service", y="Revenue",
                     color="Service", color_discrete_sequence=CENTRE_COLORS,
                     text=svc_day["Revenue"].apply(inr))
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, showlegend=False, plot_bgcolor="white",
                          paper_bgcolor="white", margin=dict(t=10))
        fig.update_yaxes(tickprefix="₹", tickformat=",")
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 – MTD Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[2]:
    st.markdown('<div class="section-header">📆 MONTH-TO-DATE REPORT</div>',
                unsafe_allow_html=True)

    all_dates = sorted(df["date"].unique())
    selected  = st.date_input("Select Date (MTD up to this date)",
                               value=datetime.date(2025, 9, 15),
                               min_value=all_dates[0], max_value=all_dates[-1])

    mtd_df = mtd_report(df, selected)
    if mtd_df.empty:
        st.warning("No data for selected period.")
        st.stop()

    month_name = selected.strftime("%B %Y")
    days_elapsed = mtd_df["date"].nunique()
    total_rev_mtd = mtd_df["total_rev"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"MTD Revenue ({month_name})", inr(total_rev_mtd))
    k2.metric("Days Elapsed", days_elapsed)
    k3.metric("Avg Daily Revenue", inr(total_rev_mtd / days_elapsed if days_elapsed else 0))
    k4.metric("MTD Walk-Ins", fmt_num(mtd_df["walk_ins"].sum()))

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### Centre-wise MTD")
        ctr_mtd = mtd_df.groupby("centre").agg(
            Walk_Ins=("walk_ins","sum"),
            SA=("sa","sum"), FL=("fl","sum"), FF=("ff","sum"),
            FH=("fh","sum"), L1=("l1","sum"),
            MTD_Revenue=("total_rev","sum"),
        ).reset_index()
        ctr_mtd["Daily Avg"] = (ctr_mtd["MTD_Revenue"] / days_elapsed).apply(inr)
        ctr_mtd["MTD_Revenue"] = ctr_mtd["MTD_Revenue"].apply(inr)
        st.dataframe(ctr_mtd, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Daily Revenue Trend")
        daily = mtd_df.groupby("date")["total_rev"].sum().reset_index()
        daily["cumulative"] = daily["total_rev"].cumsum()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=daily["date"], y=daily["total_rev"],
                             name="Daily Rev", marker_color=MED_BLUE), secondary_y=False)
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["cumulative"],
                                 name="Cumulative", line=dict(color=ORANGE, width=2)),
                      secondary_y=True)
        fig.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                          legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=10))
        fig.update_yaxes(tickprefix="₹", tickformat=",", secondary_y=False)
        fig.update_yaxes(tickprefix="₹", tickformat=",", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 – FY / Quarterly Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[3]:
    st.markdown('<div class="section-header">📈 FY 2025-26 | QUARTERLY REPORT</div>',
                unsafe_allow_html=True)

    # Quarterly revenue by centre
    qtr_df = quarterly_by_centre(df)
    pivot   = qtr_df.pivot(index="centre", columns="quarter", values="total_rev").fillna(0)
    pivot["FY Total"] = pivot.sum(axis=1)
    pivot["% of FY"]  = pivot["FY Total"] / pivot["FY Total"].sum() * 100

    st.markdown("#### Quarterly Revenue by Centre (₹)")
    pivot_display = pivot.copy()
    for col in ["Q1","Q2","Q3","Q4","FY Total"]:
        pivot_display[col] = pivot_display[col].apply(inr)
    pivot_display["% of FY"] = pivot_display["% of FY"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(pivot_display, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Quarterly Revenue Trend")
        qtr_total = df.groupby("quarter")["total_rev"].sum().reset_index()
        qtr_order = ["Q1","Q2","Q3","Q4"]
        qtr_total["quarter"] = pd.Categorical(qtr_total["quarter"], categories=qtr_order, ordered=True)
        qtr_total = qtr_total.sort_values("quarter")
        fig = px.line(qtr_total, x="quarter", y="total_rev", markers=True,
                      labels={"total_rev": "Revenue (₹)", "quarter": "Quarter"},
                      color_discrete_sequence=[MED_BLUE])
        fig.update_traces(line=dict(width=3), marker=dict(size=10))
        fig.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(t=10))
        fig.update_yaxes(tickprefix="₹", tickformat=",")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Revenue by Quarter & Centre")
        fig2 = px.bar(qtr_df, x="quarter", y="total_rev", color="centre",
                      barmode="group", color_discrete_sequence=CENTRE_COLORS,
                      category_orders={"quarter": ["Q1","Q2","Q3","Q4"]},
                      labels={"total_rev": "Revenue (₹)", "quarter": "Quarter"})
        fig2.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                           legend=dict(orientation="h", y=1.1), margin=dict(t=30))
        fig2.update_yaxes(tickprefix="₹", tickformat=",")
        st.plotly_chart(fig2, use_container_width=True)

    # Quarterly P&L
    st.markdown("#### Quarterly P&L – All Centres")
    qtrs = ["Q1","Q2","Q3","Q4"]
    qtr_rev  = {q: df[df["quarter"]==q]["total_rev"].sum() for q in qtrs}
    monthly_cost = cost_df["monthly_cost"].sum()
    qtr_cost = {q: monthly_cost * 3 for q in qtrs}
    pl_rows = []
    for q in qtrs:
        gp = qtr_rev[q] - qtr_cost[q]
        pl_rows.append({
            "Quarter": q, "Revenue": inr(qtr_rev[q]), "Cost": inr(qtr_cost[q]),
            "Gross Profit": inr(gp),
            "EBITDA %": f"{gp/qtr_rev[q]*100:.1f}%" if qtr_rev[q] else "0.0%"
        })
    total_rev_fy = sum(qtr_rev.values())
    total_cost_fy = sum(qtr_cost.values())
    gp_fy = total_rev_fy - total_cost_fy
    pl_rows.append({
        "Quarter": "FY Total", "Revenue": inr(total_rev_fy), "Cost": inr(total_cost_fy),
        "Gross Profit": inr(gp_fy),
        "EBITDA %": f"{gp_fy/total_rev_fy*100:.1f}%" if total_rev_fy else "0.0%"
    })
    st.dataframe(pd.DataFrame(pl_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 5 – Granular Metrics
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[4]:
    st.markdown('<div class="section-header">🔬 GRANULAR OPERATIONAL METRICS</div>',
                unsafe_allow_html=True)

    # 1. Cost efficiency
    st.markdown("#### 1. Cost Efficiency by Centre")
    ctr_rev = df.groupby("centre")["total_rev"].sum().reset_index()
    eff = ctr_rev.merge(cost_df, on="centre")
    eff["cost_per_sqft"]   = eff["annual_cost"] / eff["area"]
    eff["cost_per_member"] = eff["annual_cost"] / eff["staff"]
    eff["cost_pct_rev"]    = eff["annual_cost"] / eff["total_rev"] * 100
    eff_disp = eff[["centre","area","annual_cost","cost_per_sqft","cost_per_member","cost_pct_rev"]].copy()
    eff_disp.columns = ["Centre","Area (sqft)","Annual Cost","Cost/Sqft","Cost/Member","Cost % of Rev"]
    eff_disp["Annual Cost"]   = eff_disp["Annual Cost"].apply(inr)
    eff_disp["Cost/Sqft"]     = eff_disp["Cost/Sqft"].apply(inr)
    eff_disp["Cost/Member"]   = eff_disp["Cost/Member"].apply(inr)
    eff_disp["Cost % of Rev"] = eff_disp["Cost % of Rev"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(eff_disp, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(eff.sort_values("cost_per_sqft"), x="centre", y="cost_per_sqft",
                     color="centre", color_discrete_sequence=CENTRE_COLORS,
                     labels={"cost_per_sqft": "Annual Cost per Sqft (₹)", "centre": ""},
                     title="Cost per Sqft by Centre")
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                          height=300, margin=dict(t=30))
        fig.update_yaxes(tickprefix="₹", tickformat=",")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(eff.sort_values("cost_pct_rev"), x="centre", y="cost_pct_rev",
                      color="centre", color_discrete_sequence=CENTRE_COLORS,
                      labels={"cost_pct_rev": "Cost as % of Revenue", "centre": ""},
                      title="Cost % of Revenue by Centre")
        fig2.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                           height=300, margin=dict(t=30))
        fig2.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True)

    # 2. Revenue productivity
    st.markdown("#### 2. Revenue Productivity")
    ctr_wi   = df.groupby("centre")["walk_ins"].sum().reset_index()
    ctr_days = df.groupby("centre")["date"].nunique().reset_index()
    ctr_days.columns = ["centre", "working_days"]
    prod = eff[["centre","total_rev","area","staff"]].merge(ctr_wi, on="centre").merge(ctr_days, on="centre")
    prod["rev_per_sqft"]   = prod["total_rev"] / prod["area"]
    prod["rev_per_member"] = prod["total_rev"] / prod["staff"]
    prod["rev_per_wi"]     = prod["total_rev"] / prod["walk_ins"]
    prod["rev_per_day"]    = prod["total_rev"] / prod["working_days"]

    prod_disp = prod[["centre","total_rev","rev_per_sqft","rev_per_member","rev_per_wi","rev_per_day"]].copy()
    prod_disp.columns = ["Centre","Annual Rev","Rev/Sqft","Rev/Member","Rev/Walk-In","Avg Daily Rev"]
    for col in ["Annual Rev","Rev/Sqft","Rev/Member","Rev/Walk-In","Avg Daily Rev"]:
        prod_disp[col] = prod_disp[col].apply(inr)
    st.dataframe(prod_disp, use_container_width=True, hide_index=True)

    # 3. Conversion efficiency vs target
    st.markdown("#### 3. Actual vs Target Conversion Rates")
    a = assumptions
    targets = [a["sa_rate"], a["fl_rate"], a["ff_rate"], a["fh_rate"], a["l1_rate"]]
    total_wi = df["walk_ins"].sum()
    actuals  = [df[c].sum() / total_wi for c in SVC_COLS]
    conv_df  = pd.DataFrame({
        "Service": SERVICES,
        "Target %": [t * 100 for t in targets],
        "Actual %": [v * 100 for v in actuals],
        "Variance (pp)": [(v - t) * 100 for v, t in zip(actuals, targets)]
    })

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="Target", x=conv_df["Service"],
                          y=conv_df["Target %"], marker_color=LIGHT_BLUE))
    fig3.add_trace(go.Bar(name="Actual", x=conv_df["Service"],
                          y=conv_df["Actual %"], marker_color=MED_BLUE))
    fig3.update_layout(barmode="group", height=320, plot_bgcolor="white",
                       paper_bgcolor="white", margin=dict(t=10),
                       legend=dict(orientation="h", y=1.1))
    fig3.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig3, use_container_width=True)

    conv_disp = conv_df.copy()
    conv_disp["Target %"]    = conv_disp["Target %"].apply(lambda x: f"{x:.1f}%")
    conv_disp["Actual %"]    = conv_disp["Actual %"].apply(lambda x: f"{x:.1f}%")
    conv_disp["Variance (pp)"] = conv_disp["Variance (pp)"].apply(lambda x: f"{x:+.2f}pp")
    st.dataframe(conv_disp, use_container_width=True, hide_index=True)

    # 4. Service revenue heatmap by centre
    st.markdown("#### 4. Service Revenue Heatmap by Centre")
    heat_data = df.groupby("centre")[REV_COLS].sum()
    heat_data.columns = SERVICES
    fig4 = px.imshow(heat_data, color_continuous_scale="Blues", aspect="auto",
                     labels=dict(color="Revenue (₹)"),
                     title="Revenue Intensity per Centre per Service")
    fig4.update_layout(height=320, margin=dict(t=40))
    st.plotly_chart(fig4, use_container_width=True)
