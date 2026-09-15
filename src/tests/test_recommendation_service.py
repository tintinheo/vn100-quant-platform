from datetime import date, timedelta

from vnquant.portfolio import CostModel, PortfolioContext
from vnquant.recommendations import (NO_ACTIONABLE_RECOMMENDATION,
                                     RecommendationRequest,
                                     build_recommendation)


def request(**overrides):
    sessions = tuple(date(2026, 1, 5) + timedelta(days=i) for i in range(8))
    values = dict(
        symbol="AAA", setup="TREND_PULLBACK", signal_date=sessions[0], sessions=sessions,
        signal_close=50_000, entry_zone=(50_100, 50_500),
        entry_trigger="buy limit only after next-session pullback",
        technical_stop=48_000, risk_stop=47_500,
        invalidation="daily close below technical support", targets=(56_000, 60_000),
        win_probability=.60, confidence=82, forecast_status="AVAILABLE", dq_status="PASS",
        dq_actionable=True, strategy_validated=True,
        source_lineage={"provider": "fixture", "snapshot_id": "snap-1",
                        "canonical_revision": "rev-1", "ingested_at": "2026-01-05T10:00:00Z"},
        sector="BANK", correlated_group="BANK", adv_shares=1_000_000,
        maximum_gap=.02, regime="STRONG_BULL")
    values.update(overrides)
    return RecommendationRequest(**values)


def portfolio():
    return PortfolioContext(1_000_000_000, 1_000_000_000, 10_000_000,
                            costs=CostModel(.001, .002, 10_000))


def test_complete_contract_is_future_attempt_not_signal_close_fill():
    result = build_recommendation(request(), portfolio())
    assert result.status == "ACTIONABLE"
    rec = result.recommendation
    expected = {"setup", "signal_date", "attempt_date", "entry_zone", "entry_trigger",
                "technical_stop", "risk_stop", "invalidation", "targets",
                "expected_reward_to_risk", "expected_value", "position_size",
                "execution_feasibility", "confidence", "forecast_status", "dq_status",
                "source_lineage"}
    assert expected <= rec.keys()
    assert rec["attempt_date"] != rec["signal_date"]
    assert rec["fill_price"] is None
    assert rec["planned_entry_limit"] == 50_500
    assert rec["position_size"]["nav_fraction"] > 0
    assert rec["confidence"] == 82


def test_attempt_evidence_applies_gap_and_conservative_touch_gate_without_fill_claim():
    attempt = {"trading_date": date(2026, 1, 6), "open": 52_000,
               "high": 53_000, "low": 50_500}
    result = build_recommendation(request(attempt_bar=attempt), portfolio())
    assert result.status == NO_ACTIONABLE_RECOMMENDATION
    assert result.reason == "EXECUTION_GATE_FAILED:gap_gate"


def test_every_data_strategy_forecast_and_dq_gate_fails_closed():
    cases = [
        (dict(source_lineage={}), "SOURCE_LINEAGE_INCOMPLETE"),
        (dict(dq_status="DEGRADED"), "DQ_GATE_FAILED"),
        (dict(strategy_validated=False), "STRATEGY_GATE_FAILED"),
        (dict(forecast_status="FORECAST_UNAVAILABLE"), "FORECAST_GATE_FAILED"),
        (dict(adv_shares=0), "PRICE_OR_LIQUIDITY_INVALID"),
    ]
    for override, reason in cases:
        result = build_recommendation(request(**override), portfolio())
        assert (result.status, result.reason, result.recommendation) == (
            NO_ACTIONABLE_RECOMMENDATION, reason, None)


def test_ticks_bands_costs_lots_portfolio_and_settlement_are_enforced():
    result = build_recommendation(request(entry_zone=(50_101, 50_549)), portfolio())
    assert result.recommendation["planned_entry_limit"] == 50_500
    assert result.recommendation["regulatory_sellable_date"] == "2026-01-08"
    assert result.recommendation["policy_earliest_exit_fill_date"] == "2026-01-09"

    band = build_recommendation(request(entry_zone=(54_000, 54_000)), portfolio())
    assert (band.status, band.reason) == (NO_ACTIONABLE_RECOMMENDATION, "PRICE_BAND_GATE_FAILED")

    no_cash = PortfolioContext(1_000_000_000, 0, 10_000_000,
                               costs=CostModel(.001, .002, 10_000))
    rejected = build_recommendation(request(), no_cash)
    assert rejected.status == NO_ACTIONABLE_RECOMMENDATION
    assert rejected.reason.startswith("PORTFOLIO_GATE_FAILED:")
