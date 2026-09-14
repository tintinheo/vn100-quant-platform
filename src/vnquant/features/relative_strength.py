from __future__ import annotations
import pandas as pd
from .normalization import cross_sectional_percentile
from vnquant.config import parameter_value

def add_cross_sectional_rs(panel: pd.DataFrame, horizons=None) -> pd.DataFrame:
    """Add stock-vs-market, stock-vs-sector and sector-vs-market excess returns.

    Input must contain symbol,trading_date,close and sector. Benchmark returns are
    equal-weighted cross-sectional returns, deliberately avoiding cap-index
    concentration when ranking stocks.
    """
    horizons = tuple(horizons if horizons is not None else parameter_value("features.rs_horizons"))
    d = panel.sort_values(["symbol", "trading_date"]).copy()
    for h in horizons:
        ret_col = f"return_{h}"
        d[ret_col] = d.groupby("symbol", sort=False).close.pct_change(h)
        market = d.groupby("trading_date")[ret_col].mean().rename(f"market_return_{h}")
        sector = d.groupby(["trading_date", "sector"])[ret_col].mean().rename(f"sector_return_{h}")
        d = d.join(market, on="trading_date").join(sector, on=["trading_date", "sector"])
        d[f"rs_stock_market_{h}"] = d[ret_col] - d[f"market_return_{h}"]
        d[f"rs_stock_sector_{h}"] = d[ret_col] - d[f"sector_return_{h}"]
        d[f"rs_sector_market_{h}"] = d[f"sector_return_{h}"] - d[f"market_return_{h}"]
        d[f"rs_stock_market_rank_{h}"] = d.groupby("trading_date")[f"rs_stock_market_{h}"].transform(cross_sectional_percentile)
        d[f"rs_stock_sector_rank_{h}"] = d.groupby(["trading_date", "sector"])[f"rs_stock_sector_{h}"].transform(cross_sectional_percentile)
        d[f"rs_sector_market_rank_{h}"] = d.groupby("trading_date")[f"rs_sector_market_{h}"].transform(cross_sectional_percentile)
    return d
