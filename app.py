import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Hotel Analysis Dashboard", layout="wide")

st.title("🏨 Hotel Booking Analysis Dashboard")

# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader("Upload your dataset (CSV)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # -----------------------------
    # Data Preview
    # -----------------------------
    st.subheader("📊 Dataset Preview")
    st.dataframe(df.head())

    # -----------------------------
    # Basic Info
    # -----------------------------
    st.subheader("📌 Basic Information")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows", df.shape[0])
    col2.metric("Total Columns", df.shape[1])
    col3.metric("Missing Values", df.isnull().sum().sum())

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    st.sidebar.header("🔍 Filters")

    if "hotel" in df.columns:
        hotel_type = st.sidebar.multiselect(
            "Select Hotel Type",
            options=df["hotel"].unique(),
            default=df["hotel"].unique()
        )
        df = df[df["hotel"].isin(hotel_type)]

    if "arrival_date_year" in df.columns:
        year = st.sidebar.multiselect(
            "Select Year",
            options=df["arrival_date_year"].unique(),
            default=df["arrival_date_year"].unique()
        )
        df = df[df["arrival_date_year"].isin(year)]

    # -----------------------------
    # Charts Section
    # -----------------------------
    st.subheader("📈 Visual Insights")

    # 1. Booking Count by Hotel Type
    if "hotel" in df.columns:
        fig1 = px.histogram(df, x="hotel", title="Booking Count by Hotel Type")
        st.plotly_chart(fig1, use_container_width=True)

    # 2. ADR Distribution (Average Daily Rate)
    if "adr" in df.columns:
        fig2 = px.histogram(df, x="adr", nbins=50, title="ADR Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    # 3. Booking Status
    if "is_canceled" in df.columns:
        cancel_map = {0: "Not Canceled", 1: "Canceled"}
        df["Booking Status"] = df["is_canceled"].map(cancel_map)

        fig3 = px.pie(df, names="Booking Status", title="Cancellation Ratio")
        st.plotly_chart(fig3, use_container_width=True)

    # 4. Monthly Bookings Trend
    if "arrival_date_month" in df.columns:
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        df["arrival_date_month"] = pd.Categorical(
            df["arrival_date_month"], categories=month_order, ordered=True
        )

        monthly = df.groupby("arrival_date_month").size().reset_index(name="Bookings")

        fig4 = px.line(monthly, x="arrival_date_month", y="Bookings",
                       title="Monthly Booking Trend")
        st.plotly_chart(fig4, use_container_width=True)

    # -----------------------------
    # Raw Data Option
    # -----------------------------
    if st.checkbox("Show Full Dataset"):
        st.dataframe(df)

else:
    st.info("👆 Please upload a CSV file to get started.")