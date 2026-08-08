import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Hotel Booking Behaviour Dashboard",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "Data" / "hotel_bookings_data.csv"

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 14px 16px 8px 16px;
    }
    div[data-testid="stMetricLabel"] { font-size: 0.85rem; opacity: 0.75; }
    h1, h2, h3 { font-weight: 700; }
    .rec-card {
        background-color: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #FF4B4B;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .rec-card h4 { margin: 0 0 6px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# DATA LOADING & CLEANING (mirrors the notebook's pipeline)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df = df.drop_duplicates().copy()

    for col, fill in [("children", 0), ("agent", 0), ("company", 0)]:
        if col in df.columns:
            df[col] = df[col].fillna(fill)
    if "city" in df.columns:
        df["city"] = df["city"].fillna("Unknown")

    df["total_guests"] = (
        df.get("adults", 0) + df.get("children", 0) + df.get("babies", 0)
    )
    df = df[df["total_guests"] > 0].copy()

    df["total_stay"] = (
        df.get("stays_in_weekend_nights", 0) + df.get("stays_in_weekdays_nights", 0)
    )

    df["cancellation_status"] = df["is_canceled"].map(
        {0: "Not Cancelled", 1: "Cancelled"}
    )

    if "arrival_date_month" in df.columns:
        df["arrival_date_month"] = pd.Categorical(
            df["arrival_date_month"], categories=MONTH_ORDER, ordered=True
        )

    bins = [-1, 7, 30, 60, 90, 120, 180, 365, 1000]
    labels = [
        "0–7 Days", "8–30 Days", "31–60 Days", "61–90 Days",
        "91–120 Days", "121–180 Days", "181–365 Days", "365+ Days",
    ]
    df["lead_time_group"] = pd.cut(df["lead_time"], bins=bins, labels=labels)

    return df


if not DATA_PATH.exists():
    st.title("🏨 Hotel Booking Behaviour Dashboard")
    st.error(
        f"Data file not found at `Data/hotel_bookings_data.csv`.\n\n"
        f"Place your `hotel_bookings_data.csv` file inside a `Data/` folder "
        f"next to `app.py`, or upload it below."
    )
    uploaded = st.file_uploader("Upload hotel_bookings_data.csv", type="csv")
    if uploaded is not None:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_PATH, "wb") as f:
            f.write(uploaded.getbuffer())
        st.rerun()
    st.stop()

df_full = load_data(DATA_PATH)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.title("🏨 Filters")

hotel_options = sorted(df_full["hotel"].dropna().unique().tolist())
hotel_sel = st.sidebar.multiselect("Hotel Type", hotel_options, default=hotel_options)

months_present = [m for m in MONTH_ORDER if m in df_full["arrival_date_month"].dropna().unique().tolist()]
month_sel = st.sidebar.multiselect("Arrival Month", months_present, default=months_present)

if "market_segment" in df_full.columns:
    segment_options = sorted(df_full["market_segment"].dropna().unique().tolist())
    segment_sel = st.sidebar.multiselect("Market Segment", segment_options, default=segment_options)
else:
    segment_sel = None

cancel_sel = st.sidebar.multiselect(
    "Booking Status",
    ["Cancelled", "Not Cancelled"],
    default=["Cancelled", "Not Cancelled"],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Rows in dataset: {len(df_full):,}")

df = df_full[
    df_full["hotel"].isin(hotel_sel)
    & df_full["arrival_date_month"].isin(month_sel)
    & df_full["cancellation_status"].isin(cancel_sel)
]
if segment_sel is not None:
    df = df[df["market_segment"].isin(segment_sel)]

if df.empty:
    st.warning("No data matches the selected filters. Please widen your filter selection.")
    st.stop()

# ----------------------------------------------------------------------------
# HEADER + KPIs
# ----------------------------------------------------------------------------
st.title("🏨 Hotel Booking Behaviour Dashboard")
st.caption("Booking & cancellation behaviour analysis · 2017–2019")

total_bookings = len(df)
cancelled_bookings = int(df["is_canceled"].sum())
cancellation_rate = cancelled_bookings / total_bookings * 100
average_lead_time = df["lead_time"].mean()
average_stay = df["total_stay"].mean()
average_adr = df["adr"].mean()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Bookings", f"{total_bookings:,}")
k2.metric("Cancelled Bookings", f"{cancelled_bookings:,}")
k3.metric("Cancellation Rate", f"{cancellation_rate:.1f}%")
k4.metric("Avg Lead Time", f"{average_lead_time:.0f} days")
k5.metric("Avg Stay Length", f"{average_stay:.1f} nights")
k6.metric("Avg Daily Rate", f"${average_adr:.2f}")

st.markdown("---")

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Bookings Overview", "❌ Cancellation Analysis", "💰 Revenue & Segments", "💡 Recommendations"]
)

