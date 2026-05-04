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

st.set_page_config(page_title="Leverage Edu | FC Dashboard", page_icon="🎓",
                   layout="wide", initial_sidebar_state="expanded")

# colours
DARK_BG = "#0E1117"; CARD_BG = "#1A1F2E"; PLOT_BG = "#161B27"
GRID    = "#2A2F3E";  TEXT    = "#FAFAFA"; MUTED   = "#8B8FA8"
BLUE="#4DA3FF"; ORANGE="#FFC000"; GREEN="#00C48C"
RED="#FF4B4B";  PURPLE="#A78BFA"; TEAL="#22D3EE"; YELLOW="#FBBF24"
CC = [BLUE, ORANGE, GREEN, PURPLE, TEAL, YELLOW]

def ax(**kw):
    """Return axis style dict merged with dark defaults."""
    d = dict(gridcolor=GRID, zerolinecolor=GRID, color=TEXT)
    d.update(kw)
    return d

def chart(fig, h=360, barmode=None, legend_h=True, **kw):
    layout = dict(plot_bgcolor=PLOT_BG, paper_bgcolor=CARD_BG,
                  font=dict(color=TEXT, family="Arial"),
                  margin=dict(t=40,b=40,l=10,r=10), height=h,
                  legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)))
    if barmode: layout["barmode"] = barmode
    if legend_h: layout["legend"].update(orientation="h", y=1.08, xanchor="left", x=0)
    layout.update(kw)
    fig.update_layout(**layout)
    return fig

st.markdown("""<style>
.main{background:#0E1117}
.block-container{padding-top:1rem}
.kpi{background:#1A1F2E;border:1px solid #2A2F3E;border-radius:10px;
     padding:10px 8px;text-align:center;margin-bottom:6px}
.kl{font-size:10px;color:#8B8FA8;text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px}
.kv{font-size:16px;font-weight:800;color:#FAFAFA;white-space:nowrap}
.ks{font-size:10px;margin-top:2px}
.pos{color:#00C48C}.neg{color:#FF4B4B}.neu{color:#8B8FA8}
.sh{background:linear-gradient(90deg,#1A1F2E,#0E1117);border-left:4px solid #4DA3FF;
    color:#FAFAFA;padding:8px 16px;border-radius:0 6px 6px 0;font-weight:700;
    font-size:13px;margin:14px 0 8px;letter-spacing:.4px}
.ib{background:#1A1F2E;border:1px solid #2A2F3E;border-radius:8px;
    padding:10px 14px;font-size:11px;color:#FAFAFA;line-height:1.5}
.ib b{color:#4DA3FF}
div[data-testid="stSidebar"]{background:#1A1F2E}
div[data-testid="metric-container"]{display:none}
</style>""", unsafe_allow_html=True)

def kpi(col, label, val, sub=None, cls="neu"):
    sub_html = f'<div class="ks {cls}">{sub}</div>' if sub else ""
    col.markdown(f'<div class="kpi"><div class="kl">{label}</div>'
                 f'<div class="kv">{val}</div>{sub_html}</div>', unsafe_allow_html=True)

def sec(t, i=""): st.markdown(f'<div class="sh">{i} {t}</div>', unsafe_allow_html=True)
def ins(t): st.markdown(f'<div class="ib">{t}</div>', unsafe_allow_html=True)

def inr(v):
    if abs(v)>=1e7: return f"₹{v/1e7:.2f} Cr"
    if abs(v)>=1e5: return f"₹{v/1e5:.2f} L"
    if abs(v)>=1e3: return f"₹{v/1e3:.1f}K"
    return f"₹{v:,.0f}"

def num(v):
    if v>=1e6: return f"{v/1e6:.2f}M"
    if v>=1e3: return f"{v/1e3:.1f}K"
    return f"{v:,.0f}"

