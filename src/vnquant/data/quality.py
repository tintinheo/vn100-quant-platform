from __future__ import annotations
import pandas as pd
from .models import DataIssue

REQUIRED={"symbol","trading_date","open","high","low","close","volume","provider"}

def validate_bars(df: pd.DataFrame) -> list[DataIssue]:
    issues=[]
    missing=REQUIRED-set(df.columns)
    if missing:
        return [DataIssue("ERROR","SCHEMA_MISSING",f"Missing columns: {sorted(missing)}")]
    if df.empty:
        return [DataIssue("ERROR","EMPTY","No bars returned")]
    if df.duplicated(["symbol","trading_date"]).any():
        issues.append(DataIssue("ERROR","DUPLICATE","Duplicate symbol/date rows"))
    bad_ohlc=(df["high"] < df[["open","close"]].max(axis=1)) | (df["low"] > df[["open","close"]].min(axis=1)) | (df["low"]>df["high"])
    if bad_ohlc.any(): issues.append(DataIssue("ERROR","OHLC_LOGIC",f"{int(bad_ohlc.sum())} rows violate OHLC invariants"))
    if (df["volume"]<0).any(): issues.append(DataIssue("ERROR","NEGATIVE_VOLUME","Negative volume found"))
    for c in ["open","high","low","close"]:
        if (df[c] <= 0).any(): issues.append(DataIssue("ERROR","NONPOSITIVE_PRICE",f"Non-positive {c}"))
    if not df["trading_date"].is_monotonic_increasing:
        issues.append(DataIssue("WARN","UNSORTED","Bars are not sorted by trading_date"))
    return issues

def quality_score(issues:list[DataIssue])->int:
    score=100
    penalties={"ERROR":35,"WARN":10,"INFO":0}
    for i in issues: score-=penalties[i.severity]
    return max(0,score)
