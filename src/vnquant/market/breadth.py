from __future__ import annotations
import pandas as pd

def build_equal_weight_index(panel: pd.DataFrame, base: float = 1000.0) -> pd.DataFrame:
    d = panel.sort_values(["symbol", "trading_date"]).copy()
    d["ret1"] = d.groupby("symbol").close.pct_change()
    ret = d.groupby("trading_date").ret1.mean().fillna(0.0)
    close = base * (1.0 + ret).cumprod()
    out = pd.DataFrame({"trading_date": close.index, "close": close.values})
    out["ma50"] = out.close.rolling(50, min_periods=50).mean()
    out["ma200"] = out.close.rolling(200, min_periods=200).mean()
    return out

def compute_breadth(panel: pd.DataFrame) -> pd.DataFrame:
    d = panel.sort_values(["symbol", "trading_date"]).copy()
    for n in (20, 50, 200):
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
    agg["ad_slope_10"] = agg.ad_line.diff(10)
    agg["turnover_ma20"] = agg.turnover.rolling(20, min_periods=10).mean()
    agg["turnover_ratio"] = agg.turnover / agg.turnover_ma20.replace(0, pd.NA)
    return agg
