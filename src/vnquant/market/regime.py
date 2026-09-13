from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
import pandas as pd

class Regime(IntEnum):
    PANIC_BEAR = 0
    RISK_OFF = 1
    RANGE = 2
    CONCENTRATED_BULL = 3
    STRONG_BULL = 4

@dataclass(frozen=True)
class RegimeResult:
    regime: Regime
    cap_score: int
    ew_score: int
    breadth_pct_ma50: float
    turnover_ratio: float | None
    reason: str


def _index_score(row) -> int:
    vals = (row.get("close"), row.get("ma50"), row.get("ma200"))
    if any(pd.isna(x) for x in vals):
        return 0
    c, m50, m200 = map(float, vals)
    return int(c > m50) + int(c > m200) + int(m50 > m200)


def compute_regime(cap_row, ew_row, breadth_row) -> RegimeResult:
    cap = _index_score(cap_row); ew = _index_score(ew_row); s = min(cap, ew)
    b50 = float(breadth_row.get("pct_ma50", 0.0) or 0.0)
    ad_up = float(breadth_row.get("ad_slope_10", 0.0) or 0.0) > 0
    tr_raw = breadth_row.get("turnover_ratio")
    tr = None if tr_raw is None or pd.isna(tr_raw) else float(tr_raw)

    # Missing turnover must NEVER confirm Strong/Concentrated Bull.
    if tr is not None and s == 3 and b50 >= 0.60 and ad_up and tr >= 1.00:
        return RegimeResult(Regime.STRONG_BULL, cap, ew, b50, tr, "dual-index trend + breadth + turnover confirmed")
    if tr is not None and s >= 2 and b50 >= 0.45 and tr >= 0.85:
        return RegimeResult(Regime.CONCENTRATED_BULL, cap, ew, b50, tr, "positive trend with partial breadth/turnover")
    if s >= 1 and b50 >= 0.35:
        reason = "range/neutral; turnover missing caps bull classification" if tr is None else "mixed trend/breadth"
        return RegimeResult(Regime.RANGE, cap, ew, b50, tr, reason)
    if s >= 1 or b50 >= 0.25:
        return RegimeResult(Regime.RISK_OFF, cap, ew, b50, tr, "weak trend or breadth")
    return RegimeResult(Regime.PANIC_BEAR, cap, ew, b50, tr, "trend and breadth both weak")
