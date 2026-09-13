from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

@dataclass(frozen=True)
class Bar:
    symbol: str
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None
    provider: str = "unknown"

@dataclass(frozen=True)
class UniverseMember:
    symbol: str
    index_code: str = "VN100"
    effective_from: date | None = None
    effective_to: date | None = None
    source: str = "unknown"

@dataclass(frozen=True)
class DataIssue:
    severity: Literal["INFO", "WARN", "ERROR"]
    code: str
    message: str
    symbol: str | None = None
    trading_date: date | None = None

@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    action_type: str
    source: str
    ratio: float | None = None
    cash_amount: float | None = None
    announced_at: datetime | None = None

@dataclass(frozen=True)
class AdjustmentAnomaly:
    symbol: str
    trading_date: date
    factor_ratio: float
    note: str = "Adjustment-factor jump; action type is UNKNOWN until verified from official disclosure."
