from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from vnquant.market.regime import Regime

class StrategyFamily(str, Enum):
    TREND_PULLBACK = "TREND_PULLBACK"
    MOMENTUM_CONTINUATION = "MOMENTUM_CONTINUATION"
    STRUCTURAL_REVERSAL = "STRUCTURAL_REVERSAL"

@dataclass(frozen=True)
class Candidate:
    symbol: str
    trading_date: object
    family: str
    score: float
    rs_long_rank: float
    rs_short_rank: float
    sector_score: float
    reason: str

# [D] thresholds. They are deliberately centralized and must be calibrated on real data.
RS_LONG_MIN = 60.0
RS_SHORT_PULLBACK_MAX = 40.0
RS_SHORT_MOMENTUM_MIN = 65.0
SECTOR_MIN = 45.0


def detect_candidates(latest: pd.DataFrame, regime: Regime, sector_scores: pd.DataFrame) -> pd.DataFrame:
    if regime == Regime.PANIC_BEAR or latest.empty:
        return pd.DataFrame(columns=[f.name for f in Candidate.__dataclass_fields__.values()])
    ss = sector_scores.set_index("sector").leadership_score.to_dict() if not sector_scores.empty else {}
    rows=[]
    for _,r in latest.iterrows():
        long_rank=float(r.get("rs_stock_market_rank_126", float("nan")))
        short_rank=float(r.get("rs_stock_market_rank_20", float("nan")))
        sector_score=float(ss.get(r.get("sector"), 50.0))
        if pd.isna(long_rank) or pd.isna(short_rank):
            continue
        family=None; reason=[]
        if bool(r.get("signal_pullback", False)) and long_rank >= RS_LONG_MIN and short_rank <= RS_SHORT_PULLBACK_MAX:
            family=StrategyFamily.TREND_PULLBACK; reason.append("long-term leader in short-term pullback")
        elif regime == Regime.STRONG_BULL and long_rank >= RS_LONG_MIN and short_rank >= RS_SHORT_MOMENTUM_MIN \
             and bool(r.get("trend_confirmed", False)) and float(r.get("volume_z60", 0) or 0) >= 0.5:
            family=StrategyFamily.MOMENTUM_CONTINUATION; reason.append("long+short RS strong in Strong Bull")
        elif bool(r.get("signal_reversal", False)) and short_rank <= 25 and regime >= Regime.RANGE:
            family=StrategyFamily.STRUCTURAL_REVERSAL; reason.append("oversold reversal with market gate")
        if family is None or sector_score < SECTOR_MIN:
            continue
        setup=float(r.get("setup_quality", 0.5) or 0.5)
        vol=float(r.get("volume_confirmation", 0.5) or 0.5)
        # [D] explainable baseline score; not a probability.
        score=0.35*long_rank + 0.15*(100-short_rank if family != StrategyFamily.MOMENTUM_CONTINUATION else short_rank) + 0.25*sector_score + 25*(0.6*setup+0.4*vol)
        rows.append(asdict(Candidate(str(r.symbol), r.trading_date, family.value, min(100.0,float(score)), long_rank, short_rank, sector_score, "; ".join(reason))))
    return pd.DataFrame(rows).sort_values("score",ascending=False).reset_index(drop=True) if rows else pd.DataFrame(columns=Candidate.__dataclass_fields__)
