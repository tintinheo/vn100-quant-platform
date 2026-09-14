from __future__ import annotations
import pandas as pd
from vnquant.config import parameter_value

def build_equal_weight_index(panel: pd.DataFrame, base: float | None = None) -> pd.DataFrame:
    base = float(base if base is not None else parameter_value("market.equal_weight_base"))
    d = panel.sort_values(["symbol", "trading_date"]).copy()
    d["ret1"] = d.groupby("symbol").close.pct_change()
    ret = d.groupby("trading_date").ret1.mean().fillna(0.0)
    close = base * (1.0 + ret).cumprod()
    out = pd.DataFrame({"trading_date": close.index, "close": close.values})
    for window in parameter_value("features.ma_windows"):
        out[f"ma{int(window)}"] = out.close.rolling(int(window), min_periods=int(window)).mean()
    return out

def compute_breadth(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel.sort_values(["symbol", "trading_date"]).copy()
    for n in parameter_value("market.breadth_windows"):
        if f"ma{n}" not in d:
            d[f"ma{n}"] = d.groupby("symbol").close.transform(lambda x: x.rolling(n, min_periods=n).mean())
    d["adv"] = d.groupby("symbol").close.diff() > 0
    d["dec"] = d.groupby("symbol").close.diff() < 0
    agg = d.groupby("trading_date").agg(
        pct_ma20=("close", lambda s: float((s > d.loc[s.index, "ma20"]).mean())),
        pct_ma50=("close", lambda s: float((s > d.loc[s.index, "ma50"]).mean())),
        pct_ma200=("close", lambda s: float((s > d.loc[s.index, "ma200"]).mean())),
        advances=("adv", "sum"), decreases=("dec", "sum"),
        turnover=("value", "sum") if "value" in d.columns else ("volume", "sum"),
    ).reset_index()
    agg["ad_net"] = agg.advances - agg.decreases
    agg["ad_line"] = agg.ad_net.cumsum()
    ad_window = int(parameter_value("market.ad_slope_window"))
    turnover_window = int(parameter_value("market.turnover_window"))
    turnover_min = int(parameter_value("market.turnover_min_periods"))
    agg["ad_slope_10"] = agg.ad_line.diff(ad_window)
    agg["turnover_ma20"] = agg.turnover.rolling(turnover_window, min_periods=turnover_min).mean()
    agg["turnover_ratio"] = agg.turnover / agg.turnover_ma20.replace(0, pd.NA)
    return agg
