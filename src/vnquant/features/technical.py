from __future__ import annotations
import numpy as np
import pandas as pd
from .normalization import rolling_zscore
from vnquant.config import parameter_value

def _wilder_rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def _rsi(close: pd.Series, n: int | None = None) -> pd.Series:
    n = int(n if n is not None else parameter_value("features.rsi_window"))
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
    rs_horizons = tuple(int(x) for x in parameter_value("features.rs_horizons"))
    d["ret_1"]=c.pct_change()
    for n in rs_horizons: d[f"ret_{n}"] = c.pct_change(n)
    ma_windows = tuple(int(x) for x in parameter_value("features.ma_windows"))
    for n in ma_windows:
        d[f"ma{n}"]=c.rolling(n,min_periods=n).mean()
        d[f"ema{n}"]=c.ewm(span=n,adjust=False,min_periods=n).mean()
    prev=c.shift(1)
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    rsi_window = int(parameter_value("features.rsi_window"))
    z_window = int(parameter_value("features.zscore_window"))
    z_min = int(parameter_value("features.zscore_min_periods"))
    d["atr14"]=_wilder_rma(tr,rsi_window); d["atr_pct"]=d.atr14/c
    d["rsi14"]=_rsi(c,rsi_window)
    d["volume_z60"]=rolling_zscore(v,z_window,z_min)
    value=d["value"].astype(float) if "value" in d else c*v
    d["turnover_z60"]=rolling_zscore(value,z_window,z_min)
    d["displacement_atr"]=c.diff().abs()/d.atr14.replace(0,np.nan)
    d["trend_confirmed"]=(d.ma20>d.ma50)&(d.ma50>d.ma200)&(c>d.ma200)

    dist_ma20=c/d.ma20-1
    volume_short = int(parameter_value("features.pullback_volume_short_window"))
    volume_long = min(ma_windows)
    volume_multiplier = float(parameter_value("features.pullback_volume_multiplier"))
    trend_buffer = float(parameter_value("features.pullback_trend_buffer"))
    pullback_low, pullback_high = map(float, parameter_value("features.pullback_ma_distance_bounds"))
    volume_contract=v.rolling(volume_short,min_periods=volume_short).mean() < v.rolling(volume_long,min_periods=volume_long).mean()*volume_multiplier
    candle_reclaim=(c>d.open)&(c>prev)
    d["signal_pullback"]=d.trend_confirmed&(c>d.ma200*(1+trend_buffer))&dist_ma20.between(pullback_low,pullback_high)&volume_contract&candle_reclaim

    # Conservative EOD reversal proxy: oversold + reclaim of prior close while
    # still above the 200-day trend filter. [D] Hypothesis; must be calibrated.
    d["signal_reversal"]=(d.rsi14<float(parameter_value("features.reversal_rsi_max")))&(c>prev)&(c>d.ma200)&((c-l)/(h-l).replace(0,np.nan)>float(parameter_value("features.reversal_close_location_min")))

    weights = parameter_value("features.setup_score_weights")
    d["setup_quality"]=(
        float(weights["trend"])*d.trend_confirmed.astype(float)
        +float(weights["ma_distance"])*(1-(dist_ma20.abs()/float(parameter_value("features.setup_ma_distance_scale"))).clip(0,1))
        +float(weights["reclaim"])*candle_reclaim.astype(float)
        +float(weights["volatility"])*(1-(d.atr_pct/float(parameter_value("features.setup_atr_scale"))).clip(0,1))
    ).clip(0,1)
    # Direction-aware volume confirmation is finalized by strategy family.
    d["volume_confirmation"]=(float(parameter_value("features.volume_score_neutral"))+float(parameter_value("features.volume_score_slope"))*d.volume_z60.fillna(0)).clip(0,1)
    return d
