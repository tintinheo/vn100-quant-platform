from __future__ import annotations
from datetime import date
from pathlib import Path
import pandas as pd
from .base import MarketDataProvider, CANONICAL_COLUMNS

class CSVProvider(MarketDataProvider):
    """Deterministic offline provider for exported real data / fixtures.
    Files: <root>/<SYMBOL>.csv; universe.csv with one `symbol` column.
    """
    name="csv"
    def __init__(self, root: str | Path): self.root=Path(root)
    def current_index_members(self,index_code="VN100"):
        p=self.root/f"{index_code.lower()}_universe.csv"
        df=pd.read_csv(p)
        return sorted(df.symbol.astype(str).str.upper().unique().tolist())
    def daily_history(self,symbol,start,end):
        p=self.root/f"{symbol.upper()}.csv"
        df=pd.read_csv(p)
        rename={c:c.strip().lower() for c in df.columns}; df=df.rename(columns=rename)
        df["trading_date"]=pd.to_datetime(df["trading_date"]).dt.date
        df=df[(df.trading_date>=start)&(df.trading_date<=end)].copy()
        df["symbol"]=symbol.upper(); df["provider"]=self.name
        if "value" not in df: df["value"]=None
        return df[CANONICAL_COLUMNS].sort_values("trading_date").reset_index(drop=True)