# ============================== TAB 1 ========================================
with tab1:
    col1, col2 = st.columns([1.3, 1])

    with col1:
        hotel_bookings = df["hotel"].value_counts().reset_index()
        hotel_bookings.columns = ["Hotel", "Bookings"]
        fig = px.bar(
            hotel_bookings, x="Hotel", y="Bookings", text="Bookings",
            title="Bookings by Hotel Type", color="Hotel",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            hotel_bookings, names="Hotel", values="Bookings", hole=0.55,
            title="Hotel Booking Share",
        )
        st.plotly_chart(fig, use_container_width=True)

    monthly_bookings = (
        df.groupby("arrival_date_month", observed=True).size().reset_index(name="Bookings")
    )
    fig = px.line(
        monthly_bookings, x="arrival_date_month", y="Bookings", markers=True,
        title="Monthly Booking Trend",
    )
    fig.update_layout(xaxis_title="Month", yaxis_title="Number of Bookings")
    st.plotly_chart(fig, use_container_width=True)

    monthly_hotel = (
        df.groupby(["arrival_date_month", "hotel"], observed=True)
        .size().reset_index(name="Bookings")
    )
    fig = px.line(
        monthly_hotel, x="arrival_date_month", y="Bookings", color="hotel",
        markers=True, title="Monthly Bookings by Hotel Type",
    )
    st.plotly_chart(fig, use_container_width=True)

    peak_month = monthly_bookings.loc[monthly_bookings["Bookings"].idxmax()]
    lowest_month = monthly_bookings.loc[monthly_bookings["Bookings"].idxmin()]
    c1, c2 = st.columns(2)
    c1.info(f"📈 **Peak month:** {peak_month['arrival_date_month']} ({peak_month['Bookings']:,} bookings)")
    c2.info(f"📉 **Lowest month:** {lowest_month['arrival_date_month']} ({lowest_month['Bookings']:,} bookings)")

