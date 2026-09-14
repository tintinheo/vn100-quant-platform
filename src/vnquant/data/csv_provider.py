from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd

from .base import CANONICAL_COLUMNS, DataMode, MarketDataProvider, ProviderFetch


class CSVProvider(MarketDataProvider):
    """Authorized file importer which returns exact file bytes before parsing."""

    provider_id = "authorized_csv_import"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL
    adapter_version = "2"

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _fetch(self, path: Path, parameters: dict[str, str], *, unit: str,
               semantics: str) -> ProviderFetch:
        return ProviderFetch(
            provider=self.provider_id,
            payload=path.read_bytes(),
            retrieved_at=datetime.now(timezone.utc),
            request_parameters=parameters,
            adapter_version=self.adapter_version,
            source_reference=str(path.resolve()),
            trust_tier="authorized_manual_import",
            raw_price_unit=unit,
            price_semantics=semantics,
        )

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        path = self.root / f"{index_code.lower()}_universe.csv"
        return self._fetch(path, {"index_code": index_code}, unit="not_applicable",
                           semantics="effective_date_semantics_from_authorized_file")

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        frame = pd.read_csv(BytesIO(fetched.payload))
        return sorted(frame.symbol.astype(str).str.upper().unique().tolist())

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        path = self.root / f"{symbol.upper()}.csv"
        return self._fetch(path, {"symbol": symbol.upper(), "start": start.isoformat(),
            "end": end.isoformat()}, unit="file_declared_or_VND_[GUESS]",
            semantics="raw_vs_adjusted_must_be_authorized_in_file_contract")

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        frame = pd.read_csv(BytesIO(fetched.payload))
        frame = frame.rename(columns={column: column.strip().lower() for column in frame.columns})
        frame["trading_date"] = pd.to_datetime(frame["trading_date"]).dt.date
        start = date.fromisoformat(str(fetched.request_parameters["start"]))
        end = date.fromisoformat(str(fetched.request_parameters["end"]))
        frame = frame[(frame.trading_date >= start) & (frame.trading_date <= end)].copy()
        frame["symbol"] = str(fetched.request_parameters["symbol"])
        frame["provider"] = self.provider_id
        if "value" not in frame:
            frame["value"] = None
        return frame[CANONICAL_COLUMNS].sort_values("trading_date").reset_index(drop=True)
