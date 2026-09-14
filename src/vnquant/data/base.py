from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping
import pandas as pd

CANONICAL_COLUMNS = ["symbol","trading_date","open","high","low","close","volume","value","provider"]

class DataMode(str, Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"
    TEST = "test"


@dataclass(frozen=True)
class ProviderFetch:
    """Unmodified provider evidence and the context needed to interpret it."""

    provider: str
    payload: bytes
    retrieved_at: datetime
    request_parameters: Mapping[str, Any]
    adapter_version: str
    source_reference: str
    trust_tier: str
    raw_price_unit: str
    price_semantics: str

    def __post_init__(self) -> None:
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if not self.payload:
            raise ValueError("provider payload must not be empty")

class MarketDataProvider(ABC):
    """Provider-neutral boundary for market-data implementations."""

    provider_id: str
    capabilities: frozenset[str]
    data_mode: DataMode

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        raise NotImplementedError("provider must implement raw universe fetch")

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        raise NotImplementedError("provider must implement raw price fetch")

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        raise NotImplementedError

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        raise NotImplementedError

    # Compatibility conveniences. Ingestion code must use fetch -> snapshot -> normalize.
    def current_index_members(self, index_code: str = "VN100") -> list[str]:
        return self.normalize_index_members(self.fetch_current_index_members(index_code))

    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        return self.normalize_daily_history(self.fetch_daily_history(symbol, start, end))

    def close(self) -> None:
        return None
