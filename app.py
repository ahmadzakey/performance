import pandas as pd

from finance_dashboard import render_finance_dashboard

# read data
# df = pd.read_parquet(
#     r"C:\Users\User\OneDrive\Business\My busines\performance\Input\performance_monitoring_finance.parquet"
# )

df = pd.read_parquet(
    "Input/performance_monitoring_finance.parquet"
)


# render dashboard
render_finance_dashboard(df)