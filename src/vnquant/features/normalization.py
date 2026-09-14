from __future__ import annotations
import numpy as np
import pandas as pd
from vnquant.config import parameter_value

def rolling_zscore(s: pd.Series, window: int | None = None, min_periods: int | None = None) -> pd.Series:
    window = int(window if window is not None else parameter_value("features.zscore_window"))
    min_periods = int(min_periods if min_periods is not None else parameter_value("features.zscore_min_periods"))
    mu = s.rolling(window, min_periods=min_periods).mean()
    sd = s.rolling(window, min_periods=min_periods).std(ddof=0).replace(0, np.nan)
    return (s - mu) / sd

def cross_sectional_percentile(s: pd.Series) -> pd.Series:
    """0..100 rank; NaNs remain NaN."""
    return s.rank(method="average", pct=True) * 100.0

def winsorize_cross_section(s: pd.Series, lower: float | None = None, upper: float | None = None) -> pd.Series:
    lower = float(lower if lower is not None else parameter_value("features.winsor_lower"))
    upper = float(upper if upper is not None else parameter_value("features.winsor_upper"))
    valid = s.dropna()
    if valid.empty:
        return s.copy()
    lo, hi = valid.quantile([lower, upper])
    return s.clip(lo, hi)
