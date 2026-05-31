import pandas as pd
import numpy as np

def standardize_datetime(series, output_format=None):
    """
    Standardize mixed datetime formats safely.

    Parameters
    ----------
    series : pd.Series
        Column datetime campur format
    output_format : str, optional
        Example:
        '%Y-%m-%d'
        '%Y-%m-%d %H:%M:%S'

    Returns
    -------
    pd.Series
    """

    # Convert semua jadi string
    s = series.astype(str).str.strip()

    # First attempt (auto detect)
    dt = pd.to_datetime(
        s,
        errors='coerce',
        infer_datetime_format=True
    )

    # Fallback attempt untuk yg gagal
    failed_mask = dt.isna()

    if failed_mask.any():
        dt2 = pd.to_datetime(
            s[failed_mask],
            errors='coerce',
            dayfirst=False
        )

        dt.loc[failed_mask] = dt2

    # Optional output format
    if output_format:
        return dt.dt.strftime(output_format)

    return dt