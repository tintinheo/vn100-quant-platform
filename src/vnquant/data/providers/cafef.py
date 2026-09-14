from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone

import pandas as pd

from ..base import CANONICAL_COLUMNS, DataMode, MarketDataProvider, ProviderFetch
from .common import ProviderConfigurationError, ProviderResponseError


class CafeFReferenceProvider(MarketDataProvider):
    """Explicit, disabled-by-default public-HTML reference validator only."""

    provider_id = "cafef_reference"
    capabilities = frozenset({"reference_daily_ohlcv"})
    data_mode = DataMode.REAL
    reference_only = True
    primary_eligible = False
    adapter_version = "1"

    def __init__(
        self,
        *,
        allow_reference_source: bool = False,
        page_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.allow_reference_source = allow_reference_source
        self.page_fetcher = page_fetcher

    def _require_enabled(self) -> None:
        if not self.allow_reference_source:
            raise ProviderConfigurationError("CafeF reference validation is disabled")
        if self.page_fetcher is None:
            raise ProviderConfigurationError("an authorized public-HTML page fetcher is required")

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        raise ProviderConfigurationError("CafeF is not an authoritative VN100 membership source")

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        raise ProviderConfigurationError("CafeF is not an authoritative VN100 membership source")

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        self._require_enabled()
        # Public HTML only; never an undocumented JSON/XHR endpoint.
        url = f"https://cafef.vn/du-lieu/lich-su-giao-dich-{symbol.lower()}-1.chn"
        payload = self.page_fetcher(url).encode("utf-8")
        return ProviderFetch(self.provider_id, payload, datetime.now(timezone.utc),
            {"symbol": symbol.upper(), "start": start.isoformat(), "end": end.isoformat()},
            self.adapter_version, url, "reference_only", "thousand_VND", "adjustment_semantics_unverified")

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        from io import BytesIO
        tables = pd.read_html(BytesIO(fetched.payload))
        if not tables:
            raise ProviderResponseError("CafeF public page contains no table")
        aliases = {
            "trading_date": ("Ngày", "Ngay"),
            "open": ("Mở cửa", "Mo cua"),
            "high": ("Cao nhất", "Cao nhat"),
            "low": ("Thấp nhất", "Thap nhat"),
            "close": ("Đóng cửa", "Dong cua"),
            "volume": ("KL khớp lệnh", "KL giao dịch", "KLGD"),
        }
        table = tables[0]
        selected: dict[str, object] = {}
        for canonical, candidates in aliases.items():
            match = next((column for column in table.columns if any(name in str(column) for name in candidates)), None)
            if match is None:
                raise ProviderResponseError(f"CafeF HTML layout lacks {canonical!r}")
            selected[canonical] = table[match]
        frame = pd.DataFrame(selected)
        frame["symbol"] = str(fetched.request_parameters["symbol"])
        frame["provider"] = self.provider_id
        frame["trading_date"] = pd.to_datetime(frame["trading_date"], dayfirst=True, errors="raise").dt.date
        start, end = (date.fromisoformat(str(fetched.request_parameters[key])) for key in ("start", "end"))
        frame = frame[(frame["trading_date"] >= start) & (frame["trading_date"] <= end)]
        for column in ("open", "high", "low", "close"):
            frame[column] = pd.to_numeric(frame[column], errors="raise") * 1_000
        frame["volume"] = pd.to_numeric(frame["volume"], errors="raise")
        frame["value"] = pd.NA
        return frame[CANONICAL_COLUMNS]
