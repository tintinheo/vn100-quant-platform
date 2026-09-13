from __future__ import annotations
import numpy as np
import pandas as pd

def rolling_zscore(s: pd.Series, window: int = 60, min_periods: int | None = None) -> pd.Series:
    min_periods = min_periods or max(10, window // 3)
    mu = s.rolling(window, min_periods=min_periods).mean()
    sd = s.rolling(window, min_periods=min_periods).std(ddof=0).replace(0, np.nan)
    return (s - mu) / sd

def cross_sectional_percentile(s: pd.Series) -> pd.Series:
    """0..100 rank; NaNs remain NaN."""
    return s.rank(method="average", pct=True) * 100.0

def winsorize_cross_section(s: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    valid = s.dropna()
    if valid.empty:
        return s.copy()
    lo, hi = valid.quantile([lower, upper])
    return s.clip(lo, hi)
