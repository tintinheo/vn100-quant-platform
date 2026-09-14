import pandas as pd

from vnquant.portfolio import (CostModel, PortfolioContext, PortfolioPosition,
                               PortfolioRiskService)


def recommendation(**overrides):
    row = {"symbol": "AAA", "sector": "BANK", "correlated_group": "BANK",
           "entry_price": 50_000, "risk_stop": 47_500, "adv_shares": 1_000_000}
    row.update(overrides)
    return pd.DataFrame([row])


def context(**overrides):
    values = {"account_equity": 1_000_000_000, "available_cash": 1_000_000_000,
              "maximum_permitted_loss": 10_000_000,
              "costs": CostModel(buy_rate=.001, sell_rate=.001, fixed_cost=10_000)}
    values.update(overrides)
    return PortfolioContext(**values)


def test_sizes_from_stop_cost_lot_and_maximum_loss():
    row = PortfolioRiskService().evaluate(recommendation(risk_stop=45_000), context(), "STRONG_BULL").iloc[0]
    assert row.status == "ACCEPTED"
    assert row.binding_constraint == "RISK_BUDGET"
    assert row.quantity == 1900 and row.quantity % 100 == 0
    assert row.estimated_loss <= 10_000_000
    assert row.configuration_version.startswith("quant-parameters-v1")


def test_liquidity_ceiling_resizes_and_is_auditable():
    row = PortfolioRiskService().evaluate(
        recommendation(adv_shares=50_000), context(), "STRONG_BULL").iloc[0]
    assert (row.status, row.quantity, row.binding_constraint) == (
        "RESIZED", 1500, "LIQUIDITY_PARTICIPATION")
    assert row.decision_id and row.decided_at


def test_rejects_missing_or_invalid_stop_and_liquidity():
    service = PortfolioRiskService()
    assert service.evaluate(recommendation(risk_stop=None), context(), "RANGE").iloc[0].binding_constraint == "RISK_STOP_INVALID"
    assert service.evaluate(recommendation(adv_shares=None), context(), "RANGE").iloc[0].binding_constraint == "LIQUIDITY_UNAVAILABLE"
    assert service.evaluate(recommendation(risk_stop=49_900), context(), "RANGE").iloc[0].binding_constraint == "MINIMUM_STOP_DISTANCE"


def test_rejects_when_risk_budget_cannot_buy_minimum_lot():
    row = PortfolioRiskService().evaluate(
        recommendation(), context(maximum_permitted_loss=100_000), "STRONG_BULL").iloc[0]
    assert (row.status, row.binding_constraint) == ("REJECTED", "MINIMUM_LOT_RISK")


def test_existing_positions_enforce_sector_correlated_concurrent_and_exposure():
    position = PortfolioPosition("OLD", "BANK", "BANK", 2000, 50_000, 47_500)
    row = PortfolioRiskService().evaluate(
        recommendation(), context(positions=(position,)), "STRONG_BULL").iloc[0]
    assert row.status == "RESIZED" and row.binding_constraint == "CORRELATED_EXPOSURE"

    correlated = tuple(PortfolioPosition(f"B{i}", "BANK", "BANK", 100, 10_000, 9_000)
                       for i in range(2))
    row = PortfolioRiskService().evaluate(recommendation(), context(positions=correlated), "STRONG_BULL").iloc[0]
    assert row.binding_constraint == "CORRELATED_POSITION_LIMIT"

    positions = tuple(PortfolioPosition(f"S{i}", f"SEC{i}", f"G{i}", 100, 10_000, 9_000)
                      for i in range(10))
    row = PortfolioRiskService().evaluate(recommendation(), context(positions=positions), "STRONG_BULL").iloc[0]
    assert row.binding_constraint == "CONCURRENT_POSITION_LIMIT"


def test_regime_limit_can_resize_total_exposure():
    existing = PortfolioPosition("OLD", "OTHER", "OTHER", 4000, 100_000, 95_000)
    row = PortfolioRiskService().evaluate(
        recommendation(), context(positions=(existing,)), "RISK_OFF").iloc[0]
    assert (row.status, row.binding_constraint) == ("REJECTED", "TOTAL_EXPOSURE")


def test_ranked_recommendations_reserve_capacity_for_following_decisions():
    recs = pd.concat([recommendation(symbol="AAA"), recommendation(symbol="BBB")], ignore_index=True)
    rows = PortfolioRiskService().evaluate(recs, context(), "STRONG_BULL")
    assert list(rows.symbol) == ["AAA", "BBB"]
    assert set(rows.status) <= {"ACCEPTED", "RESIZED", "REJECTED"}


def test_decisions_persist_append_only_with_binding_constraint_and_version(tmp_path):
    from vnquant.data.storage import Warehouse

    warehouse = Warehouse(tmp_path)
    service = PortfolioRiskService()
    first = service.evaluate(recommendation(), context(), "STRONG_BULL")
    second = service.evaluate(recommendation(symbol="BBB", adv_shares=None), context(), "STRONG_BULL")
    warehouse.persist_portfolio_risk_decisions(first)
    warehouse.persist_portfolio_risk_decisions(second)
    stored = warehouse.read_table("portfolio_risk_decisions")
    assert list(stored.status) == ["RESIZED", "REJECTED"]
    assert list(stored.binding_constraint) == ["SECURITY_EXPOSURE", "LIQUIDITY_UNAVAILABLE"]
    assert stored.configuration_version.nunique() == 1


def test_invalid_cost_or_unknown_regime_fails_closed():
    bad_cost = context(costs=CostModel(buy_rate=-0.01))
    assert PortfolioRiskService().evaluate(recommendation(), bad_cost, "STRONG_BULL").iloc[0].binding_constraint == "COST_MODEL_INVALID"
    assert PortfolioRiskService().evaluate(recommendation(), context(), "UNKNOWN").iloc[0].binding_constraint == "REGIME_LIMIT_UNAVAILABLE"
