from __future__ import annotations
import math
import pandas as pd

def trade_metrics(trades: pd.DataFrame) -> dict:
    if trades.empty or "net_return" not in trades:
        return {"trades":0,"hit_rate":None,"mean_net_return":None,"profit_factor":None,"max_trade_loss":None}
    r=trades.net_return.dropna().astype(float)
    if r.empty:
        return {"trades":len(trades),"hit_rate":None,"mean_net_return":None,"profit_factor":None,"max_trade_loss":None}
    wins=r[r>0].sum(); losses=-r[r<0].sum()
    return {
        "trades":int(len(r)),
        "hit_rate":float((r>0).mean()),
        "mean_net_return":float(r.mean()),
        "median_net_return":float(r.median()),
        "profit_factor":float(wins/losses) if losses>0 else None,
        "max_trade_loss":float(r.min()),
    }