def pct(v): return f"{v:.1f}%"

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Leverage Edu FC")
    st.caption("FY 2025-26 | 6 Experience Centres")
    st.markdown("---")

    # Navigation FIRST
    pages = ["📊 Executive Dashboard","📅 Day Report","📆 MTD Report",
             "📈 FY / Quarterly","🔬 Granular Metrics"]
    page = st.radio("Navigate", pages, index=0)
    st.markdown("---")

    # Assumptions below
    st.markdown("### ⚙️ Assumptions")
    with st.expander("💰 Revenue", expanded=True):
        ticket = st.number_input("Ticket Size (X) ₹", value=150000, step=5000, format="%d")
        fl_pct = st.slider("Fly Loans % of X",  1, 20,  7) / 100
        ff_pct = st.slider("Fly Forex % of X",  1, 10,  2) / 100
        fh_pct = st.slider("Fly Homes % of X",  1, 25, 12) / 100
        l1_pct = st.slider("Leverage 1 % of X",10,100, 60) / 100
    with st.expander("📊 Conversion Rates"):
        sa_r = st.slider("Study Abroad %", 5, 60, 30) / 100
        fl_r = st.slider("Fly Loans %",    5, 80, 40) / 100
        ff_r = st.slider("Fly Forex %",    5, 80, 40) / 100
        fh_r = st.slider("Fly Homes %",    5, 80, 40) / 100
        l1_r = st.slider("Leverage 1 %",   2, 30, 10) / 100
    with st.expander("🏢 Costs"):
        mgr = st.number_input("Manager ₹",    value=80000, step=2000, format="%d")
        cch = st.number_input("Coach ₹",      value=45000, step=2000, format="%d")
        bda = st.number_input("BDA ₹",        value=40000, step=2000, format="%d")
        adm = st.number_input("Admin ₹",      value=25000, step=2000, format="%d")
        rnt = st.number_input("Rent/sqft ₹",  value=120,   step=10,   format="%d")
        utl = st.number_input("Utilities ₹",  value=15000, step=1000, format="%d")
        mkt = st.number_input("Marketing ₹",  value=20000, step=1000, format="%d")
        msc = st.number_input("Misc ₹",       value=10000, step=1000, format="%d")

assumptions = dict(
    ticket_size=ticket, fl_pct=fl_pct, ff_pct=ff_pct, fh_pct=fh_pct, l1_pct=l1_pct,
    walkin_min=10, walkin_max=12,
    sa_rate=sa_r, fl_rate=fl_r, ff_rate=ff_r, fh_rate=fh_r, l1_rate=l1_r,
    mgr_salary=mgr, coach_salary=cch, n_coaches=3,
    bda_salary=bda, admin_salary=adm,
    rent_per_sqft=rnt, utilities=utl, marketing=mkt, misc=msc,
)

@st.cache_data
def load(key):
    a = dict(zip(DEFAULT_ASSUMPTIONS.keys(), key))
    return generate_raw(a), get_centre_costs(a)

df, cost_df = load(tuple(assumptions.values()))

# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 – Executive Dashboard
# ══════════════════════════════════════════════════════════════════════════
if page == pages[0]:
    st.markdown("## 🎓 Executive Dashboard — FY 2025-26")
    tot_rev  = df["total_rev"].sum()
    tot_cost = cost_df["annual_cost"].sum()
    gp       = tot_rev - tot_cost
    gm       = gp / tot_rev * 100 if tot_rev else 0
    tot_wi   = df["walk_ins"].sum()
    tot_conv = int(df[SVC_COLS].sum().sum())
    avg_tkt  = tot_rev / tot_conv if tot_conv else 0
    daily_rv = tot_rev / df["date"].nunique()

    k = st.columns(8)
    kpi(k[0], "Total Revenue",   inr(tot_rev))
    kpi(k[1], "Total Cost",      inr(tot_cost))
    kpi(k[2], "Gross Profit",    inr(gp),  sub="Revenue − Cost", cls="pos" if gp>0 else "neg")
    kpi(k[3], "GM %",            pct(gm),  sub=f"{gm-30:+.1f}pp vs 30% target", cls="pos" if gm>=30 else "neg")
    kpi(k[4], "Walk-Ins",        num(tot_wi))
    kpi(k[5], "Conversions",     num(tot_conv))
    kpi(k[6], "Avg Ticket",      inr(avg_tkt))
    kpi(k[7], "Daily Rev",       inr(daily_rv))
    st.markdown("---")

    # MoM chart
    sec("Month-on-Month Revenue by Centre", "📅")
    mon_df  = monthly_by_centre(df)
    mon_tot = mon_df.groupby(["month_lbl","month_num","year"])["total_rev"].sum().reset_index()
    mon_tot = mon_tot.sort_values(["year","month_num"])
    fig = go.Figure()
    for i, c in enumerate(CENTRES):
        d = mon_df[mon_df["centre"]==c["name"]].sort_values(["year","month_num"])
        fig.add_trace(go.Bar(name=c["name"], x=d["month_lbl"], y=d["total_rev"],
                             marker_color=CC[i], opacity=0.9))
    fig.add_trace(go.Scatter(name="Monthly Total", x=mon_tot["month_lbl"], y=mon_tot["total_rev"],
                             mode="lines+markers+text",
                             text=[inr(v) for v in mon_tot["total_rev"]],
                             textposition="top center", textfont=dict(size=9, color=ORANGE),
                             line=dict(color=ORANGE, width=2.5, dash="dot"),
                             marker=dict(size=7, color=ORANGE), yaxis="y2"))
    chart(fig, h=380, barmode="stack",
          yaxis=ax(title="Revenue (₹)", tickprefix="₹", tickformat=","),
          yaxis2=dict(title="Monthly Total", overlaying="y", side="right",
                      tickprefix="₹", tickformat=",", color=TEXT, gridcolor=GRID),
          xaxis=ax(tickangle=-30))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        sec("Centre P&L — Annual", "🏢")
        ctr_rev = df.groupby("centre")["total_rev"].sum().reset_index()
        ctr_rev.columns = ["centre","annual_rev"]
        pl = ctr_rev.merge(cost_df[["centre","area","annual_cost","staff"]], on="centre")
        pl["gp"]  = pl["annual_rev"] - pl["annual_cost"]
        pl["gm"]  = pl["gp"] / pl["annual_rev"] * 100
        pl["r_sq"]= pl["annual_rev"] / pl["area"]
        pl = pl.sort_values("annual_rev", ascending=False)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Revenue", x=pl["centre"], y=pl["annual_rev"],
                              marker_color=BLUE,
                              text=[inr(v) for v in pl["annual_rev"]],
                              textposition="outside", textfont=dict(color=TEXT, size=9)))
        fig2.add_trace(go.Bar(name="Cost", x=pl["centre"], y=pl["annual_cost"],
                              marker_color=RED, opacity=0.75,
                              text=[inr(v) for v in pl["annual_cost"]],
                              textposition="outside", textfont=dict(color=TEXT, size=9)))
        fig2.add_trace(go.Scatter(name="GM %", x=pl["centre"], y=pl["gm"],
                                  mode="lines+markers+text",
                                  text=[f"{v:.1f}%" for v in pl["gm"]],
                                  textposition="top center", textfont=dict(size=10, color=GREEN),
                                  line=dict(color=GREEN, width=2), marker=dict(size=8),
                                  yaxis="y2"))
        chart(fig2, h=340, barmode="group",
              yaxis=ax(title="₹ Revenue / Cost", tickprefix="₹", tickformat=","),
              yaxis2=dict(title="GM %", overlaying="y", side="right",
                          ticksuffix="%", color=TEXT, range=[90, 102]),
              xaxis=ax())
        st.plotly_chart(fig2, use_container_width=True)
        tbl = pl[["centre","annual_rev","annual_cost","gp","gm","r_sq"]].copy()
        tbl.columns = ["Centre","Revenue","Cost","Gross Profit","GM %","Rev/Sqft"]
        for c in ["Revenue","Cost","Gross Profit","Rev/Sqft"]: tbl[c] = tbl[c].apply(inr)
        tbl["GM %"] = tbl["GM %"].apply(pct)
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    with col2:
        sec("Service Revenue Mix", "🥧")
        svc_df = service_mix(df)
        fig3 = px.pie(svc_df, names="service", values="revenue",
                      color_discrete_sequence=CC, hole=0.5)
        fig3.update_traces(textinfo="percent+label")
        fig3.update_layout(plot_bgcolor=PLOT_BG, paper_bgcolor=CARD_BG,
                           font=dict(color=TEXT), showlegend=False,
                           height=280, margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig3, use_container_width=True)
        sec("Service Details", "📋")
        sd = svc_df.copy()
        sd["Revenue"]     = sd["revenue"].apply(inr)
        sd["Share"]       = sd["pct"].apply(lambda x: pct(x*100))
        sd["Avg Ticket"]  = sd["avg_ticket"].apply(inr)
        sd["Conversions"] = sd["conversions"].apply(lambda x: f"{int(x):,}")
        st.dataframe(sd[["service","Revenue","Share","Conversions","Avg Ticket"]]
                     .rename(columns={"service":"Service"}),
                     use_container_width=True, hide_index=True)

    sec("Key Insights", "💡")
    top = pl.iloc[0]; low = pl.iloc[-1]; bst = pl.loc[pl["gm"].idxmax()]
    sa_s = pct(svc_df[svc_df["service"]=="Study Abroad"]["pct"].values[0]*100)
    ic = st.columns(3)
    with ic[0]: ins(f"🏆 <b>{top['centre']}</b> is top revenue centre at <b>{inr(top['annual_rev'])}</b>.")
    with ic[1]: ins(f"📉 <b>{low['centre']}</b> lowest GM at <b>{pct(low['gm'])}</b> — review rent.")
    with ic[2]: ins(f"💰 <b>Study Abroad</b> = <b>{sa_s}</b> of total revenue.")

# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 – Day Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[1]:
    st.markdown("## 📅 Daily Performance Report")
    all_dates = sorted(df["date"].unique())
    c1, c2 = st.columns([2, 5])
    with c1:
        sel = st.date_input("Select Date", value=datetime.date(2025,9,15),
                            min_value=all_dates[0], max_value=all_dates[-1])
    day_df = day_report(df, sel)
    if day_df.empty:
        st.warning("No data — pick a Mon–Sat working date.")
        st.stop()
    tr = day_df["total_rev"].sum(); tw = int(day_df["walk_ins"].sum())
    tc = int(day_df[SVC_COLS].sum().sum()); at = tr/tc if tc else 0
    with c2:
        k = st.columns(4)
        kpi(k[0],"Day Revenue",inr(tr)); kpi(k[1],"Walk-Ins",num(tw))
        kpi(k[2],"Conversions",num(tc)); kpi(k[3],"Avg Ticket",inr(at))
    st.markdown("---")
    c1, c2 = st.columns([3,2])
    with c1:
        sec("Centre-wise Performance","🏢")
        cd = day_df.groupby("centre").agg(
            Walk_Ins=("walk_ins","sum"), SA=("sa","sum"), FL=("fl","sum"),
            FF=("ff","sum"), FH=("fh","sum"), L1=("l1","sum"), Revenue=("total_rev","sum")
        ).reset_index().sort_values("Revenue", ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=cd["centre"], y=cd["Revenue"], marker_color=CC,
                             text=[inr(v) for v in cd["Revenue"]],
                             textposition="outside", textfont=dict(color=TEXT)))
        chart(fig, h=280, showlegend=False, xaxis=ax(), yaxis=ax(tickprefix="₹", tickformat=","))
        st.plotly_chart(fig, use_container_width=True)
        cd["Revenue"] = cd["Revenue"].apply(inr)
        st.dataframe(cd, use_container_width=True, hide_index=True)
    with c2:
        sec("Service Breakdown","📊")
        sd = pd.DataFrame({"Service":SERVICES,
                           "Revenue":[day_df[c].sum() for c in REV_COLS],
                           "Conversions":[int(day_df[c].sum()) for c in SVC_COLS]})
        sd["Avg Ticket"] = sd.apply(lambda r: r["Revenue"]/r["Conversions"] if r["Conversions"] else 0, axis=1)
        fig2 = px.bar(sd, x="Revenue", y="Service", orientation="h",
                      color="Service", color_discrete_sequence=CC,
                      text=sd["Revenue"].apply(inr))
        fig2.update_traces(textposition="outside", textfont=dict(color=TEXT))
        chart(fig2, h=300, showlegend=False, xaxis=ax(tickprefix="₹", tickformat=","), yaxis=ax())
        st.plotly_chart(fig2, use_container_width=True)
        sd["Revenue"] = sd["Revenue"].apply(inr); sd["Avg Ticket"] = sd["Avg Ticket"].apply(inr)
        st.dataframe(sd, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 – MTD Report
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[2]:
    st.markdown("## 📆 Month-to-Date Report")
    all_dates = sorted(df["date"].unique())
    c1, c2 = st.columns([2, 5])
    with c1:
        sel = st.date_input("MTD up to date", value=datetime.date(2025,9,15),
                            min_value=all_dates[0], max_value=all_dates[-1])
    mtd_df = mtd_report(df, sel)
    if mtd_df.empty:
        st.warning("No data for selected period.")
        st.stop()
    days = mtd_df["date"].nunique()
    tr   = mtd_df["total_rev"].sum()
    tw   = int(mtd_df["walk_ins"].sum())
    with c2:
        k = st.columns(4)
        kpi(k[0], f"MTD Revenue", inr(tr), sub=sel.strftime("%B %Y"))
        kpi(k[1], "Days Elapsed", str(days))
        kpi(k[2], "Daily Avg",    inr(tr/days if days else 0))
        kpi(k[3], "Walk-Ins",     num(tw))
    st.markdown("---")
    c1, c2 = st.columns([2,3])
    with c1:
        sec("Centre MTD Summary","🏢")
        cm = mtd_df.groupby("centre").agg(
            Walk_Ins=("walk_ins","sum"), SA=("sa","sum"), FL=("fl","sum"),
            FF=("ff","sum"), FH=("fh","sum"), L1=("l1","sum"), MTD_Rev=("total_rev","sum")
        ).reset_index().sort_values("MTD_Rev", ascending=False)
        cm["Daily Avg"] = (cm["MTD_Rev"]/days).apply(inr)
        fig = px.bar(cm, x="MTD_Rev", y="centre", orientation="h",
                     color="centre", color_discrete_sequence=CC, text=cm["MTD_Rev"].apply(inr))
        fig.update_traces(textposition="outside", textfont=dict(color=TEXT))
        chart(fig, h=280, showlegend=False, xaxis=ax(tickprefix="₹", tickformat=","), yaxis=ax())
        st.plotly_chart(fig, use_container_width=True)
        cm["MTD_Rev"] = cm["MTD_Rev"].apply(inr)
        st.dataframe(cm[["centre","MTD_Rev","Daily Avg"]].rename(
            columns={"centre":"Centre","MTD_Rev":"MTD Revenue"}),
            use_container_width=True, hide_index=True)
    with c2:
        sec("Daily Revenue Trend","📈")
        daily = mtd_df.groupby("date")["total_rev"].sum().reset_index()
        daily["cumulative"] = daily["total_rev"].cumsum()
        daily["ma3"] = daily["total_rev"].rolling(3, min_periods=1).mean()
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(x=daily["date"], y=daily["total_rev"], name="Daily Rev",
                              marker_color=BLUE, opacity=0.7), secondary_y=False)
        fig2.add_trace(go.Scatter(x=daily["date"], y=daily["ma3"], name="3-Day MA",
                                  line=dict(color=TEAL, width=2)), secondary_y=False)
        fig2.add_trace(go.Scatter(x=daily["date"], y=daily["cumulative"], name="Cumulative",
                                  line=dict(color=ORANGE, width=2.5, dash="dot"),
                                  mode="lines+markers", marker=dict(size=5)), secondary_y=True)
        fig2.update_layout(plot_bgcolor=PLOT_BG, paper_bgcolor=CARD_BG,
                           font=dict(color=TEXT), height=380, margin=dict(t=40,b=40,l=10,r=10),
                           legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"))
        fig2.update_yaxes(tickprefix="₹", tickformat=",", gridcolor=GRID,
                          color=TEXT, secondary_y=False)
        fig2.update_yaxes(tickprefix="₹", tickformat=",", gridcolor=GRID,
                          color=TEXT, secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 – FY / Quarterly
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[3]:
    st.markdown("## 📈 FY 2025-26 | Quarterly Report")
    qtrs   = ["Q1","Q2","Q3","Q4"]
    qtr_df = quarterly_by_centre(df)
    pivot  = qtr_df.pivot(index="centre", columns="quarter", values="total_rev").fillna(0)
    pivot  = pivot.reindex(columns=qtrs)
    pivot["FY Total"] = pivot.sum(axis=1)
    pivot["% of FY"]  = pivot["FY Total"] / pivot["FY Total"].sum() * 100
    pivot  = pivot.sort_values("FY Total", ascending=False)

    sec("Quarterly Revenue by Centre","📊")
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        for i, q in enumerate(qtrs):
            fig.add_trace(go.Bar(name=q, x=pivot.index, y=pivot[q],
                                 marker_color=CC[i],
                                 text=[inr(v) for v in pivot[q]],
                                 textposition="outside", textfont=dict(size=9, color=TEXT)))
        chart(fig, h=360, barmode="group",
              yaxis=ax(tickprefix="₹", tickformat=","), xaxis=ax())
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        qr = {q: df[df["quarter"]==q]["total_rev"].sum() for q in qtrs}
        qc = {q: cost_df["monthly_cost"].sum()*3 for q in qtrs}
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=qtrs, y=[qr[q] for q in qtrs], name="Revenue",
                                  mode="lines+markers+text",
                                  text=[inr(qr[q]) for q in qtrs],
                                  textposition="top center", textfont=dict(color=BLUE, size=11),
                                  line=dict(color=BLUE, width=3), marker=dict(size=12)))
        fig2.add_trace(go.Scatter(x=qtrs, y=[qr[q]-qc[q] for q in qtrs], name="Gross Profit",
                                  mode="lines+markers+text",
                                  text=[inr(qr[q]-qc[q]) for q in qtrs],
                                  textposition="bottom center", textfont=dict(color=GREEN, size=11),
                                  line=dict(color=GREEN, width=3, dash="dot"), marker=dict(size=12)))
        chart(fig2, h=360, yaxis=ax(tickprefix="₹", tickformat=","), xaxis=ax())
        st.plotly_chart(fig2, use_container_width=True)

    sec("Revenue Matrix","📋")
    dp = pivot.copy()
    for c in qtrs+["FY Total"]: dp[c] = dp[c].apply(inr)
    dp["% of FY"] = dp["% of FY"].apply(pct)
    st.dataframe(dp, use_container_width=True)

    sec("Quarterly P&L — All Centres","💰")
    rows = []
    for q in qtrs:
        g = qr[q]-qc[q]
        rows.append({"Quarter":q,"Revenue":inr(qr[q]),"Cost":inr(qc[q]),
                     "Gross Profit":inr(g),"GM %":pct(g/qr[q]*100 if qr[q] else 0)})
    fr = sum(qr.values()); fc2 = sum(qc.values()); fg = fr-fc2
    rows.append({"Quarter":"FY Total","Revenue":inr(fr),"Cost":inr(fc2),
                 "Gross Profit":inr(fg),"GM %":pct(fg/fr*100 if fr else 0)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 5 – Granular Metrics
# ══════════════════════════════════════════════════════════════════════════
elif page == pages[4]:
    st.markdown("## 🔬 Granular Operational Metrics")
    ctr_rev  = df.groupby("centre")["total_rev"].sum().reset_index()
    ctr_wi   = df.groupby("centre")["walk_ins"].sum().reset_index()
    ctr_days = df.groupby("centre")["date"].nunique().reset_index()
    ctr_days.columns = ["centre","working_days"]
    eff = ctr_rev.merge(cost_df, on="centre").merge(ctr_wi, on="centre").merge(ctr_days, on="centre")
    eff.rename(columns={"total_rev":"annual_rev"}, inplace=True)
    eff["cost_sq"]  = eff["annual_cost"] / eff["area"]
    eff["cost_pct"] = eff["annual_cost"] / eff["annual_rev"] * 100
    eff["rev_sq"]   = eff["annual_rev"]  / eff["area"]
    eff["rev_mbr"]  = eff["annual_rev"]  / eff["staff"]
    eff["rev_wi"]   = eff["annual_rev"]  / eff["walk_ins"]
    eff["rev_day"]  = eff["annual_rev"]  / eff["working_days"]
    eff["gm"]       = (eff["annual_rev"] - eff["annual_cost"]) / eff["annual_rev"] * 100

    sec("1. Revenue vs Cost per Centre","💰")
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Rev/Sqft", x=eff["centre"], y=eff["rev_sq"],
                             marker_color=BLUE,
                             text=[inr(v) for v in eff["rev_sq"]],
                             textposition="outside", textfont=dict(color=TEXT)))
        fig.add_trace(go.Bar(name="Cost/Sqft", x=eff["centre"], y=eff["cost_sq"],
                             marker_color=RED,
                             text=[inr(v) for v in eff["cost_sq"]],
                             textposition="outside", textfont=dict(color=TEXT)))
        chart(fig, h=320, barmode="group",
              yaxis=ax(tickprefix="₹", tickformat=","), xaxis=ax())
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="GM %", x=eff["centre"], y=eff["gm"],
                              marker_color=[GREEN if v>=95 else ORANGE if v>=90 else RED for v in eff["gm"]],
                              text=[pct(v) for v in eff["gm"]],
                              textposition="outside", textfont=dict(color=TEXT)))
        fig2.add_hline(y=95, line_dash="dot", line_color=GREEN,
                       annotation_text="95% target", annotation_font_color=GREEN)
        chart(fig2, h=320, showlegend=False,
              yaxis=ax(ticksuffix="%", range=[0,105]), xaxis=ax())
        st.plotly_chart(fig2, use_container_width=True)

    sec("2. Revenue Productivity","📈")
    prod = [("rev_sq","Rev/Sqft"),("rev_mbr","Rev/Member"),
            ("rev_wi","Rev/Walk-In"),("rev_day","Daily Rev")]
    cols = st.columns(4)
    for (fld, lbl), col in zip(prod, cols):
        f = go.Figure(go.Bar(x=eff["centre"], y=eff[fld], marker_color=CC,
                             text=[inr(v) for v in eff[fld]],
                             textposition="outside", textfont=dict(size=9, color=TEXT)))
        chart(f, h=240, showlegend=False,
              title=dict(text=lbl, font=dict(size=12, color=TEXT)),
              margin=dict(t=40,b=30,l=5,r=5),
              yaxis=ax(tickprefix="₹", tickformat=","), xaxis=ax())
        col.plotly_chart(f, use_container_width=True)

    sec("3. Actual vs Target Conversion","🎯")
    targets = [assumptions[k] for k in ["sa_rate","fl_rate","ff_rate","fh_rate","l1_rate"]]
    total_wi = df["walk_ins"].sum()
    actuals  = [df[c].sum()/total_wi for c in SVC_COLS]
    var      = [(a-t)*100 for a,t in zip(actuals,targets)]
    c1, c2 = st.columns([3,2])
    with c1:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(name="Target %", x=SERVICES, y=[t*100 for t in targets],
                              marker_color=MUTED, opacity=0.6))
        fig3.add_trace(go.Bar(name="Actual %", x=SERVICES, y=[a*100 for a in actuals],
                              marker_color=[GREEN if v>=0 else RED for v in var],
                              text=[f"{a*100:.1f}%" for a in actuals],
                              textposition="outside", textfont=dict(color=TEXT)))
        chart(fig3, h=320, barmode="group",
              yaxis=ax(ticksuffix="%"), xaxis=ax())
        st.plotly_chart(fig3, use_container_width=True)
    with c2:
        ct = pd.DataFrame({"Service":SERVICES,
                           "Target":[pct(t*100) for t in targets],
                           "Actual":[pct(a*100) for a in actuals],
                           "Variance":[f"{v:+.2f}pp" for v in var]})
        st.dataframe(ct, use_container_width=True, hide_index=True)

    sec("4. Service Revenue Heatmap","🗺️")
    heat = df.groupby("centre")[REV_COLS].sum()
    heat.columns = SERVICES
    heat_pct = heat.div(heat.sum(axis=1), axis=0)*100
    fig4 = px.imshow(heat_pct.round(1), color_continuous_scale="Blues",
                     aspect="auto", text_auto=".1f",
                     labels=dict(color="% of Centre Rev"))
    fig4.update_layout(plot_bgcolor=PLOT_BG, paper_bgcolor=CARD_BG,
                       font=dict(color=TEXT), height=300, margin=dict(t=20,b=20,l=10,r=10))
    st.plotly_chart(fig4, use_container_width=True)
