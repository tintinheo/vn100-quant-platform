from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
import pandas as pd

CANONICAL_COLUMNS = ["symbol","trading_date","open","high","low","close","volume","value","provider"]

class DataMode(str, Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"
    TEST = "test"

class MarketDataProvider(ABC):
    """Provider-neutral boundary for market-data implementations."""

    provider_id: str
    capabilities: frozenset[str]
    data_mode: DataMode

    @abstractmethod
    def current_index_members(self, index_code: str = "VN100") -> list[str]: ...

    @abstractmethod
    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...

    def close(self) -> None:
        return None
