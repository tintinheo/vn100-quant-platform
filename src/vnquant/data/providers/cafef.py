from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from html.parser import HTMLParser

import pandas as pd

from ..base import CANONICAL_COLUMNS, DataMode, MarketDataProvider, ProviderFetch
from .common import ProviderConfigurationError, ProviderResponseError


class _FirstTableParser(HTMLParser):
    """Small dependency-free parser for the explicit public-table contract."""

    def __init__(self) -> None:
        super().__init__()
        self.table_depth = 0
        self.cell: list[str] | None = None
        self.row: list[str] | None = None
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self.table_depth += 1
        elif self.table_depth == 1 and tag == "tr":
            self.row = []
        elif self.table_depth == 1 and self.row is not None and tag in {"th", "td"}:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.table_depth == 1 and tag in {"th", "td"} and self.cell is not None:
            assert self.row is not None
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif self.table_depth == 1 and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.table_depth:
            self.table_depth -= 1

    def frame(self) -> pd.DataFrame:
        if len(self.rows) < 2:
            raise ProviderResponseError("CafeF public page contains no populated table")
        header, records = self.rows[0], self.rows[1:]
        if any(len(record) != len(header) for record in records):
            raise ProviderResponseError("CafeF HTML table has inconsistent columns")
        return pd.DataFrame(records, columns=header)


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
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.allow_reference_source = allow_reference_source
        self.page_fetcher = page_fetcher
        self._now = now or (lambda: datetime.now(timezone.utc))

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
        return ProviderFetch(self.provider_id, payload, self._now(),
            {"symbol": symbol.upper(), "start": start.isoformat(), "end": end.isoformat()},
            self.adapter_version, url, "reference_only", "thousand_VND", "adjustment_semantics_unverified")

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        parser = _FirstTableParser()
        parser.feed(fetched.payload.decode("utf-8"))
        aliases = {
            "trading_date": ("Ngày", "Ngay"),
            "open": ("Mở cửa", "Mo cua"),
            "high": ("Cao nhất", "Cao nhat"),
            "low": ("Thấp nhất", "Thap nhat"),
            "close": ("Đóng cửa", "Dong cua"),
            "volume": ("KL khớp lệnh", "KL giao dịch", "KLGD"),
        }
        table = parser.frame()
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
