from __future__ import annotations
import numpy as np
import pandas as pd
from .normalization import rolling_zscore

def _wilder_rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta=close.diff(); up=delta.clip(lower=0); down=(-delta).clip(lower=0)
    avg_up=_wilder_rma(up,n); avg_down=_wilder_rma(down,n)
    rs=avg_up/avg_down.replace(0,np.nan)
    out=100-100/(1+rs)
    return out.where(avg_down.ne(0),100.0)

def add_baseline_features(df:pd.DataFrame)->pd.DataFrame:
    """Explainable technical baseline using only past/current bars.

    No feature in this function uses future bars. SMC/Wyckoff confirmed-pivot
    features belong in a separate future module with explicit recognition delay.
    """
    d=df.copy().sort_values("trading_date").reset_index(drop=True)
    c=d.close.astype(float); h=d.high.astype(float); l=d.low.astype(float); v=d.volume.astype(float)
    d["ret_1"]=c.pct_change(); d["ret_20"]=c.pct_change(20); d["ret_126"]=c.pct_change(126)
    for n in (20,50,200):
        d[f"ma{n}"]=c.rolling(n,min_periods=n).mean()
        d[f"ema{n}"]=c.ewm(span=n,adjust=False,min_periods=n).mean()
    prev=c.shift(1)
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    d["atr14"]=_wilder_rma(tr,14); d["atr_pct"]=d.atr14/c
    d["rsi14"]=_rsi(c,14)
    d["volume_z60"]=rolling_zscore(v,60,20)
    value=d["value"].astype(float) if "value" in d else c*v
    d["turnover_z60"]=rolling_zscore(value,60,20)
    d["displacement_atr"]=c.diff().abs()/d.atr14.replace(0,np.nan)
    d["trend_confirmed"]=(d.ma20>d.ma50)&(d.ma50>d.ma200)&(c>d.ma200)

    dist_ma20=c/d.ma20-1
    volume_contract=v.rolling(5,min_periods=5).mean() < v.rolling(20,min_periods=20).mean()*1.10
    candle_reclaim=(c>d.open)&(c>prev)
    d["signal_pullback"]=d.trend_confirmed&(c>d.ma200*1.02)&dist_ma20.between(-0.04,0.02)&volume_contract&candle_reclaim

    # Conservative EOD reversal proxy: oversold + reclaim of prior close while
    # still above the 200-day trend filter. [D] Hypothesis; must be calibrated.
    d["signal_reversal"]=(d.rsi14<32)&(c>prev)&(c>d.ma200)&((c-l)/(h-l).replace(0,np.nan)>0.60)

    d["setup_quality"]=(
        0.35*d.trend_confirmed.astype(float)
        +0.25*(1-(dist_ma20.abs()/0.06).clip(0,1))
        +0.20*candle_reclaim.astype(float)
        +0.20*(1-(d.atr_pct/0.08).clip(0,1))
    ).clip(0,1)
    # Direction-aware volume confirmation is finalized by strategy family.
    d["volume_confirmation"]=(0.5+0.2*d.volume_z60.fillna(0)).clip(0,1)
    return d
