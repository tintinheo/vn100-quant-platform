from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from vnquant.config import parameter_value

@dataclass(frozen=True)
class BrokerCostProfile:
    commission_rate: float
    commission_includes_exchange_fee: bool=True
    exchange_fee_rate: float=0.00027  # [S] verified market-rule schedule; version by effective date.
    sell_tax_rate: float=0.001  # [S] verified tax rule; version by effective date.
    slippage_bps: float=float(parameter_value("execution.slippage_bps"))
    def buy_cost_rate(self):
        return self.commission_rate + (0 if self.commission_includes_exchange_fee else self.exchange_fee_rate) + self.slippage_bps/10000
    def sell_cost_rate(self):
        return self.commission_rate + (0 if self.commission_includes_exchange_fee else self.exchange_fee_rate) + self.sell_tax_rate + self.slippage_bps/10000

def hose_tick(price: float) -> int:
    # [S] HOSE tick schedule; keep aligned with versioned market_rules.yaml.
    if price < 10_000: return 10
    if price < 50_000: return 50
    return 100

def round_down_hose(price: float) -> float:
    # Decimal avoids binary-float artefacts at Vietnamese tick boundaries (e.g. 10,000 * 1.005).
    px=Decimal(str(price)).quantize(Decimal("0.000001")); tick=Decimal(str(hose_tick(float(px))))
    units=(px/tick).to_integral_value(rounding=ROUND_FLOOR)
    return float(units*tick)

def hose_floor(reference:float)->float:
    # [S] HOSE 7% band. Rounding implementation remains intentionally conservative.
    return round_down_hose(reference*(1-0.07))
