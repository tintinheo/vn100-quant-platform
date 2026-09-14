from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from vnquant.market.regime import Regime
from vnquant.data.quality import apply_dq_policy
from vnquant.config import parameter_value

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
    confidence: float
    actionable: bool

def detect_candidates(latest: pd.DataFrame, regime: Regime, sector_scores: pd.DataFrame,
                      *, dq_score: int | None = None, dq_actionable: bool = True) -> pd.DataFrame:
    score_max = float(parameter_value("scores.maximum"))
    dq_score = int(score_max if dq_score is None else dq_score)
    rs_long_min = float(parameter_value("recommendations.rs_long_min"))
    rs_short_pullback_max = float(parameter_value("recommendations.rs_short_pullback_max"))
    rs_short_momentum_min = float(parameter_value("recommendations.rs_short_momentum_min"))
    rs_short_reversal_max = float(parameter_value("recommendations.rs_short_reversal_max"))
    sector_min = float(parameter_value("recommendations.sector_min"))
    momentum_volume_min = float(parameter_value("recommendations.momentum_volume_z_min"))
    neutral = float(parameter_value("recommendations.neutral_component_score"))
    if regime == Regime.PANIC_BEAR or latest.empty:
        return pd.DataFrame(columns=[f.name for f in Candidate.__dataclass_fields__.values()])
    ss = sector_scores.set_index("sector").leadership_score.to_dict() if not sector_scores.empty else {}
    rows=[]
    for _,r in latest.iterrows():
        long_rank=float(r.get("rs_stock_market_rank_126", float("nan")))
        short_rank=float(r.get("rs_stock_market_rank_20", float("nan")))
        sector_score=float(ss.get(r.get("sector"), parameter_value("recommendations.neutral_sector_score")))
        if pd.isna(long_rank) or pd.isna(short_rank):
            continue
        family=None; reason=[]
        if bool(r.get("signal_pullback", False)) and long_rank >= rs_long_min and short_rank <= rs_short_pullback_max:
            family=StrategyFamily.TREND_PULLBACK; reason.append("long-term leader in short-term pullback")
        elif regime == Regime.STRONG_BULL and long_rank >= rs_long_min and short_rank >= rs_short_momentum_min \
             and bool(r.get("trend_confirmed", False)) and float(r.get("volume_z60", 0) or 0) >= momentum_volume_min:
            family=StrategyFamily.MOMENTUM_CONTINUATION; reason.append("long+short RS strong in Strong Bull")
        elif bool(r.get("signal_reversal", False)) and short_rank <= rs_short_reversal_max and regime >= Regime.RANGE:
            family=StrategyFamily.STRUCTURAL_REVERSAL; reason.append("oversold reversal with market gate")
        if family is None or sector_score < sector_min:
            continue
        setup=float(r.get("setup_quality", neutral) or neutral)
        vol=float(r.get("volume_confirmation", neutral) or neutral)
        weights = parameter_value("recommendations.score_weights")
        short_evidence = score_max-short_rank if family != StrategyFamily.MOMENTUM_CONTINUATION else short_rank
        score=(float(weights["long_rs"])*long_rank + float(weights["short_rs"])*short_evidence
               + float(weights["sector"])*sector_score + score_max*float(weights["setup"])*setup
               + score_max*float(weights["volume"])*vol)
        score = min(score_max, float(score))
        confidence, threshold_actionable = apply_dq_policy(score, dq_score)
        actionable = bool(dq_actionable and threshold_actionable)
        rows.append(asdict(Candidate(str(r.symbol), r.trading_date, family.value, score,
            long_rank, short_rank, sector_score, "; ".join(reason), confidence, actionable)))
    return pd.DataFrame(rows).sort_values("score",ascending=False).reset_index(drop=True) if rows else pd.DataFrame(columns=Candidate.__dataclass_fields__)
