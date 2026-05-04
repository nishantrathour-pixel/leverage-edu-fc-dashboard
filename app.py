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

# ── Palette ────────────────────────────────────────────────────────────────
DARK_BG    = "#0E1117"
CARD_BG    = "#1A1F2E"
BLUE       = "#4DA3FF"
BLUE2      = "#2E75B6"
ORANGE     = "#FFC000"
GREEN      = "#00C48C"
RED        = "#FF4B4B"
PURPLE     = "#A78BFA"
TEAL       = "#22D3EE"
YELLOW     = "#FBBF24"
PLOT_BG    = "#161B27"
GRID_CLR   = "#2A2F3E"
TEXT_CLR   = "#FAFAFA"
MUTED      = "#8B8FA8"
CENTRE_COLORS = [BLUE, ORANGE, GREEN, PURPLE, TEAL, YELLOW]

CHART_LAYOUT = dict(
    
    plot_bgcolor=PLOT_BG,
    paper_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, family="Arial"),
    margin=dict(t=40, b=40, l=10, r=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_CLR)),
)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main { background-color: #0E1117; }
  .block-container { padding-top: 1rem; }

  .kpi-card {
    background: #1A1F2E;
    border: 1px solid #2A2F3E;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    margin-bottom: 8px;
  }
  .kpi-label { font-size: 10px; color: #8B8FA8; font-weight: 600;
               text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
  .kpi-value { font-size: 15px; font-weight: 800; color: #FAFAFA; white-space: nowrap; }
  .kpi-sub   { font-size: 12px; margin-top: 4px; }
  .kpi-pos   { color: #00C48C; }
  .kpi-neg   { color: #FF4B4B; }
  .kpi-neu   { color: #8B8FA8; }

  .sec-hdr {
    background: linear-gradient(90deg, #1A1F2E, #0E1117);
    border-left: 4px solid #4DA3FF;
    color: #FAFAFA;
    padding: 8px 16px;
    border-radius: 0 6px 6px 0;
    font-weight: 700;
    font-size: 14px;
    margin: 16px 0 10px;
    letter-spacing: 0.5px;
  }
  .insight-box {
    background: #1A1F2E;
    border: 1px solid #2A2F3E;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 6px 0;
    font-size: 13px;
    color: #FAFAFA;
  }
  .insight-box b { color: #4DA3FF; }
  div[data-testid="stSidebar"] { background-color: #1A1F2E; }
  div[data-testid="metric-container"] { display:none; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────
def inr_full(v):
    """Full readable INR format."""
    if abs(v) >= 1e7:
        return f"₹{v/1e7:.2f} Cr"
    elif abs(v) >= 1e5:
        return f"₹{v/1e5:.2f} L"
    elif abs(v) >= 1e3:
        return f"₹{v/1e3:.1f}K"
    return f"₹{v:,.0f}"

def pct(v): return f"{v:.1f}%"
def num(v):
    if v >= 1e6: return f"{v/1e6:.2f}M"
    if v >= 1e3: return f"{v/1e3:.1f}K"
    return f"{v:,.0f}"

def kpi(col, label, value, sub=None, sub_positive=None):
    sub_class = ""
    if sub_positive is True:   sub_class = "kpi-pos"
    elif sub_positive is False: sub_class = "kpi-neg"
    else:                        sub_class = "kpi-neu"
    sub_html = f'<div class="kpi-sub {sub_class}">{sub}</div>' if sub else ""
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)

def section(title, icon=""):
    st.markdown(f'<div class="sec-hdr">{icon} {title}</div>', unsafe_allow_html=True)

def insight(text):
    st.markdown(f'<div class="insight-box">{text}</div>', unsafe_allow_html=True)

def apply_dark(fig, height=360, legend_h=True):
    fig.update_layout(**CHART_LAYOUT, height=height)
    if legend_h:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom",
                                      y=1.02, xanchor="left", x=0,
                                      bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_CLR)))
    return fig

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Leverage Edu FC")
    st.caption("FY 2025-26 | 6 Experience Centres")
    st.markdown("---")
    st.markdown("### ⚙️ Assumptions")

    with st.expander("💰 Revenue", expanded=True):
        ticket_size = st.number_input("Ticket Size (X) ₹", value=150000, step=5000, format="%d")
        fl_pct = st.slider("Fly Loans % of X", 1, 20, 7) / 100
        ff_pct = st.slider("Fly Forex % of X", 1, 10,  2) / 100
        fh_pct = st.slider("Fly Homes % of X", 1, 25, 12) / 100
        l1_pct = st.slider("Leverage 1 % of X", 10, 100, 60) / 100

    with st.expander("📊 Conversion Rates"):
        sa_rate = st.slider("Study Abroad %", 5,  60, 30) / 100
        fl_rate = st.slider("Fly Loans %",    5,  80, 40) / 100
        ff_rate = st.slider("Fly Forex %",    5,  80, 40) / 100
        fh_rate = st.slider("Fly Homes %",    5,  80, 40) / 100
        l1_rate = st.slider("Leverage 1 %",   2,  30, 10) / 100

    with st.expander("🏢 Costs"):
        mgr_sal   = st.number_input("Manager Salary ₹",  value=80000,  step=2000, format="%d")
        cch_sal   = st.number_input("Coach Salary ₹",    value=45000,  step=2000, format="%d")
        bda_sal   = st.number_input("BDA Salary ₹",      value=40000,  step=2000, format="%d")
        adm_sal   = st.number_input("Admin Salary ₹",    value=25000,  step=2000, format="%d")
        rent_sqft = st.number_input("Rent/sqft/month ₹", value=120,    step=10,   format="%d")
        utilities = st.number_input("Utilities ₹/month", value=15000,  step=1000, format="%d")
        marketing = st.number_input("Marketing ₹/month", value=20000,  step=1000, format="%d")
        misc      = st.number_input("Misc ₹/month",      value=10000,  step=1000, format="%d")

    st.markdown("---")
    pages = ["📊 Executive Dashboard","📅 Day Report","📆 MTD Report",
             "📈 FY / Quarterly","🔬 Granular Metrics"]
    page  = st.radio("Navigate", pages, index=0)

assumptions = dict(
    ticket_size=ticket_size, fl_pct=fl_pct, ff_pct=ff_pct,
    fh_pct=fh_pct, l1_pct=l1_pct, walkin_min=10, walkin_max=12,
    sa_rate=sa_rate, fl_rate=fl_rate, ff_rate=ff_rate,
    fh_rate=fh_rate, l1_rate=l1_rate,
    mgr_salary=mgr_sal, coach_salary=cch_sal, n_coaches=3,
    bda_salary=bda_sal, admin_salary=adm_sal,
    rent_per_sqft=rent_sqft, utilities=utilities,
    marketing=marketing, misc=misc,
)

@st.cache_data
def load(key):
    a = dict(zip(DEFAULT_ASSUMPTIONS.keys(), key))
    return generate_raw(a), get_centre_costs(a)

df, cost_df = load(tuple(assumptions.values()))

# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 — Executive Dashboard
# ══════════════════════════════════════════════════════════════════════════
if page == pages[0]:
    st.markdown("## 🎓 Executive Dashboard — FY 2025-26")

    total_rev   = df["total_rev"].sum()
    total_cost  = cost_df["annual_cost"].sum()
    gross_pft   = total_rev - total_cost
    gm_pct      = gross_pft / total_rev * 100 if total_rev else 0
    total_wi    = df["walk_ins"].sum()
    total_conv  = int(df[SVC_COLS].sum().sum())
    avg_ticket  = total_rev / total_conv if total_conv else 0
    rev_per_day = total_rev / df["date"].nunique()

    k = st.columns(8)
    kpi(k[0], "Total Revenue",   inr_full(total_rev))
    kpi(k[1], "Total Cost",      inr_full(total_cost))
    kpi(k[2], "Gross Profit",    inr_full(gross_pft), sub="Revenue − Cost", sub_positive=gross_pft>0)
    kpi(k[3], "GM %",            pct(gm_pct), sub=f"{gm_pct-30:+.1f}pp vs 30% target", sub_positive=gm_pct>=30)
    kpi(k[4], "Walk-Ins",        num(total_wi))
    kpi(k[5], "Conversions",     num(total_conv))
    kpi(k[6], "Avg Ticket",      inr_full(avg_ticket))
    kpi(k[7], "Daily Rev",       inr_full(rev_per_day))

    st.markdown("---")

    # ── MoM stacked bar + line overlay ───────────────────────────────────
    section("Month-on-Month Revenue & Trend", "📅")
    mon_df   = monthly_by_centre(df)
    mon_tot  = mon_df.groupby(["month_lbl","month_num","year"])["total_rev"].sum().reset_index()
    mon_tot  = mon_tot.sort_values(["year","month_num"])

    fig = go.Figure()
    for i, c in enumerate(CENTRES):
        cname = c["name"]
        cdata = mon_df[mon_df["centre"]==cname].sort_values(["year","month_num"])
        fig.add_trace(go.Bar(
            name=cname, x=cdata["month_lbl"], y=cdata["total_rev"],
            marker_color=CENTRE_COLORS[i], opacity=0.9,
        ))
    # Cumulative revenue line on secondary axis
    fig.add_trace(go.Scatter(
        name="Monthly Total", x=mon_tot["month_lbl"], y=mon_tot["total_rev"],
        mode="lines+markers+text",
        text=[inr_full(v) for v in mon_tot["total_rev"]],
        textposition="top center", textfont=dict(size=9, color=ORANGE),
        line=dict(color=ORANGE, width=2.5, dash="dot"),
        marker=dict(size=7, color=ORANGE),
        yaxis="y2",
    ))
    fig.update_layout(
        **CHART_LAYOUT, height=380, barmode="stack",
        yaxis=dark_axis({"title":"Revenue (₹)","tickprefix":"₹","tickformat":","}),
        yaxis2=dict(title="Monthly Total", overlaying="y", side="right",
                    gridcolor=GRID_CLR, tickprefix="₹", tickformat=",", color=TEXT_CLR),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        xaxis=dark_axis({"tickangle":-30}),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Centre P&L + Service Mix ─────────────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        section("Centre P&L — Annual", "🏢")
        ctr_rev = df.groupby("centre")["total_rev"].sum().reset_index()
        ctr_rev.columns = ["centre","annual_rev"]
        pl = ctr_rev.merge(cost_df[["centre","area","annual_cost","staff"]], on="centre")
        pl["gross_profit"] = pl["annual_rev"] - pl["annual_cost"]
        pl["gm_pct"]       = pl["gross_profit"] / pl["annual_rev"] * 100
        pl["rev_per_sqft"] = pl["annual_rev"] / pl["area"]
        pl = pl.sort_values("annual_rev", ascending=False)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Revenue", x=pl["centre"], y=pl["annual_rev"],
            marker_color=BLUE, text=[inr_full(v) for v in pl["annual_rev"]],
            textposition="outside", textfont=dict(color=TEXT_CLR, size=10),
        ))
        fig2.add_trace(go.Bar(
            name="Cost", x=pl["centre"], y=pl["annual_cost"],
            marker_color=RED, opacity=0.75,
            text=[inr_full(v) for v in pl["annual_cost"]],
            textposition="outside", textfont=dict(color=TEXT_CLR, size=10),
        ))
        fig2.add_trace(go.Scatter(
            name="GM %", x=pl["centre"], y=pl["gm_pct"],
            mode="lines+markers+text",
            text=[f"{v:.1f}%" for v in pl["gm_pct"]],
            textposition="top center", textfont=dict(size=10, color=GREEN),
            line=dict(color=GREEN, width=2), marker=dict(size=8),
            yaxis="y2",
        ))
        fig2.update_layout(
            **CHART_LAYOUT, height=360, barmode="group",
            yaxis=dark_axis({"title":"₹ Revenue / Cost","tickprefix":"₹","tickformat":","}),
            yaxis2=dict(title="GM %", overlaying="y", side="right",
                        ticksuffix="%", color=TEXT_CLR, range=[90, 102]),
            legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Summary table
        tbl = pl[["centre","annual_rev","annual_cost","gross_profit","gm_pct","rev_per_sqft"]].copy()
        tbl.columns = ["Centre","Revenue","Cost","Gross Profit","GM %","Rev/Sqft"]
        tbl["Revenue"]      = tbl["Revenue"].apply(inr_full)
        tbl["Cost"]         = tbl["Cost"].apply(inr_full)
        tbl["Gross Profit"] = tbl["Gross Profit"].apply(inr_full)
        tbl["GM %"]         = tbl["GM %"].apply(pct)
        tbl["Rev/Sqft"]     = tbl["Rev/Sqft"].apply(inr_full)
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col2:
        section("Service Revenue Mix", "🥧")
        svc_df = service_mix(df)
        fig3 = px.pie(svc_df, names="service", values="revenue",
                      color_discrete_sequence=CENTRE_COLORS, hole=0.5)
        fig3.update_traces(
            textposition="outside",
            texttemplate="<b>%{label}</b><br>%{percent:.1%}<br>" +
                         "<span style='font-size:10px'>" +
                         svc_df["revenue"].apply(inr_full).tolist()[0] + "</span>",
            hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.0f}<br>Share: %{percent:.1%}",
        )
        # Custom text per slice
        fig3.update_traces(text=[f"{inr_full(r)}" for r in svc_df["revenue"]],
                           textinfo="percent+label")
        fig3.update_layout(**CHART_LAYOUT, height=300, showlegend=False,
                           margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig3, use_container_width=True)

        section("Service Details", "📋")
        svc_tbl = svc_df.copy()
        svc_tbl["Revenue"]  = svc_tbl["revenue"].apply(inr_full)
        svc_tbl["Share"]    = svc_tbl["pct"].apply(lambda x: pct(x*100))
        svc_tbl["Avg Ticket"] = svc_tbl["avg_ticket"].apply(inr_full)
        svc_tbl["Conversions"] = svc_tbl["conversions"].apply(lambda x: f"{int(x):,}")
        st.dataframe(svc_tbl[["service","Revenue","Share","Conversions","Avg Ticket"]]
                     .rename(columns={"service":"Service"}),
                     use_container_width=True, hide_index=True)

    # ── Insights ──────────────────────────────────────────────────────────
    section("Key Insights", "💡")
    top_centre = pl.iloc[0]["centre"]
    top_rev    = inr_full(pl.iloc[0]["annual_rev"])
    low_centre = pl.iloc[-1]["centre"]
    low_gm     = pct(pl.iloc[-1]["gm_pct"])
    best_gm_c  = pl.loc[pl["gm_pct"].idxmax(), "centre"]
    best_gm    = pct(pl["gm_pct"].max())
    sa_rev_pct = pct(svc_df[svc_df["service"]=="Study Abroad"]["pct"].values[0]*100)

    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        insight(f"🏆 <b>{top_centre}</b> is the top revenue centre at <b>{top_rev}</b> annually.")
    with ic2:
        insight(f"📉 <b>{low_centre}</b> has the lowest GM at <b>{low_gm}</b> — review rent cost.")
    with ic3:
        insight(f"💰 <b>Study Abroad</b> contributes <b>{sa_rev_pct}</b> of total revenue — highest ticket driver.")

# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 — Day Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[1]:
    st.markdown("## 📅 Daily Performance Report")
    all_dates = sorted(df["date"].unique())

    col_d, col_info = st.columns([2, 5])
    with col_d:
        selected = st.date_input("Select Date", value=datetime.date(2025, 9, 15),
                                  min_value=all_dates[0], max_value=all_dates[-1])
    day_df = day_report(df, selected)
    if day_df.empty:
        st.warning(f"No data for {selected} — may be a Sunday. Pick a Mon–Sat.")
        st.stop()

    total_rev_day  = day_df["total_rev"].sum()
    total_wi_day   = int(day_df["walk_ins"].sum())
    total_conv_day = int(day_df[SVC_COLS].sum().sum())
    avg_ticket_day = total_rev_day / total_conv_day if total_conv_day else 0

    with col_info:
        k = st.columns(4)
        kpi(k[0], "Day Revenue",    inr_full(total_rev_day))
        kpi(k[1], "Walk-Ins",       num(total_wi_day))
        kpi(k[2], "Conversions",    num(total_conv_day))
        kpi(k[3], "Avg Ticket",     inr_full(avg_ticket_day))

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        section("Centre-wise Performance", "🏢")
        ctr_day = day_df.groupby("centre").agg(
            Walk_Ins=("walk_ins","sum"),
            SA=("sa","sum"), FL=("fl","sum"), FF=("ff","sum"),
            FH=("fh","sum"), L1=("l1","sum"),
            Revenue=("total_rev","sum"),
        ).reset_index().sort_values("Revenue", ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ctr_day["centre"], y=ctr_day["Revenue"],
            marker_color=CENTRE_COLORS[:len(ctr_day)],
            text=[inr_full(v) for v in ctr_day["Revenue"]],
            textposition="outside", textfont=dict(color=TEXT_CLR),
        ))
        fig.update_layout(**CHART_LAYOUT, height=300, showlegend=False,
                          yaxis=dark_axis({"tickprefix":"₹","tickformat":","}),
                          xaxis=dark_axis())
        st.plotly_chart(fig, use_container_width=True)

        ctr_day["Revenue"] = ctr_day["Revenue"].apply(inr_full)
        st.dataframe(ctr_day, use_container_width=True, hide_index=True)

    with col2:
        section("Service Breakdown", "📊")
        svc_day = pd.DataFrame({
            "Service": SERVICES,
            "Revenue": [day_df[c].sum() for c in REV_COLS],
            "Conversions": [int(day_df[c].sum()) for c in SVC_COLS],
        })
        svc_day["Avg Ticket"] = svc_day.apply(
            lambda r: r["Revenue"]/r["Conversions"] if r["Conversions"] else 0, axis=1)

        fig2 = px.bar(svc_day, x="Revenue", y="Service", orientation="h",
                      color="Service", color_discrete_sequence=CENTRE_COLORS,
                      text=svc_day["Revenue"].apply(inr_full))
        fig2.update_traces(textposition="outside", textfont=dict(color=TEXT_CLR))
        fig2.update_layout(**CHART_LAYOUT, height=320, showlegend=False,
                           xaxis=dark_axis({"tickprefix":"₹","tickformat":","}))
        st.plotly_chart(fig2, use_container_width=True)

        svc_day["Revenue"]    = svc_day["Revenue"].apply(inr_full)
        svc_day["Avg Ticket"] = svc_day["Avg Ticket"].apply(inr_full)
        st.dataframe(svc_day, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 — MTD Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[2]:
    st.markdown("## 📆 Month-to-Date Report")
    all_dates = sorted(df["date"].unique())

    col_d, col_info = st.columns([2, 5])
    with col_d:
        selected = st.date_input("MTD up to date", value=datetime.date(2025, 9, 15),
                                  min_value=all_dates[0], max_value=all_dates[-1])

    mtd_df = mtd_report(df, selected)
    if mtd_df.empty:
        st.warning("No data for selected period.")
        st.stop()

    days_elapsed  = mtd_df["date"].nunique()
    total_rev_mtd = mtd_df["total_rev"].sum()
    total_wi_mtd  = int(mtd_df["walk_ins"].sum())
    daily_avg     = total_rev_mtd / days_elapsed if days_elapsed else 0

    with col_info:
        k = st.columns(4)
        kpi(k[0], f"MTD Revenue", inr_full(total_rev_mtd),
            sub=selected.strftime("%B %Y"), sub_positive=None)
        kpi(k[1], "Days Elapsed", str(days_elapsed))
        kpi(k[2], "Daily Avg Rev", inr_full(daily_avg))
        kpi(k[3], "MTD Walk-Ins", num(total_wi_mtd))

    st.markdown("---")
    col1, col2 = st.columns([2, 3])

    with col1:
        section("Centre MTD Summary", "🏢")
        ctr_mtd = mtd_df.groupby("centre").agg(
            Walk_Ins=("walk_ins","sum"),
            SA=("sa","sum"), FL=("fl","sum"), FF=("ff","sum"),
            FH=("fh","sum"), L1=("l1","sum"),
            MTD_Revenue=("total_rev","sum"),
        ).reset_index().sort_values("MTD_Revenue", ascending=False)
        ctr_mtd["Daily Avg"] = (ctr_mtd["MTD_Revenue"] / days_elapsed).apply(inr_full)
        ctr_mtd["MTD_Revenue_disp"] = ctr_mtd["MTD_Revenue"].apply(inr_full)

        fig = px.bar(ctr_mtd, x="MTD_Revenue", y="centre", orientation="h",
                     color="centre", color_discrete_sequence=CENTRE_COLORS,
                     text=ctr_mtd["MTD_Revenue"].apply(inr_full))
        fig.update_traces(textposition="outside", textfont=dict(color=TEXT_CLR))
        fig.update_layout(**CHART_LAYOUT, height=300, showlegend=False,
                          xaxis=dark_axis({"tickprefix":"₹","tickformat":","}))
        st.plotly_chart(fig, use_container_width=True)

        disp = ctr_mtd[["centre","MTD_Revenue_disp","Daily Avg"]].copy()
        disp.columns = ["Centre","MTD Revenue","Daily Avg"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

    with col2:
        section("Daily Revenue Trend (MTD)", "📈")
        daily = mtd_df.groupby("date")["total_rev"].sum().reset_index()
        daily["cumulative"] = daily["total_rev"].cumsum()
        daily["ma3"] = daily["total_rev"].rolling(3, min_periods=1).mean()

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(
            x=daily["date"], y=daily["total_rev"], name="Daily Rev",
            marker_color=BLUE, opacity=0.7,
            text=[inr_full(v) for v in daily["total_rev"]],
            textposition="outside", textfont=dict(size=8, color=TEXT_CLR),
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=daily["date"], y=daily["ma3"], name="3-Day MA",
            line=dict(color=TEAL, width=2), mode="lines",
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            x=daily["date"], y=daily["cumulative"], name="Cumulative",
            line=dict(color=ORANGE, width=2.5, dash="dot"),
            mode="lines+markers", marker=dict(size=5),
        ), secondary_y=True)
        fig2.update_layout(**CHART_LAYOUT, height=380,
                           legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        fig2.update_yaxes(title_text="Daily Revenue (₹)", tickprefix="₹",
                          tickformat=",", gridcolor=GRID_CLR, color=TEXT_CLR, secondary_y=False)
        fig2.update_yaxes(title_text="Cumulative (₹)", tickprefix="₹",
                          tickformat=",", gridcolor=GRID_CLR, color=TEXT_CLR, secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 — FY / Quarterly
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[3]:
    st.markdown("## 📈 FY 2025-26 | Quarterly Report")

    qtrs = ["Q1","Q2","Q3","Q4"]
    qtr_df = quarterly_by_centre(df)

    section("Quarterly Revenue by Centre", "📊")
    pivot = qtr_df.pivot(index="centre", columns="quarter", values="total_rev").fillna(0)
    pivot = pivot.reindex(columns=qtrs)
    pivot["FY Total"] = pivot.sum(axis=1)
    pivot["% of FY"]  = pivot["FY Total"] / pivot["FY Total"].sum() * 100
    pivot = pivot.sort_values("FY Total", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        # Grouped bar by centre
        fig = go.Figure()
        for i, q in enumerate(qtrs):
            fig.add_trace(go.Bar(
                name=q, x=pivot.index, y=pivot[q],
                marker_color=CENTRE_COLORS[i],
                text=[inr_full(v) for v in pivot[q]],
                textposition="outside", textfont=dict(size=9, color=TEXT_CLR),
            ))
        fig.update_layout(**CHART_LAYOUT, height=380, barmode="group",
                          yaxis=dark_axis({"tickprefix":"₹","tickformat":","}),
                          legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Waterfall of FY progression
        qtr_total = {q: df[df["quarter"]==q]["total_rev"].sum() for q in qtrs}
        monthly_cost = cost_df["monthly_cost"].sum()
        qtr_cost = {q: monthly_cost*3 for q in qtrs}

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=qtrs, y=[qtr_total[q] for q in qtrs],
            mode="lines+markers+text",
            name="Revenue",
            text=[inr_full(qtr_total[q]) for q in qtrs],
            textposition="top center", textfont=dict(color=BLUE, size=11),
            line=dict(color=BLUE, width=3), marker=dict(size=12, color=BLUE),
        ))
        gp_vals = [qtr_total[q]-qtr_cost[q] for q in qtrs]
        fig2.add_trace(go.Scatter(
            x=qtrs, y=gp_vals,
            mode="lines+markers+text",
            name="Gross Profit",
            text=[inr_full(v) for v in gp_vals],
            textposition="bottom center", textfont=dict(color=GREEN, size=11),
            line=dict(color=GREEN, width=3, dash="dot"), marker=dict(size=12, color=GREEN),
        ))
        fig2.update_layout(**CHART_LAYOUT, height=380,
                           yaxis=dark_axis({"tickprefix":"₹","tickformat":","}),
                           legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2, use_container_width=True)

    # Pivot table
    section("Revenue Matrix", "📋")
    disp = pivot.copy()
    for col in qtrs + ["FY Total"]:
        disp[col] = disp[col].apply(inr_full)
    disp["% of FY"] = disp["% of FY"].apply(pct)
    st.dataframe(disp, use_container_width=True)

    # Quarterly P&L
    section("Quarterly P&L — All Centres", "💰")
    pl_rows = []
    for q in qtrs:
        gp = qtr_total[q] - qtr_cost[q]
        gm = gp / qtr_total[q] * 100 if qtr_total[q] else 0
        pl_rows.append({"Quarter":q, "Revenue":inr_full(qtr_total[q]),
                        "Cost":inr_full(qtr_cost[q]), "Gross Profit":inr_full(gp), "GM %":pct(gm)})
    fy_rev  = sum(qtr_total.values())
    fy_cost = sum(qtr_cost.values())
    fy_gp   = fy_rev - fy_cost
    pl_rows.append({"Quarter":"FY Total","Revenue":inr_full(fy_rev),
                    "Cost":inr_full(fy_cost),"Gross Profit":inr_full(fy_gp),
                    "GM %":pct(fy_gp/fy_rev*100 if fy_rev else 0)})
    st.dataframe(pd.DataFrame(pl_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 5 — Granular Metrics
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[4]:
    st.markdown("## 🔬 Granular Operational Metrics")

    ctr_rev  = df.groupby("centre")["total_rev"].sum().reset_index()
    ctr_wi   = df.groupby("centre")["walk_ins"].sum().reset_index()
    ctr_days = df.groupby("centre")["date"].nunique().reset_index()
    ctr_days.columns = ["centre","working_days"]
    eff = ctr_rev.merge(cost_df, on="centre").merge(ctr_wi, on="centre").merge(ctr_days, on="centre")
    eff.columns = [c.replace("total_rev","annual_rev") for c in eff.columns]
    eff["cost_per_sqft"]   = eff["annual_cost"] / eff["area"]
    eff["cost_pct_rev"]    = eff["annual_cost"] / eff["annual_rev"] * 100
    eff["rev_per_sqft"]    = eff["annual_rev"]  / eff["area"]
    eff["rev_per_member"]  = eff["annual_rev"]  / eff["staff"]
    eff["rev_per_wi"]      = eff["annual_rev"]  / eff["walk_ins"]
    eff["rev_per_day"]     = eff["annual_rev"]  / eff["working_days"]
    eff["gm_pct"]          = (eff["annual_rev"] - eff["annual_cost"]) / eff["annual_rev"] * 100

    section("1. Revenue vs Cost per Centre", "💰")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Rev/Sqft (₹)", x=eff["centre"], y=eff["rev_per_sqft"],
                             marker_color=BLUE, text=[inr_full(v) for v in eff["rev_per_sqft"]],
                             textposition="outside", textfont=dict(color=TEXT_CLR)))
        fig.add_trace(go.Bar(name="Cost/Sqft (₹)", x=eff["centre"], y=eff["cost_per_sqft"],
                             marker_color=RED, text=[inr_full(v) for v in eff["cost_per_sqft"]],
                             textposition="outside", textfont=dict(color=TEXT_CLR)))
        fig.update_layout(**CHART_LAYOUT, height=340, barmode="group",
                          yaxis=dark_axis({"tickprefix":"₹","tickformat":","}))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="GM %", x=eff["centre"], y=eff["gm_pct"],
                              marker_color=[GREEN if v>=95 else ORANGE if v>=90 else RED
                                            for v in eff["gm_pct"]],
                              text=[pct(v) for v in eff["gm_pct"]],
                              textposition="outside", textfont=dict(color=TEXT_CLR)))
        fig2.add_hline(y=95, line_dash="dot", line_color=GREEN,
                       annotation_text="Target 95%", annotation_font_color=GREEN)
        fig2.update_layout(**CHART_LAYOUT, height=340,
                           yaxis=dark_axis({"ticksuffix":"%","range":[0,105]}))
        st.plotly_chart(fig2, use_container_width=True)

    section("2. Revenue Productivity per Centre", "📈")
    prod_cols = [("rev_per_sqft","Rev/Sqft"), ("rev_per_member","Rev/Member"),
                 ("rev_per_wi","Rev/Walk-In"), ("rev_per_day","Avg Daily Rev")]
    cols = st.columns(4)
    for (col_key, label), col in zip(prod_cols, cols):
        fig = go.Figure(go.Bar(
            x=eff["centre"], y=eff[col_key],
            marker_color=CENTRE_COLORS,
            text=[inr_full(v) for v in eff[col_key]],
            textposition="outside", textfont=dict(size=9, color=TEXT_CLR),
        ))
        fig.update_layout(**CHART_LAYOUT, height=260, showlegend=False,
                          title=dict(text=label, font=dict(size=12, color=TEXT_CLR)),
                          margin=dict(t=40, b=30, l=5, r=5),
                          yaxis=dark_axis({"tickprefix":"₹","tickformat":","}))
        col.plotly_chart(fig, use_container_width=True)

    section("3. Actual vs Target Conversion Rates", "🎯")
    a = assumptions
    targets = [a["sa_rate"], a["fl_rate"], a["ff_rate"], a["fh_rate"], a["l1_rate"]]
    total_wi_all = df["walk_ins"].sum()
    actuals      = [df[c].sum() / total_wi_all for c in SVC_COLS]
    variances    = [(act-tgt)*100 for act, tgt in zip(actuals, targets)]

    col1, col2 = st.columns([3,2])
    with col1:
        fig3 = go.Figure()
        x = SERVICES
        fig3.add_trace(go.Bar(name="Target %", x=x, y=[t*100 for t in targets],
                              marker_color=MUTED, opacity=0.6))
        fig3.add_trace(go.Bar(name="Actual %", x=x, y=[a*100 for a in actuals],
                              marker_color=[GREEN if v>=0 else RED for v in variances],
                              text=[f"{a*100:.1f}%" for a in actuals],
                              textposition="outside", textfont=dict(color=TEXT_CLR)))
        fig3.update_layout(**CHART_LAYOUT, height=340, barmode="group",
                           yaxis=dark_axis({"ticksuffix":"%"}))
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        conv_tbl = pd.DataFrame({
            "Service":  SERVICES,
            "Target":   [pct(t*100) for t in targets],
            "Actual":   [pct(a*100) for a in actuals],
            "Variance": [f"{v:+.2f}pp" for v in variances],
        })
        st.dataframe(conv_tbl, use_container_width=True, hide_index=True)

    section("4. Service Revenue Heatmap by Centre", "🗺️")
    heat = df.groupby("centre")[REV_COLS].sum()
    heat.columns = SERVICES
    heat_pct = heat.div(heat.sum(axis=1), axis=0) * 100
    fig4 = px.imshow(heat_pct.round(1), color_continuous_scale="Blues", aspect="auto",
                     text_auto=".1f",
                     labels=dict(color="% of Centre Rev"),
                     title="Service Revenue Share % by Centre")
    fig4.update_layout(**CHART_LAYOUT, height=320, margin=dict(t=50, b=20))
    fig4.update_traces(textfont=dict(color="white"))
    st.plotly_chart(fig4, use_container_width=True)