# ============================== TAB 2 ========================================
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        cancellation_summary = df["cancellation_status"].value_counts().reset_index()
        cancellation_summary.columns = ["Status", "Bookings"]
        fig = px.pie(
            cancellation_summary, names="Status", values="Bookings", hole=0.55,
            title="Cancelled vs Non-Cancelled Bookings",
            color="Status",
            color_discrete_map={"Cancelled": "#FF4B4B", "Not Cancelled": "#2ECC71"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        hotel_cancellation = df.groupby("hotel")["is_canceled"].mean().reset_index()
        hotel_cancellation["Cancellation Rate"] = hotel_cancellation["is_canceled"] * 100
        fig = px.bar(
            hotel_cancellation, x="hotel", y="Cancellation Rate", text="Cancellation Rate",
            title="Cancellation Rate by Hotel Type", color="hotel",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    stay_cancellation = df.groupby("total_stay")["is_canceled"].mean().reset_index()
    stay_cancellation["Cancellation Rate"] = stay_cancellation["is_canceled"] * 100
    stay_cancellation = stay_cancellation[stay_cancellation["total_stay"] <= 30]
    fig = px.line(
        stay_cancellation, x="total_stay", y="Cancellation Rate", markers=True,
        title="Cancellation Rate vs Length of Stay",
    )
    fig.update_layout(xaxis_title="Length of Stay (Nights)", yaxis_title="Cancellation Rate (%)")
    st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        lead_analysis = (
            df.groupby("lead_time_group", observed=True)["is_canceled"].mean().reset_index()
        )
        lead_analysis["Cancellation Rate"] = lead_analysis["is_canceled"] * 100
        fig = px.bar(
            lead_analysis, x="lead_time_group", y="Cancellation Rate", text="Cancellation Rate",
            title="Cancellation Rate by Lead Time",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="Lead Time", yaxis_title="Cancellation Rate (%)")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.histogram(
            df, x="lead_time", color="hotel", nbins=50,
            title="Distribution of Booking Lead Time",
        )
        fig.update_layout(xaxis_title="Lead Time (Days)", yaxis_title="Number of Bookings")
        st.plotly_chart(fig, use_container_width=True)

# ============================== TAB 3 ========================================
with tab3:
    col1, col2 = st.columns(2)

    with col1:
        adr_by_hotel = df.groupby("hotel")["adr"].mean().reset_index()
        adr_by_hotel.columns = ["Hotel", "Average ADR"]
        fig = px.bar(
            adr_by_hotel, x="Hotel", y="Average ADR", text="Average ADR",
            title="Average Daily Rate by Hotel", color="Hotel",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "market_segment" in df.columns:
            segment_analysis = df["market_segment"].value_counts().reset_index()
            segment_analysis.columns = ["Market Segment", "Bookings"]
            fig = px.bar(
                segment_analysis, x="Market Segment", y="Bookings", text="Bookings",
                title="Bookings by Market Segment", color="Market Segment",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

    if "market_segment" in df.columns:
        seg_cancel = df.groupby("market_segment")["is_canceled"].mean().reset_index()
        seg_cancel["Cancellation Rate"] = seg_cancel["is_canceled"] * 100
        fig = px.bar(
            seg_cancel.sort_values("Cancellation Rate", ascending=False),
            x="market_segment", y="Cancellation Rate", text="Cancellation Rate",
            title="Cancellation Rate by Market Segment",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="Market Segment", yaxis_title="Cancellation Rate (%)", xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

# ============================== TAB 4 ========================================
with tab4:
    st.subheader("💡 Business Recommendations")
    st.caption("Auto-generated from the current filtered data & KPIs above.")

    hotel_bookings_full = df["hotel"].value_counts().reset_index()
    hotel_bookings_full.columns = ["Hotel", "Bookings"]
    top_hotel = hotel_bookings_full.iloc[0]["Hotel"]

    monthly_bookings_full = (
        df.groupby("arrival_date_month", observed=True).size().reset_index(name="Bookings")
    )
    peak_month = monthly_bookings_full.loc[monthly_bookings_full["Bookings"].idxmax()]
    lowest_month = monthly_bookings_full.loc[monthly_bookings_full["Bookings"].idxmin()]

    st.markdown(
        f"""
        <div class="rec-card">
        <h4>1. 📅 Peak Season Planning</h4>
        Bookings peak in <b>{peak_month['arrival_date_month']}</b> ({peak_month['Bookings']:,} bookings)
        and are lowest in <b>{lowest_month['arrival_date_month']}</b> ({lowest_month['Bookings']:,} bookings).
        Prepare additional staffing, inventory, and marketing campaigns ahead of the peak month,
        and run promotions or discounted packages to boost demand in the low season.
        </div>

        <div class="rec-card">
        <h4>2. ❌ Cancellation Management</h4>
        The overall cancellation rate is <b>{cancellation_rate:.1f}%</b>. Hotels should consider
        requiring deposits for higher-risk bookings, sending automated reminder messages before
        arrival, and offering flexible rescheduling instead of outright cancellation to retain revenue.
        </div>

        <div class="rec-card">
        <h4>3. ⏱️ Lead Time Strategy</h4>
        The average booking lead time is <b>{average_lead_time:.0f} days</b>. Bookings made far in
        advance tend to carry higher cancellation risk — send confirmation and reminder
        communications at key intervals (30/7/1 days before arrival) to reduce no-shows and late cancellations.
        </div>

        <div class="rec-card">
        <h4>4. 🛏️ Stay Duration Packages</h4>
        The average customer stays approximately <b>{average_stay:.1f} nights</b>. Hotels can design
        targeted packages (e.g. weekend getaways, week-long stays) around the most common stay
        lengths to increase conversion and average booking value.
        </div>

        <div class="rec-card">
        <h4>5. 🏨 Hotel Type Focus</h4>
        The most frequently booked hotel type is <b>{top_hotel}</b>. Concentrate marketing spend,
        loyalty offers, and inventory management on this hotel type while investigating why the
        other type underperforms — pricing, location, or amenities may need review.
        </div>

        <div class="rec-card">
        <h4>6. 💰 Revenue Optimization</h4>
        Average Daily Rate (ADR) across bookings is <b>${average_adr:.2f}</b>. Use dynamic pricing
        during peak months and high-demand segments, and consider upsell packages (breakfast,
        late checkout) for lower-ADR segments to lift overall revenue per booking.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.caption("Built with Streamlit & Plotly · Data covers 2017–2019 hotel bookings.")