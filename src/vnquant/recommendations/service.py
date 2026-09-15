"""Fail-closed, execution-aware recommendation construction.

The service creates an *instruction for a future attempt*, never a fill.  A fill
belongs to execution/audit data and can only be established from the attempt
session (or finer) observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Mapping, Sequence

import pandas as pd

from vnquant.backtest.execution import ExecutionMode, simulate_buy_limit
from vnquant.market.rules import hose_floor, round_down_hose
from vnquant.market.settlement import (eod_policy_earliest_exit_fill_date,
                                       regulatory_sellable_date)
from vnquant.portfolio import PortfolioContext, PortfolioRiskService


NO_ACTIONABLE_RECOMMENDATION = "NO_ACTIONABLE_RECOMMENDATION"


@dataclass(frozen=True)
class RecommendationRequest:
    symbol: str
    setup: str
    signal_date: date
    sessions: Sequence[date]
    signal_close: float
    entry_zone: tuple[float, float]
    entry_trigger: str
    technical_stop: float
    risk_stop: float
    invalidation: str
    targets: tuple[float, ...]
    win_probability: float
    confidence: float
    forecast_status: str
    dq_status: str
    dq_actionable: bool
    strategy_validated: bool
    source_lineage: Mapping[str, object]
    sector: str
    correlated_group: str
    adv_shares: float
    maximum_gap: float
    regime: str
    # Optional attempt-session bar is evidence for feasibility, not permission
    # to record a fill in this recommendation contract.
    attempt_bar: Mapping[str, float] | None = None


@dataclass(frozen=True)
class RecommendationResult:
    status: str
    reason: str
    recommendation: Mapping[str, object] | None


def _finite_positive(value: object) -> bool:
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def _next_session(signal_date: date, sessions: Sequence[date]) -> date | None:
    later = sorted(day for day in set(sessions) if day > signal_date)
    return later[0] if later else None


def build_recommendation(request: RecommendationRequest,
                         portfolio: PortfolioContext) -> RecommendationResult:
    """Build a recommendation only when data, strategy, risk and execution pass.

    Prices are VND.  The entry price used for planning is the tick-valid upper
    limit of the entry zone; it is explicitly labelled ``planned_entry_limit``
    and is never represented as an actual or assumed fill.
    """
    required_text = (request.symbol, request.setup, request.entry_trigger,
                     request.invalidation, request.forecast_status,
                     request.dq_status, request.sector, request.correlated_group)
    if any(not str(value).strip() for value in required_text):
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "REQUIRED_DATA_MISSING", None)
    if not request.source_lineage or not all(
            request.source_lineage.get(key) for key in
            ("provider", "snapshot_id", "canonical_revision", "ingested_at")):
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "SOURCE_LINEAGE_INCOMPLETE", None)
    if not request.dq_actionable or request.dq_status != "PASS":
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "DQ_GATE_FAILED", None)
    if not request.strategy_validated:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "STRATEGY_GATE_FAILED", None)
    if (request.forecast_status != "AVAILABLE" or not 0 <= request.win_probability <= 1
            or not 0 <= request.confidence <= 100):
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "FORECAST_GATE_FAILED", None)

    attempt_date = _next_session(request.signal_date, request.sessions)
    if attempt_date is None:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "ATTEMPT_DATE_UNAVAILABLE", None)
    low, high = request.entry_zone
    numeric = (request.signal_close, low, high, request.technical_stop,
               request.risk_stop, request.adv_shares)
    if not all(_finite_positive(value) for value in numeric) or low > high:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "PRICE_OR_LIQUIDITY_INVALID", None)
    planned_low = round_down_hose(low)
    planned_entry = round_down_hose(high)
    if planned_low > planned_entry:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "ENTRY_PLAN_INVALID", None)
    band_floor = hose_floor(request.signal_close)
    band_ceiling = round_down_hose(request.signal_close * 1.07)
    if not band_floor <= planned_low <= planned_entry <= band_ceiling:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "PRICE_BAND_GATE_FAILED", None)
    if request.technical_stop >= planned_entry or request.risk_stop >= planned_entry:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "STOP_GATE_FAILED", None)
    if not request.targets or not all(_finite_positive(target) and target > planned_entry
                                      for target in request.targets):
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "TARGET_GATE_FAILED", None)

    execution_status = "ELIGIBLE_FOR_FUTURE_ATTEMPT"
    if not math.isfinite(request.maximum_gap) or request.maximum_gap < 0:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "GAP_GATE_INVALID", None)
    if request.attempt_bar is not None:
        bar = request.attempt_bar
        if bar.get("trading_date") != attempt_date:
            return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "ATTEMPT_BAR_DATE_MISMATCH", None)
        try:
            open_px, high_px, low_px = (float(bar[key]) for key in ("open", "high", "low"))
            if (not all(_finite_positive(value) for value in (open_px, high_px, low_px))
                    or not low_px <= open_px <= high_px):
                raise ValueError("invalid attempt OHLC")
            fill = simulate_buy_limit(
                request.signal_close, open_px, high_px, low_px,
                premium=planned_entry / request.signal_close - 1,
                max_gap=request.maximum_gap, mode=ExecutionMode.CONSERVATIVE)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "ATTEMPT_BAR_INVALID", None)
        if not fill.filled:
            return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION,
                                        f"EXECUTION_GATE_FAILED:{fill.reason}", None)
        execution_status = "ATTEMPT_FEASIBLE_NOT_A_FILL"

    risk_input = pd.DataFrame([{
        "symbol": request.symbol, "sector": request.sector,
        "correlated_group": request.correlated_group,
        "entry_price": planned_entry, "risk_stop": request.risk_stop,
        "adv_shares": request.adv_shares,
    }])
    decision = PortfolioRiskService().evaluate(risk_input, portfolio, request.regime).iloc[0]
    if decision.status == "REJECTED":
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION,
                                    f"PORTFOLIO_GATE_FAILED:{decision.binding_constraint}", None)

    buy_cost = planned_entry * portfolio.costs.buy_rate
    quantity = int(decision.quantity)
    loss = float(decision.estimated_loss)
    rewards = tuple(quantity * (float(target) - planned_entry - buy_cost
                    - float(target) * portfolio.costs.sell_rate) - portfolio.costs.fixed_cost
                    for target in request.targets)
    if loss <= 0 or min(rewards) <= 0:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "COST_ADJUSTED_PAYOFF_INVALID", None)
    reward_to_risk = rewards[0] / loss
    expected_value = request.win_probability * rewards[0] - (1 - request.win_probability) * loss
    if expected_value <= 0:
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION, "EXPECTED_VALUE_GATE_FAILED", None)

    try:
        sellable = regulatory_sellable_date(attempt_date, list(request.sessions))
        earliest_exit = eod_policy_earliest_exit_fill_date(attempt_date, list(request.sessions))
    except (ValueError, IndexError):
        return RecommendationResult(NO_ACTIONABLE_RECOMMENDATION,
                                    "SETTLEMENT_CALENDAR_INCOMPLETE", None)
    payload = {
        "symbol": request.symbol, "setup": request.setup,
        "signal_date": request.signal_date.isoformat(), "attempt_date": attempt_date.isoformat(),
        "entry_zone": [planned_low, planned_entry], "planned_entry_limit": planned_entry,
        "entry_trigger": request.entry_trigger, "technical_stop": request.technical_stop,
        "risk_stop": request.risk_stop, "invalidation": request.invalidation,
        "targets": list(map(float, request.targets)),
        "expected_reward_to_risk": reward_to_risk, "expected_value": expected_value,
        "position_size": {"nav_fraction": decision.notional / portfolio.account_equity},
        "execution_feasibility": execution_status, "confidence": request.confidence,
        "forecast_status": request.forecast_status, "dq_status": request.dq_status,
        "source_lineage": dict(request.source_lineage),
        "regulatory_sellable_date": sellable.isoformat(),
        "policy_earliest_exit_fill_date": earliest_exit.isoformat(),
        "risk_decision_id": decision.decision_id,
        "fill_price": None,
    }
    return RecommendationResult("ACTIONABLE", "ALL_GATES_PASSED", payload)
