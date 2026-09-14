from __future__ import annotations
import pandas as pd
from vnquant.features.normalization import cross_sectional_percentile
from vnquant.config import parameter_value

def compute_sector_scores(panel: pd.DataFrame, as_of=None) -> pd.DataFrame:
    d = panel.copy()
    if as_of is not None:
        d = d[d.trading_date <= as_of]
    if d.empty:
        return pd.DataFrame()
    latest = d.trading_date.max()
    cur = d[d.trading_date == latest].copy()
    cols = [c for c in ("rs_sector_market_20", "rs_sector_market_126") if c in cur]
    rows=[]
    for sector,g in cur.groupby("sector"):
        row={"trading_date":latest,"sector":sector,"members":int(g.symbol.nunique())}
        row["rs20"] = float(g["rs_sector_market_20"].median()) if "rs_sector_market_20" in g else 0.0
        row["rs126"] = float(g["rs_sector_market_126"].median()) if "rs_sector_market_126" in g else 0.0
        row["breadth"] = float((g.close > g.ma50).mean()) if "ma50" in g else 0.0
        row["volume_impulse"] = float(g.volume_z60.median()) if "volume_z60" in g else 0.0
        rows.append(row)
    out=pd.DataFrame(rows)
    if out.empty: return out
    for c in ("rs20","rs126","breadth","volume_impulse"):
        out[c+"_rank"] = cross_sectional_percentile(out[c]) / 100.0
    weights = parameter_value("sector.weights")
    out["leadership_score"] = 100*(float(weights["rs20"])*out.rs20_rank + float(weights["rs126"])*out.rs126_rank + float(weights["breadth"])*out.breadth_rank + float(weights["volume_impulse"])*out.volume_impulse_rank)
    return out.sort_values("leadership_score", ascending=False).reset_index(drop=True)
