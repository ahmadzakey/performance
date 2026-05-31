
import streamlit as st
import pandas as pd
import numpy as np


def money_card(label, value):
    st.markdown(
        f"""
        <div style="
            padding:16px 18px;
            border:1px solid #e5e7eb;
            border-radius:14px;
            background:#ffffff;
            min-height:92px;
            margin-bottom:12px;
        ">
            <div style="font-size:13px;color:#6b7280;margin-bottom:8px;">
                {label}
            </div>
            <div style="
                font-size:22px;
                font-weight:700;
                color:#111827;
                line-height:1.2;
                white-space:nowrap;
                overflow:visible;
            ">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def clean_finance_df(df):
    df = df.copy()

    df["txn_date"] = pd.to_datetime(df["txn_date"], dayfirst=True, errors="coerce")
    df["income_amt_rm"] = pd.to_numeric(df["income_amt_rm"], errors="coerce").fillna(0)
    df["spend_amt_rm"] = pd.to_numeric(df["spend_amt_rm"], errors="coerce").fillna(0)

    text_cols = [
        "txn_type", "income_cat", "income_cat_detail",
        "product_type", "ASSET_OWNER_CODE",
        "spend_type", "remarks", "day_type"
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
            )

    df = df.dropna(subset=["txn_date"])
    df["month_period"] = df["txn_date"].dt.to_period("M")
    df["month_name"] = df["month_period"].astype(str)

    return df


def sidebar_filter(label, col, data):
    if col not in data.columns:
        return data

    options = sorted(data[col].dropna().unique())

    selected = st.sidebar.multiselect(
        label,
        options=options,
        default=options
    )

    if selected:
        return data[data[col].isin(selected)]

    return data


def render_finance_dashboard(df):

    st.title("📊 Finance Monitoring Dashboard")

    df = clean_finance_df(df)

    st.sidebar.header("🔎 Report Filter")

    min_date = df["txn_date"].min().date()
    max_date = df["txn_date"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        df = df[
            (df["txn_date"].dt.date >= start_date)
            & (df["txn_date"].dt.date <= end_date)
        ]

    df = sidebar_filter("Transaction Type", "txn_type", df)
    df = sidebar_filter("Income Category", "income_cat", df)
    df = sidebar_filter("Income Detail", "income_cat_detail", df)
    df = sidebar_filter("Product Type", "product_type", df)
    df = sidebar_filter("Spend Type", "spend_type", df)
    df = sidebar_filter("Day Type", "day_type", df)

    if df.empty:
        st.warning("Tiada data untuk filter yang dipilih.")
        return {}

    income_df = df[df["txn_type"].str.lower().eq("pendapatan")].copy()
    expense_df = df[df["txn_type"].str.lower().eq("perbelanjaan")].copy()

    rental_df = income_df[
        income_df["income_cat_detail"].str.lower().eq("pendapatan sewaan")
    ].copy()

    tab1, tab2 = st.tabs([
        "💰 Personal Finance Summary",
        "📷 EasyKamera Rental Summary"
    ])

    # =====================================================
    # TAB 1: PERSONAL FINANCE
    # =====================================================
    with tab1:

        st.subheader("1) Overall Performance")

        total_income = income_df["income_amt_rm"].sum()
        total_expense = expense_df["spend_amt_rm"].sum()
        net = total_income - total_expense

        c1, c2 = st.columns(2)
        with c1:
            money_card("Total Income", f"RM{total_income:,.2f}")
        with c2:
            money_card("Total Expense", f"RM{total_expense:,.2f}")

        c3, c4 = st.columns(2)
        with c3:
            money_card("Net", f"RM{net:,.2f}")
        with c4:
            money_card("Total Rows", f"{len(df):,}")

        c5, c6 = st.columns(2)
        with c5:
            money_card("Income Txns", f"{len(income_df):,}")
        with c6:
            money_card("Expense Txns", f"{len(expense_df):,}")

        st.caption(
            f"Data period: {df['txn_date'].min().date()} hingga {df['txn_date'].max().date()}"
        )

        st.subheader("2) Monthly Trend: Income vs Expense")

        monthly_income = (
            income_df.groupby("month_period", as_index=False)
            .agg(
                total_income_rm=("income_amt_rm", "sum"),
                income_txn=("income_amt_rm", "count"),
                avg_income_rm=("income_amt_rm", "mean")
            )
        )

        monthly_income["month_name"] = monthly_income["month_period"].astype(str)

        monthly_expense = (
            expense_df.groupby("month_period", as_index=False)
            .agg(
                total_expense_rm=("spend_amt_rm", "sum"),
                expense_txn=("spend_amt_rm", "count"),
                avg_expense_rm=("spend_amt_rm", "mean")
            )
        )

        monthly_expense["month_name"] = monthly_expense["month_period"].astype(str)

        monthly = (
            pd.merge(
                monthly_income,
                monthly_expense,
                on=["month_period", "month_name"],
                how="outer"
            )
            .fillna(0)
            .sort_values("month_period")
            .reset_index(drop=True)
        )

        monthly["net_rm"] = monthly["total_income_rm"] - monthly["total_expense_rm"]
        monthly["prev_month_income"] = monthly["total_income_rm"].shift(1)
        monthly["mom_growth_rm"] = monthly["total_income_rm"] - monthly["prev_month_income"]

        monthly["mom_growth_pct"] = np.where(
            monthly["prev_month_income"].fillna(0) == 0,
            np.nan,
            monthly["mom_growth_rm"] / monthly["prev_month_income"] * 100
        )

        st.line_chart(
            monthly.set_index("month_name")[
                ["total_income_rm", "total_expense_rm", "net_rm"]
            ]
        )

        st.dataframe(
            monthly[
                [
                    "month_name",
                    "total_income_rm",
                    "income_txn",
                    "avg_income_rm",
                    "total_expense_rm",
                    "expense_txn",
                    "avg_expense_rm",
                    "net_rm",
                    "mom_growth_rm",
                    "mom_growth_pct",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("3) Income Breakdown by Category")

        income_by_cat = (
            income_df.groupby("income_cat", dropna=False, as_index=False)
            .agg(
                total_income_rm=("income_amt_rm", "sum"),
                txn_count=("income_amt_rm", "count")
            )
            .sort_values("total_income_rm", ascending=False)
        )

        income_by_cat["contribution_pct"] = np.where(
            income_by_cat["total_income_rm"].sum() == 0,
            0,
            income_by_cat["total_income_rm"]
            / income_by_cat["total_income_rm"].sum()
            * 100
        )

        st.dataframe(income_by_cat, use_container_width=True, hide_index=True)

        st.subheader("4) Income Breakdown by Detail")

        income_by_detail = (
            income_df.groupby(
                ["income_cat", "income_cat_detail"],
                dropna=False,
                as_index=False
            )
            .agg(
                total_income_rm=("income_amt_rm", "sum"),
                txn_count=("income_amt_rm", "count")
            )
            .sort_values("total_income_rm", ascending=False)
        )

        income_by_detail["contribution_pct"] = np.where(
            income_by_detail["total_income_rm"].sum() == 0,
            0,
            income_by_detail["total_income_rm"]
            / income_by_detail["total_income_rm"].sum()
            * 100
        )

        st.dataframe(income_by_detail, use_container_width=True, hide_index=True)

        st.subheader("5) Expense Breakdown by Spend Type")

        exp_by_type = (
            expense_df.groupby("spend_type", dropna=False, as_index=False)
            .agg(
                total_expense_rm=("spend_amt_rm", "sum"),
                txn_count=("spend_amt_rm", "count"),
                avg_expense_rm=("spend_amt_rm", "mean")
            )
            .sort_values("total_expense_rm", ascending=False)
        )

        exp_by_type["contribution_pct"] = np.where(
            exp_by_type["total_expense_rm"].sum() == 0,
            0,
            exp_by_type["total_expense_rm"]
            / exp_by_type["total_expense_rm"].sum()
            * 100
        )

        st.dataframe(exp_by_type, use_container_width=True, hide_index=True)

    # =====================================================
    # TAB 2: EASYKAMERA RENTAL
    # =====================================================
    with tab2:

        st.subheader("1) Rental Overall Performance")

        rental_income = rental_df["income_amt_rm"].sum()
        rental_txn = len(rental_df)
        avg_rental = rental_df["income_amt_rm"].mean() if rental_txn > 0 else 0
        median_rental = rental_df["income_amt_rm"].median() if rental_txn > 0 else 0

        r1, r2 = st.columns(2)
        with r1:
            money_card("Rental Income", f"RM{rental_income:,.2f}")
        with r2:
            money_card("Rental Txns", f"{rental_txn:,}")

        r3, r4 = st.columns(2)
        with r3:
            money_card("Avg Rental", f"RM{avg_rental:,.2f}")
        with r4:
            money_card("Median Rental", f"RM{median_rental:,.2f}")

        st.subheader("2) Monthly Rental Trend")

        rental_monthly = (
            rental_df.groupby("month_period", as_index=False)
            .agg(
                total_income_rm=("income_amt_rm", "sum"),
                txn_count=("income_amt_rm", "count"),
                avg_per_txn_rm=("income_amt_rm", "mean")
            )
            .sort_values("month_period")
        )

        rental_monthly["month_name"] = rental_monthly["month_period"].astype(str)
        rental_monthly["prev_month_income"] = rental_monthly["total_income_rm"].shift(1)
        rental_monthly["mom_growth_rm"] = (
            rental_monthly["total_income_rm"]
            - rental_monthly["prev_month_income"]
        )

        rental_monthly["mom_growth_pct"] = np.where(
            rental_monthly["prev_month_income"].fillna(0) == 0,
            np.nan,
            rental_monthly["mom_growth_rm"]
            / rental_monthly["prev_month_income"]
            * 100
        )

        st.line_chart(
            rental_monthly.set_index("month_name")[["total_income_rm"]]
        )

        st.dataframe(
            rental_monthly,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("3) Product Performance")

        product_perf = (
            rental_df.groupby("product_type", dropna=False, as_index=False)
            .agg(
                total_income_rm=("income_amt_rm", "sum"),
                txn_count=("income_amt_rm", "count"),
                avg_income_rm=("income_amt_rm", "mean")
            )
            .sort_values("total_income_rm", ascending=False)
        )

        product_perf["contribution_pct"] = np.where(
            product_perf["total_income_rm"].sum() == 0,
            0,
            product_perf["total_income_rm"]
            / product_perf["total_income_rm"].sum()
            * 100
        )

        st.dataframe(product_perf, use_container_width=True, hide_index=True)

        st.subheader("4) Monthly Product Performance")

        monthly_product = (
            rental_df.groupby(["month_period", "product_type"], dropna=False)
            .agg(
                prod_income_rm=("income_amt_rm", "sum"),
                prod_txn_count=("income_amt_rm", "count"),
                prod_avg_rm=("income_amt_rm", "mean")
            )
            .reset_index()
            .sort_values(
                ["month_period", "prod_income_rm"],
                ascending=[True, False]
            )
        )

        monthly_product["month_name"] = monthly_product["month_period"].astype(str)

        st.dataframe(monthly_product, use_container_width=True, hide_index=True)

        st.subheader("5) Pivot: Product Income by Month")

        pivot_income = (
            monthly_product.pivot_table(
                index="month_name",
                columns="product_type",
                values="prod_income_rm",
                aggfunc="sum",
                fill_value=0
            )
            .reset_index()
        )

        st.dataframe(pivot_income, use_container_width=True, hide_index=True)
        st.bar_chart(pivot_income.set_index("month_name"))

    return {
        "filtered_df": df,
        "income_df": income_df,
        "expense_df": expense_df,
        "rental_df": rental_df,
    }