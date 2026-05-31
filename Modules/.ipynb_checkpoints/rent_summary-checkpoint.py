import pandas as pd
import numpy as np

def easykamera_rental_summary(df, df_list=None, show=True):

    df = df.copy()

    # ======================
    # Cleaning
    # ======================
    df["txn_date"] = pd.to_datetime(df["txn_date"], dayfirst=True, errors="coerce")
    df["txn_type"] = df["txn_type"].astype(str).str.strip()
    df["income_cat"] = df["income_cat"].astype(str).str.strip()
    df["income_cat_detail"] = df["income_cat_detail"].astype(str).str.strip()
    df["income_amt_rm"] = pd.to_numeric(df["income_amt_rm"], errors="coerce")

    # ======================
    # Filter rental EasyKamera
    # ======================
    df_analysis = df[
        df["txn_type"].str.lower().eq("pendapatan")
        & df["income_cat_detail"].str.lower().eq("pendapatan sewaan")
    ].copy()

    df_analysis["txn_date"] = pd.to_datetime(df_analysis["txn_date"], dayfirst=True, errors="coerce")
    df_analysis["income_amt_rm"] = pd.to_numeric(df_analysis["income_amt_rm"], errors="coerce").fillna(0)

    df_analysis["product_type"] = (
        df_analysis["product_type"]
        .astype("string")
        .replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
        .str.strip()
    )

    required_cols = ["txn_date", "income_amt_rm", "product_type"]
    missing = [c for c in required_cols if c not in df_analysis.columns]

    if missing:
        raise KeyError(f"Missing columns in df_analysis: {missing}. Available: {df_analysis.columns.tolist()}")

    # ======================
    # Monthly income
    # ======================
    df_analysis["month_period"] = df_analysis["txn_date"].dt.to_period("M")

    monthly_income = (
        df_analysis
        .groupby("month_period")
        .agg(
            total_income_rm=("income_amt_rm", "sum"),
            txn_count=("income_amt_rm", "count"),
            avg_per_txn_rm=("income_amt_rm", "mean")
        )
        .reset_index()
        .sort_values("month_period")
        .reset_index(drop=True)
    )

    monthly_income["month_name"] = monthly_income["month_period"].astype(str)
    monthly_income["prev_month_income"] = monthly_income["total_income_rm"].shift(1)
    monthly_income["mom_growth_rm"] = monthly_income["total_income_rm"] - monthly_income["prev_month_income"]

    monthly_income["mom_growth_pct"] = np.where(
        monthly_income["prev_month_income"].fillna(0) == 0,
        np.nan,
        monthly_income["mom_growth_rm"] / monthly_income["prev_month_income"] * 100
    )

    # ======================
    # Product performance
    # ======================
    product_perf = (
        df_analysis
        .groupby("product_type")["income_amt_rm"]
        .agg(
            total_income_rm="sum",
            txn_count="count",
            avg_income_rm="mean"
        )
        .reset_index()
        .sort_values("total_income_rm", ascending=False)
    )

    product_perf["contribution_pct"] = np.where(
        product_perf["total_income_rm"].sum() == 0,
        0,
        product_perf["total_income_rm"] / product_perf["total_income_rm"].sum() * 100
    )

    # ======================
    # Monthly product
    # ======================
    monthly_product = (
        df_analysis
        .groupby(["month_period", "product_type"])
        .agg(
            prod_income_rm=("income_amt_rm", "sum"),
            prod_txn_count=("income_amt_rm", "count"),
            prod_avg_rm=("income_amt_rm", "mean"),
            prod_median_rm=("income_amt_rm", "median"),
            prod_min_rm=("income_amt_rm", "min"),
            prod_max_rm=("income_amt_rm", "max"),
        )
        .reset_index()
        .sort_values(["month_period", "prod_income_rm"], ascending=[True, False])
        .reset_index(drop=True)
    )

    monthly_product["month_name"] = monthly_product["month_period"].astype(str)

    month_total = (
        monthly_product
        .groupby("month_period", as_index=False)["prod_income_rm"]
        .sum()
        .rename(columns={"prod_income_rm": "month_total_income_rm"})
    )

    monthly_product = monthly_product.merge(month_total, on="month_period", how="left")

    monthly_product["prod_contribution_pct"] = np.where(
        monthly_product["month_total_income_rm"].fillna(0) == 0,
        0,
        monthly_product["prod_income_rm"] / monthly_product["month_total_income_rm"] * 100
    )

    monthly_product = monthly_product.sort_values(["product_type", "month_period"]).copy()

    monthly_product["prod_prev_income_rm"] = (
        monthly_product
        .groupby("product_type")["prod_income_rm"]
        .shift(1)
    )

    monthly_product["prod_mom_growth_rm"] = (
        monthly_product["prod_income_rm"]
        - monthly_product["prod_prev_income_rm"]
    )

    monthly_product["prod_mom_growth_pct"] = np.where(
        monthly_product["prod_prev_income_rm"].fillna(0) == 0,
        np.nan,
        monthly_product["prod_mom_growth_rm"] / monthly_product["prod_prev_income_rm"] * 100
    )

    # ======================
    # Pivot
    # ======================
    pivot_contrib_pct = (
        monthly_product
        .pivot_table(
            index="month_name",
            columns="product_type",
            values="prod_contribution_pct",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    pivot_income = (
        monthly_product
        .pivot_table(
            index="month_name",
            columns="product_type",
            values="prod_income_rm",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )

    pivot_avg = (
        monthly_product
        .pivot_table(
            index="month_name",
            columns="product_type",
            values="prod_avg_rm",
            aggfunc="mean",
            fill_value=0
        )
        .reset_index()
    )

    # ======================
    # Insight
    # ======================
    total_income = df_analysis["income_amt_rm"].sum()
    total_txn = len(df_analysis)
    avg_txn = df_analysis["income_amt_rm"].mean()
    median_txn = df_analysis["income_amt_rm"].median()
    n_months = monthly_income.shape[0]

    start_date = df_analysis["txn_date"].min().strftime("%d-%m-%Y")
    end_date = df_analysis["txn_date"].max().strftime("%d-%m-%Y")

    peak_month_row = monthly_income.loc[monthly_income["total_income_rm"].idxmax()]
    peak_month = peak_month_row["month_name"]
    peak_month_income = peak_month_row["total_income_rm"]

    growth_df = monthly_income.dropna(subset=["mom_growth_rm"])
    best_growth_row = growth_df.loc[growth_df["mom_growth_rm"].idxmax()] if len(growth_df) else None
    worst_growth_row = growth_df.loc[growth_df["mom_growth_rm"].idxmin()] if len(growth_df) else None

    top_prod = product_perf.iloc[0] if len(product_perf) else None
    second_prod = product_perf.iloc[1] if product_perf.shape[0] > 1 else None

    if product_perf.shape[0] > 2:
        long_tail_share = 100 - product_perf.iloc[:2]["contribution_pct"].sum()
    else:
        long_tail_share = 0.0

    insight = {
        "total_income": total_income,
        "total_txn": total_txn,
        "avg_txn": avg_txn,
        "median_txn": median_txn,
        "n_months": n_months,
        "start_date": start_date,
        "end_date": end_date,
        "peak_month": peak_month,
        "peak_month_income": peak_month_income,
        "best_growth_row": best_growth_row,
        "worst_growth_row": worst_growth_row,
        "top_prod": top_prod,
        "second_prod": second_prod,
        "long_tail_share": long_tail_share
    }

    # ======================
    # Optional print macam code asal
    # ======================
    if show:
        print("===== EASYKAMERA RENTAL INSIGHT SUMMARY =====\n")

        if df_list is not None and "CONVERSION" in df_list.columns:
            converted_count = df_list[df_list["CONVERSION"] == "Y"].shape[0]
            total_customer = df_list.shape[0]
            conversion_rate = (converted_count / total_customer) * 100 if total_customer > 0 else 0

            print("📊 Customer Conversion Summary")
            print(f"Total customer (Leads): {total_customer}")
            print(f"Converted customer : {converted_count}")
            print(f"Conversion rate: {conversion_rate:.2f}%\n")

        print("1) Overall Performance")
        print(f"- Total income       : RM{total_income:,.2f} ({n_months} active months)")
        print(f"- Total transactions : {total_txn} rental(s)")
        print(f"- Avg per rental     : RM{avg_txn:,.2f}")
        print(f"- Median per rental  : RM{median_txn:,.2f}")
        print(f"- Data period        : {start_date} hingga {end_date}\n")

        print("2) Monthly Trend")
        print(f"- Peak month         : {peak_month} dengan income RM{peak_month_income:,.2f}")

        if best_growth_row is not None:
            print(f"- Best MoM growth    : {best_growth_row['month_name']} "
                  f"(+RM{best_growth_row['mom_growth_rm']:,.2f}, {best_growth_row['mom_growth_pct']:.1f}%)")

        if worst_growth_row is not None:
            print(f"- Worst MoM growth   : {worst_growth_row['month_name']} "
                  f"(RM{worst_growth_row['mom_growth_rm']:,.2f}, {worst_growth_row['mom_growth_pct']:.1f}%)\n")

        print("3) Product Performance (Overall)")

        if top_prod is not None:
            print(f"- Top product        : {top_prod['product_type']} "
                  f"(RM{top_prod['total_income_rm']:,.2f} | {top_prod['txn_count']} txn | {top_prod['contribution_pct']:.1f}% of total)")

        if second_prod is not None:
            print(f"- Second product     : {second_prod['product_type']} "
                  f"(RM{second_prod['total_income_rm']:,.2f} | {second_prod['txn_count']} txn | {second_prod['contribution_pct']:.1f}% of total)")

        print(f"- Long-tail products : ~{long_tail_share:.1f}% of total income\n")

    return {
        "df_analysis": df_analysis,
        "monthly_income": monthly_income,
        "product_perf": product_perf,
        "monthly_product": monthly_product,
        "pivot_contrib_pct": pivot_contrib_pct,
        "pivot_income": pivot_income,
        "pivot_avg": pivot_avg,
        "insight": insight
    }