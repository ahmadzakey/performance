import pandas as pd
from Utils.timestamp import standardize_datetime

def proces_df(old_path, new_path):

    old = pd.read_parquet(old_path)
    old = old[['txn_date','txn_type','day_type','income_amt_rm','income_cat','income_cat_detail','product_type','spend_amt_rm','spend_type']]
    old['txn_date'] = standardize_datetime(old['txn_date'])  # Utilis

    new = pd.read_csv(new_path)
    new = new[['txn_date','txn_type','day_type','income_amt_rm','income_cat','income_cat_detail','product_type','spend_amt_rm','spend_type']]
    new['txn_date'] = standardize_datetime(new['txn_date'])  # Utilis


    append = pd.concat([old, new], ignore_index=True)


    mask = (
        append['income_cat'].str.contains('Partner Investment', case=False, na=False) |
        append['income_cat_detail'].str.contains('Partner Investment', case=False, na=False)
    )
    append = append[~mask]


    append["product_type"] = append["product_type"].replace({
        "Canon G7X – Partner (INV001)": "Canon G7X"
    })


    append = append.sort_values(by='txn_date', ascending=True).reset_index(drop=True)

    output_path = r"C:\Users\User\OneDrive\Business\My busines\performance\Input\performance_monitoring_finance.parquet"

    append.to_parquet(output_path, index=False)


    return append
