# Leverage Edu – Experience Centres FC Dashboard

A Streamlit-based Financial Control (FC) dashboard for Leverage Edu's 6 offline experience centres across India.

## Features

| Page | Description |
|------|-------------|
| 📊 Executive Dashboard | KPI tiles, MoM revenue chart, Centre P&L, Service mix |
| 📅 Day Report | Pick any date → centre-wise and service-wise daily performance |
| 📆 MTD Report | MTD revenue up to selected date + daily trend |
| 📈 FY / Quarterly | Q1–Q4 revenue matrix, P&L, trend charts |
| 🔬 Granular Metrics | Cost/sqft, Rev/member, conversion efficiency, heatmap |

## Assumptions (all editable in sidebar)

- 6 Centres: Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Pune
- Study Abroad ticket size (X) = ₹1,50,000
- Ancillary multipliers: Fly Loans 7%, Fly Forex 2%, Fly Homes 12%, Leverage 1 60%
- Conversion rates: SA 30%, Ancillary 40%, L1 10%
- Working days: Mon–Sat (FY Apr-25 to Mar-26)

## Local Setup

```bash
git clone https://github.com/<your-username>/leverage-edu-fc-dashboard.git
cd leverage-edu-fc-dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub → select repo → set `app.py` as main file
4. Click **Deploy**

## Project Structure

```
├── app.py              # Main Streamlit app (5 pages)
├── data_engine.py      # Data generation & aggregation logic
├── requirements.txt
└── .streamlit/
    └── config.toml     # Theme config
```
