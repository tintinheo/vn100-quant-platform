"""Fail-closed portfolio-risk sizing and constraint enforcement."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Iterable, Mapping
from uuid import uuid4

import pandas as pd

from vnquant.config import parameter_value, parameters_version


class RiskDecisionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    RESIZED = "RESIZED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class CostModel:
    buy_rate: float = 0.0
    sell_rate: float = 0.0
    fixed_cost: float = 0.0


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    sector: str
    correlated_group: str
    quantity: int
    market_price: float
    risk_stop: float


@dataclass(frozen=True)
class PortfolioContext:
    account_equity: float
    available_cash: float
    maximum_permitted_loss: float
    positions: tuple[PortfolioPosition, ...] = ()
    costs: CostModel = CostModel()


@dataclass(frozen=True)
class RiskDecision:
    decision_id: str
    decided_at: str
    symbol: str
    status: str
    quantity: int
    entry_price: float | None
    risk_stop: float | None
    estimated_loss: float
    notional: float
    binding_constraint: str
    configuration_version: str
    regime: str

    def asdict(self) -> dict:
        return asdict(self)


def _number(value) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


class PortfolioRiskService:
    """Evaluate ranked recommendations sequentially against one portfolio snapshot.

    Accepted decisions reserve capacity for later rows, so callers must supply their
    intended priority order. Every outcome is returned for append-only persistence.
    """

    def __init__(self, *, config_version: str | None = None):
        self.config_version = config_version or parameters_version()

    def evaluate(self, recommendations: pd.DataFrame, context: PortfolioContext,
                 regime: str) -> pd.DataFrame:
        decisions: list[RiskDecision] = []
        positions = list(context.positions)
        reserved: list[PortfolioPosition] = []
        for row in recommendations.to_dict("records"):
            decision = self._evaluate_one(row, context, regime, positions + reserved)
            decisions.append(decision)
            if decision.status != RiskDecisionStatus.REJECTED.value:
                reserved.append(PortfolioPosition(
                    symbol=decision.symbol, sector=str(row.get("sector", "UNKNOWN")),
                    correlated_group=str(row.get("correlated_group", row.get("sector", "UNKNOWN"))),
                    quantity=decision.quantity, market_price=float(decision.entry_price),
                    risk_stop=float(decision.risk_stop)))
        columns = [field for field in RiskDecision.__dataclass_fields__]
        return pd.DataFrame([d.asdict() for d in decisions], columns=columns)

    def _reject(self, symbol: str, regime: str, constraint: str,
                entry: float | None = None, stop: float | None = None) -> RiskDecision:
        return self._decision(symbol, regime, RiskDecisionStatus.REJECTED, 0, entry, stop,
                              0.0, constraint)

    def _decision(self, symbol, regime, status, qty, entry, stop, loss, constraint):
        return RiskDecision(str(uuid4()), datetime.now(timezone.utc).isoformat(), symbol,
                            status.value, int(qty), entry, stop, float(loss),
                            float(qty * entry) if entry is not None else 0.0,
                            constraint, self.config_version, str(regime))

    def _evaluate_one(self, row: Mapping, context: PortfolioContext, regime: str,
                      positions: Iterable[PortfolioPosition]) -> RiskDecision:
        symbol = str(row.get("symbol", ""))
        entry, stop, adv = (_number(row.get(k)) for k in ("entry_price", "risk_stop", "adv_shares"))
        if not symbol:
            return self._reject(symbol, regime, "INVALID_SYMBOL", entry, stop)
        if entry is None or entry <= 0:
            return self._reject(symbol, regime, "ENTRY_PRICE_UNAVAILABLE", entry, stop)
        if stop is None or stop <= 0 or stop >= entry:
            return self._reject(symbol, regime, "RISK_STOP_INVALID", entry, stop)
        stop_fraction = (entry - stop) / entry
        if stop_fraction < float(parameter_value("portfolio.minimum_stop_fraction")):
            return self._reject(symbol, regime, "MINIMUM_STOP_DISTANCE", entry, stop)
        if stop_fraction > float(parameter_value("portfolio.maximum_stop_fraction")):
            return self._reject(symbol, regime, "MAXIMUM_STOP_DISTANCE", entry, stop)
        if adv is None or adv <= 0:
            return self._reject(symbol, regime, "LIQUIDITY_UNAVAILABLE", entry, stop)
        if context.account_equity <= 0 or context.available_cash < 0 or context.maximum_permitted_loss <= 0:
            return self._reject(symbol, regime, "RISK_CONTEXT_INVALID", entry, stop)

        lot = int(parameter_value("portfolio.lot_size"))
        cost = context.costs
        if cost.buy_rate < 0 or cost.sell_rate < 0 or cost.fixed_cost < 0:
            return self._reject(symbol, regime, "COST_MODEL_INVALID", entry, stop)
        regime_limits = parameter_value("portfolio.regime_limits")
        if str(regime) not in regime_limits:
            return self._reject(symbol, regime, "REGIME_LIMIT_UNAVAILABLE", entry, stop)
        per_share_loss = entry - stop + entry * cost.buy_rate + stop * cost.sell_rate
        loss_budget = min(context.maximum_permitted_loss,
                          context.account_equity * float(parameter_value("portfolio.risk_per_trade"))
                          * float(regime_limits[str(regime)]["risk_multiplier"]))
        if loss_budget <= cost.fixed_cost or per_share_loss <= 0:
            return self._reject(symbol, regime, "MAXIMUM_PERMITTED_LOSS", entry, stop)
        raw_qty = math.floor((loss_budget - cost.fixed_cost) / per_share_loss / lot) * lot
        if raw_qty < lot:
            return self._reject(symbol, regime, "MINIMUM_LOT_RISK", entry, stop)

        current = list(positions)
        if len(current) >= int(parameter_value("portfolio.maximum_concurrent_positions")):
            return self._reject(symbol, regime, "CONCURRENT_POSITION_LIMIT", entry, stop)
        exposure = sum(p.quantity * p.market_price for p in current)
        open_risk = sum(max(0.0, p.market_price - p.risk_stop) * p.quantity for p in current)
        sector = str(row.get("sector", "UNKNOWN"))
        group = str(row.get("correlated_group", sector))
        sector_exposure = sum(p.quantity * p.market_price for p in current if p.sector == sector)
        correlated_exposure = sum(p.quantity * p.market_price for p in current if p.correlated_group == group)
        correlated_count = sum(1 for p in current if p.correlated_group == group)
        if correlated_count >= int(parameter_value("portfolio.maximum_correlated_positions")):
            return self._reject(symbol, regime, "CORRELATED_POSITION_LIMIT", entry, stop)

        limits = regime_limits[str(regime)]
        ceilings = {
            "RISK_BUDGET": raw_qty,
            "AVAILABLE_CASH": math.floor(context.available_cash / entry / lot) * lot,
            "SECURITY_EXPOSURE": math.floor(context.account_equity * float(parameter_value("portfolio.maximum_security_exposure")) / entry / lot) * lot,
            "TOTAL_EXPOSURE": math.floor(max(0.0, context.account_equity * float(limits["total_exposure"]) - exposure) / entry / lot) * lot,
            "SECTOR_CONCENTRATION": math.floor(max(0.0, context.account_equity * float(parameter_value("portfolio.maximum_sector_exposure")) - sector_exposure) / entry / lot) * lot,
            "CORRELATED_EXPOSURE": math.floor(max(0.0, context.account_equity * float(parameter_value("portfolio.maximum_correlated_exposure")) - correlated_exposure) / entry / lot) * lot,
            "LIQUIDITY_PARTICIPATION": math.floor(adv * float(parameter_value("portfolio.maximum_adv_participation")) / lot) * lot,
            "TOTAL_OPEN_RISK": math.floor(max(0.0, context.account_equity * float(parameter_value("portfolio.maximum_total_open_risk")) - open_risk - cost.fixed_cost) / per_share_loss / lot) * lot,
        }
        binding, quantity = min(ceilings.items(), key=lambda item: (item[1], item[0]))
        if quantity < lot:
            return self._reject(symbol, regime, binding, entry, stop)
        estimated_loss = quantity * per_share_loss + cost.fixed_cost
        if estimated_loss > context.maximum_permitted_loss + 1e-9:
            return self._reject(symbol, regime, "MAXIMUM_PERMITTED_LOSS", entry, stop)
        min_notional = float(parameter_value("portfolio.minimum_notional"))
        if quantity * entry < min_notional:
            return self._reject(symbol, regime, "MINIMUM_NOTIONAL", entry, stop)
        status = RiskDecisionStatus.ACCEPTED if binding == "RISK_BUDGET" else RiskDecisionStatus.RESIZED
        return self._decision(symbol, regime, status, quantity, entry, stop, estimated_loss, binding)
