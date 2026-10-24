"""
Investment Portfolio Tracker — Streamlit App
Run: streamlit run portfolio_tracker.py

Required packages:
    pip install streamlit pandas numpy plotly requests
"""

import csv
import io
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
GREEN_DARK   = "#0d6e3f"
GREEN_MID    = "#22a86a"
GREEN_LIGHT  = "#56d9a0"
BLUE_DARK    = "#0a3d6b"
BLUE_MID     = "#1565c0"
BLUE_LIGHT   = "#42a5f5"
BG_PAGE      = "#f0f7f4"
BG_CARD      = "#ffffff"
TEXT_MAIN    = "#0d2618"
TEXT_MUTED   = "#4a7060"
RED          = "#c0392b"
AMBER        = "#e67e22"

CHART_PALETTE = [GREEN_MID, BLUE_MID, GREEN_LIGHT, BLUE_LIGHT,
                 GREEN_DARK, BLUE_DARK, "#80cbc4", "#a5d6a7"]

# ── S&P 500 CONSTITUENTS (ticker → company name) ──────────────────────────────
SP500 = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "AMZN": "Amazon", "GOOGL": "Alphabet (A)", "GOOG": "Alphabet (C)",
    "META": "Meta Platforms", "TSLA": "Tesla", "BRK.B": "Berkshire Hathaway",
    "AVGO": "Broadcom", "JPM": "JPMorgan Chase", "LLY": "Eli Lilly",
    "V": "Visa", "UNH": "UnitedHealth", "XOM": "ExxonMobil",
    "MA": "Mastercard", "JNJ": "Johnson & Johnson", "COST": "Costco",
    "HD": "Home Depot", "PG": "Procter & Gamble", "ABBV": "AbbVie",
    "BAC": "Bank of America", "KO": "Coca-Cola", "MRK": "Merck",
    "CVX": "Chevron", "CRM": "Salesforce", "ACN": "Accenture",
    "AMD": "Advanced Micro Devices", "PEP": "PepsiCo", "NFLX": "Netflix",
    "TMO": "Thermo Fisher", "ABT": "Abbott Laboratories", "ADBE": "Adobe",
    "WMT": "Walmart", "CSCO": "Cisco", "LIN": "Linde",
    "DIS": "Walt Disney", "MCD": "McDonald's", "NKE": "Nike",
    "IBM": "IBM", "INTC": "Intel", "GS": "Goldman Sachs",
    "CAT": "Caterpillar", "QCOM": "Qualcomm", "T": "AT&T",
    "VZ": "Verizon", "PFE": "Pfizer", "BA": "Boeing",
    "GE": "GE Aerospace", "AMGN": "Amgen",
}

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG_PAGE}; }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {BLUE_DARK} 0%, {GREEN_DARK} 100%);
    }}
    section[data-testid="stSidebar"] * {{ color: #e8f5e9 !important; }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stTextInput label {{
        color: #b2dfdb !important;
    }}

    .dash-header {{
        background: linear-gradient(135deg, {BLUE_DARK} 0%, {GREEN_DARK} 100%);
        padding: 28px 36px 20px;
        border-radius: 12px;
        margin-bottom: 24px;
        color: #fff;
    }}
    .dash-header h1 {{ font-size: 2rem; font-weight: 700; margin: 0; color: #fff; }}
    .dash-header p  {{ font-size: 0.95rem; margin: 6px 0 0; color: #b2dfdb; }}

    .metric-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
    .metric-card {{
        background: {BG_CARD};
        border-left: 5px solid {GREEN_MID};
        border-radius: 10px;
        padding: 18px 22px;
        flex: 1 1 160px;
        box-shadow: 0 1px 6px rgba(0,0,0,.06);
    }}
    .metric-card.blue  {{ border-left-color: {BLUE_MID}; }}
    .metric-card.red   {{ border-left-color: {RED}; }}
    .metric-card.amber {{ border-left-color: {AMBER}; }}
    .metric-card .label {{ font-size: 0.75rem; color: {TEXT_MUTED}; font-weight: 600;
                           text-transform: uppercase; letter-spacing: .05em; }}
    .metric-card .value {{ font-size: 1.9rem; font-weight: 700; color: {TEXT_MAIN}; line-height: 1.1; }}
    .metric-card .sub   {{ font-size: 0.8rem; color: {TEXT_MUTED}; margin-top: 2px; }}

    .section-title {{
        font-size: 1rem; font-weight: 700; color: {BLUE_DARK};
        border-bottom: 2px solid {GREEN_LIGHT};
        padding-bottom: 6px; margin-bottom: 16px;
    }}
    .insight {{
        background: #e8f5e9; border-left: 4px solid {GREEN_MID};
        border-radius: 6px; padding: 12px 16px;
        font-size: 0.88rem; color: {GREEN_DARK}; margin-top: 10px;
    }}
    .insight.blue {{ background: #e3f2fd; border-left-color: {BLUE_MID}; color: {BLUE_DARK}; }}
    .gain  {{ color: {GREEN_MID}; font-weight: 600; }}
    .loss  {{ color: {RED};       font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []   # list of position dicts


# ── HELPERS ───────────────────────────────────────────────────────────────────

def fig_style(fig, title=""):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=BLUE_DARK)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_MAIN),
        margin=dict(t=40, b=20, l=10, r=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e0ece6", linecolor="#c8ddd4")
    fig.update_yaxes(showgrid=True, gridcolor="#e0ece6", linecolor="#c8ddd4")
    return fig


def metric_card_html(label, value, sub="", variant="green"):
    cls = "metric-card" if variant == "green" else f"metric-card {variant}"
    return (
        f"<div class='{cls}'>"
        f"<div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>"
        f"<div class='sub'>{sub}</div>"
        f"</div>"
    )


def fetch_price_yf(ticker: str) -> float | None:
    """Try Yahoo Finance v8 JSON endpoint (no API key required)."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=6)
        data = r.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(float(price), 4)
    except Exception:
        return None


def color_pct(val: float) -> str:
    return f"<span class='gain'>+{val:.2f}%</span>" if val >= 0 else f"<span class='loss'>{val:.2f}%</span>"


def color_dollar(val: float) -> str:
    sign = "+" if val >= 0 else ""
    css  = "gain" if val >= 0 else "loss"
    return f"<span class='{css}'>{sign}${val:,.2f}</span>"


def portfolio_to_df() -> pd.DataFrame:
    if not st.session_state.portfolio:
        return pd.DataFrame()
    rows = []
    for p in st.session_state.portfolio:
        cost        = p["buy_price"] * p["shares"]
        curr_price  = p.get("current_price", p["buy_price"])
        mkt_value   = curr_price * p["shares"]
        gain_dollar = mkt_value - cost
        gain_pct    = (gain_dollar / cost * 100) if cost else 0.0
        rows.append({
            "Ticker":         p["ticker"],
            "Company":        p.get("company", ""),
            "Shares":         p["shares"],
            "Buy Price":      p["buy_price"],
            "Current Price":  curr_price,
            "Cost Basis":     round(cost, 2),
            "Market Value":   round(mkt_value, 2),
            "Gain/Loss ($)":  round(gain_dollar, 2),
            "Gain/Loss (%)":  round(gain_pct, 2),
            "Date Added":     p.get("date_added", ""),
        })
    return pd.DataFrame(rows)


def save_to_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


def load_portfolio_from_csv(uploaded_file) -> list:
    """Parse an uploaded CSV into portfolio positions."""
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    positions = []
    required = {"Ticker", "Shares", "Buy Price"}
    if not required.issubset(set(df.columns)):
        st.error(f"CSV must contain columns: {required}. Found: {list(df.columns)}")
        return []
    for _, row in df.iterrows():
        ticker = str(row["Ticker"]).strip().upper()
        positions.append({
            "ticker":        ticker,
            "company":       SP500.get(ticker, str(row.get("Company", ""))),
            "shares":        float(row["Shares"]),
            "buy_price":     float(row["Buy Price"]),
            "current_price": float(row["Current Price"]) if "Current Price" in df.columns else float(row["Buy Price"]),
            "date_added":    str(row.get("Date Added", datetime.now().strftime("%Y-%m-%d"))),
        })
    return positions


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📁 Import Portfolio CSV")
    uploaded = st.file_uploader(
        "Upload a portfolio CSV",
        type=["csv"],
        help="Columns: Ticker, Shares, Buy Price (optional: Company, Current Price, Date Added)",
    )
    if uploaded and st.button("Load CSV into portfolio"):
        loaded = load_portfolio_from_csv(uploaded)
        if loaded:
            st.session_state.portfolio = loaded
            st.success(f"Loaded {len(loaded)} positions.")

    st.markdown("---")
    st.markdown("## ➕ Add Position")

    all_tickers = sorted(SP500.keys())
    ticker_sel  = st.selectbox("Ticker (S&P 500)", all_tickers, index=all_tickers.index("AAPL"))
    custom_tick = st.text_input("Or type any ticker", placeholder="e.g. PLTR")
    ticker_final = custom_tick.strip().upper() if custom_tick.strip() else ticker_sel

    buy_price = st.number_input("Buy Price ($ per share)", min_value=0.01, value=150.00, step=0.01, format="%.2f")
    shares    = st.number_input("Shares Owned", min_value=0.001, value=10.0, step=0.001, format="%.3f")

    if st.button("Add to Portfolio", type="primary"):
        if any(p["ticker"] == ticker_final for p in st.session_state.portfolio):
            st.warning(f"{ticker_final} is already in your portfolio.")
        else:
            with st.spinner(f"Fetching price for {ticker_final}…"):
                live_price = fetch_price_yf(ticker_final)
            if live_price is None:
                live_price = buy_price
                st.info(f"Could not fetch live price — using buy price as estimate.")
            else:
                st.success(f"Live price: ${live_price:,.2f}")
            st.session_state.portfolio.append({
                "ticker":        ticker_final,
                "company":       SP500.get(ticker_final, ticker_final),
                "shares":        shares,
                "buy_price":     buy_price,
                "current_price": live_price,
                "date_added":    datetime.now().strftime("%Y-%m-%d"),
            })

    st.markdown("---")
    if st.button("↻ Refresh All Prices"):
        with st.spinner("Refreshing prices…"):
            for p in st.session_state.portfolio:
                price = fetch_price_yf(p["ticker"])
                if price:
                    p["current_price"] = price
        st.success("Prices updated.")

    if st.session_state.portfolio:
        st.markdown("---")
        st.markdown("## 🗑️ Remove Position")
        tickers_in  = [p["ticker"] for p in st.session_state.portfolio]
        to_remove   = st.selectbox("Remove:", tickers_in)
        if st.button("Remove"):
            st.session_state.portfolio = [
                p for p in st.session_state.portfolio if p["ticker"] != to_remove
            ]
            st.success(f"Removed {to_remove}.")

    st.markdown("---")
    st.markdown(
        "<span style='font-size:0.78rem;opacity:.7'>Green/Blue palette · "
        "Powered by Streamlit & Plotly</span>",
        unsafe_allow_html=True,
    )

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="dash-header">
        <h1>📈 Investment Portfolio Tracker</h1>
        <p>Track holdings · Compute gain / loss · Export transaction summary</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── EMPTY STATE ───────────────────────────────────────────────────────────────
if not st.session_state.portfolio:
    st.info(
        "No positions yet. Add stocks using the sidebar, or upload a portfolio CSV. "
        "A sample CSV can have columns: Ticker, Company, Shares, Buy Price, Current Price, Date Added."
    )
    st.stop()

# ── BUILD DATAFRAME ───────────────────────────────────────────────────────────
df = portfolio_to_df()

total_invested = df["Cost Basis"].sum()
total_value    = df["Market Value"].sum()
total_gain     = total_value - total_invested
gain_pct       = (total_gain / total_invested * 100) if total_invested else 0.0
best_row       = df.loc[df["Gain/Loss (%)"].idxmax()]
worst_row      = df.loc[df["Gain/Loss (%)"].idxmin()]

# ── KPI METRICS ───────────────────────────────────────────────────────────────
cards = "<div class='metric-row'>"
cards += metric_card_html("Total Invested",    f"${total_invested:,.2f}", f"{len(df)} holdings")
cards += metric_card_html("Market Value",      f"${total_value:,.2f}", f"{df['Shares'].sum():,.2f} shares", "blue")
gain_variant = "green" if total_gain >= 0 else "red"
cards += metric_card_html(
    "Total Gain / Loss",
    f"{'+'if total_gain>=0 else ''}${total_gain:,.2f}",
    f"{'+'if gain_pct>=0 else ''}{gain_pct:.2f}% all-time",
    gain_variant,
)
cards += metric_card_html(
    "Best Performer",
    best_row["Ticker"],
    f"+{best_row['Gain/Loss (%)']:.2f}%",
    "green",
)
cards += metric_card_html(
    "Worst Performer",
    worst_row["Ticker"],
    f"{worst_row['Gain/Loss (%)']:.2f}%",
    "red" if worst_row["Gain/Loss (%)"] < 0 else "blue",
)
cards += "</div>"
st.markdown(cards, unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_holdings, tab_charts, tab_export = st.tabs(["Holdings", "Charts", "Export"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HOLDINGS TABLE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_holdings:
    st.markdown("<div class='section-title'>Portfolio positions</div>", unsafe_allow_html=True)

    display = df.copy()
    display["Gain/Loss ($)"] = display["Gain/Loss ($)"].apply(
        lambda v: f"{'+'if v>=0 else ''}${v:,.2f}"
    )
    display["Gain/Loss (%)"] = display["Gain/Loss (%)"].apply(
        lambda v: f"{'+'if v>=0 else ''}{v:.2f}%"
    )
    display["Buy Price"]     = display["Buy Price"].apply(lambda v: f"${v:,.2f}")
    display["Current Price"] = display["Current Price"].apply(lambda v: f"${v:,.2f}")
    display["Cost Basis"]    = display["Cost Basis"].apply(lambda v: f"${v:,.2f}")
    display["Market Value"]  = display["Market Value"].apply(lambda v: f"${v:,.2f}")

    st.dataframe(display, use_container_width=True, hide_index=True, height=380)

    # Summary footer
    st.markdown(
        f"<div class='insight'>"
        f"Total invested: <strong>${total_invested:,.2f}</strong> &nbsp;|&nbsp; "
        f"Current value: <strong>${total_value:,.2f}</strong> &nbsp;|&nbsp; "
        f"Net P&amp;L: <strong>{'+'if total_gain>=0 else ''}${total_gain:,.2f} ({gain_pct:+.2f}%)</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CHARTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_charts:
    col1, col2 = st.columns(2)

    # Portfolio allocation donut
    with col1:
        st.markdown("<div class='section-title'>Allocation by market value</div>", unsafe_allow_html=True)
        fig_pie = go.Figure(go.Pie(
            labels=df["Ticker"],
            values=df["Market Value"],
            hole=0.5,
            marker_colors=CHART_PALETTE,
            textinfo="label+percent",
            hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Gain/loss bar
    with col2:
        st.markdown("<div class='section-title'>Gain / loss per holding</div>", unsafe_allow_html=True)
        bar_df = df.sort_values("Gain/Loss (%)")
        colors = [GREEN_MID if v >= 0 else RED for v in bar_df["Gain/Loss (%)"]]
        fig_bar = go.Figure(go.Bar(
            x=bar_df["Ticker"],
            y=bar_df["Gain/Loss (%)"],
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in bar_df["Gain/Loss (%)"]],
            textposition="outside",
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        ))
        fig_bar = fig_style(fig_bar)
        fig_bar.update_layout(yaxis_title="Return (%)", xaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Cost basis vs market value comparison
    st.markdown("<div class='section-title'>Cost basis vs market value</div>", unsafe_allow_html=True)
    comp_df = df[["Ticker", "Cost Basis", "Market Value"]].melt(
        id_vars="Ticker", var_name="Type", value_name="Value"
    )
    fig_comp = px.bar(
        comp_df, x="Ticker", y="Value", color="Type", barmode="group",
        color_discrete_map={"Cost Basis": BLUE_MID, "Market Value": GREEN_MID},
        labels={"Value": "USD ($)"},
    )
    fig_comp = fig_style(fig_comp)
    st.plotly_chart(fig_comp, use_container_width=True)

    # P&L waterfall
    st.markdown("<div class='section-title'>P&L waterfall</div>", unsafe_allow_html=True)
    wf_tickers = list(df["Ticker"]) + ["Total"]
    wf_values  = list(df["Gain/Loss ($)"]) + [total_gain]
    wf_types   = ["relative"] * len(df) + ["total"]
    wf_colors  = [GREEN_MID if v >= 0 else RED for v in df["Gain/Loss ($)"]]
    wf_colors.append(BLUE_MID)

    fig_wf = go.Figure(go.Waterfall(
        x=wf_tickers,
        y=wf_values,
        measure=wf_types,
        text=[f"${v:+,.0f}" for v in wf_values],
        textposition="outside",
        connector=dict(line=dict(color=TEXT_MUTED, width=1, dash="dot")),
        increasing=dict(marker_color=GREEN_MID),
        decreasing=dict(marker_color=RED),
        totals=dict(marker_color=BLUE_MID),
    ))
    fig_wf = fig_style(fig_wf)
    fig_wf.update_layout(yaxis_title="Gain / Loss ($)")
    st.plotly_chart(fig_wf, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_export:
    st.markdown("<div class='section-title'>Export portfolio summary</div>", unsafe_allow_html=True)

    export_df = df.copy()
    export_df["Export Date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    st.dataframe(export_df, use_container_width=True, hide_index=True)

    csv_bytes = save_to_csv(export_df)
    filename  = f"portfolio_summary_{datetime.now().strftime('%Y-%m-%d')}.csv"

    st.download_button(
        label="⬇ Download portfolio_summary.csv",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
    )

    st.markdown("---")
    st.markdown("<div class='section-title'>Sample CSV template</div>", unsafe_allow_html=True)
    st.markdown(
        "Use the template below to prepare a CSV you can upload in the sidebar:"
    )
    template = pd.DataFrame({
        "Ticker":        ["AAPL", "MSFT", "NVDA"],
        "Company":       ["Apple Inc.", "Microsoft", "Nvidia"],
        "Shares":        [10, 5, 8],
        "Buy Price":     [150.00, 280.00, 450.00],
        "Current Price": [175.00, 310.00, 480.00],
        "Date Added":    ["2024-01-15", "2024-02-20", "2024-03-10"],
    })
    st.dataframe(template, use_container_width=True, hide_index=True)
    st.download_button(
        label="⬇ Download CSV template",
        data=save_to_csv(template),
        file_name="portfolio_template.csv",
        mime="text/csv",
    )
