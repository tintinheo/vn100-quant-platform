from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

CANONICAL_COLUMNS = ["symbol","trading_date","open","high","low","close","volume","value","provider"]

class MarketDataProvider(ABC):
    @abstractmethod
    def current_index_members(self, index_code: str = "VN100") -> list[str]: ...

    @abstractmethod
    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...

    def close(self) -> None:
        return None
