from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
import json
from typing import Any, Protocol

import pandas as pd

from ..base import DataMode, MarketDataProvider, ProviderFetch
from .common import ProviderConfigurationError, ProviderResponseError, canonical_frame, unix_seconds


class DNSEMarketDataClient(Protocol):
    """Only the documented read-only market-data surface used by this adapter."""

    def get_instruments(self, **kwargs: Any) -> Any: ...

    def get_ohlc(self, **kwargs: Any) -> Any: ...


# [GUESS] Live DNSE resolution, accepted VN100 index-name literal, response
# schema, units, available history depth, and quota/rate-limit behavior remain
# unverified. The request/schema/unit assumptions used here are injectable; the
# adapter must not be admitted until each assumption has supporting evidence.
DEFAULT_DNSE_FIELD_MAP = {
    "symbol": "symbol",
    "trading_date": "time",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
}


class DNSEProvider(MarketDataProvider):
    """DNSE read-only market-data adapter; it intentionally exposes no trading API."""

    provider_id = "dnse_openapi"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL
    read_only = True
    adapter_version = "1"
    trust_tier = "candidate"
    raw_price_unit = "provider_native_[GUESS]"
    price_semantics = "raw_ohlc_[GUESS]"

    def __init__(
        self,
        client: DNSEMarketDataClient | None = None,
        *,
        client_factory: Callable[[], DNSEMarketDataClient] | None = None,
        resolution: str = "1D",  # [GUESS]
        index_name: str = "VN100",  # [GUESS]
        field_map: Mapping[str, str] = DEFAULT_DNSE_FIELD_MAP,  # [GUESS]
        price_multiplier: float = 1.0,  # [GUESS] pending live unit verification
    ) -> None:
        self._client = client
        self._client_factory = client_factory
        self.resolution = resolution
        self.index_name = index_name
        self.field_map = dict(field_map)
        self.price_multiplier = price_multiplier

    @property
    def client(self) -> DNSEMarketDataClient:
        if self._client is None:
            if self._client_factory is None:
                raise ProviderConfigurationError(
                    "DNSE requires an injected official read-only SDK client/factory"
                )
            self._client = self._client_factory()
        return self._client

    @staticmethod
    def _records(response: Any) -> list[Mapping[str, Any]]:
        payload = response.json() if callable(getattr(response, "json", None)) else response
        # [GUESS] Accepted live envelope names must be replaced/confirmed from captured evidence.
        if isinstance(payload, Mapping):
            payload = payload.get("data", payload.get("items", payload.get("records")))
        if not isinstance(payload, list) or not all(isinstance(x, Mapping) for x in payload):
            raise ProviderResponseError("unverified DNSE response does not contain a record list")
        return payload

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        parameters = {"index_name": index_code or self.index_name, "limit": 100, "page": 1,
                      "dry_run": False}
        response = self.client.get_instruments(
            **parameters
        )
        payload = response.json() if callable(getattr(response, "json", None)) else response
        return ProviderFetch(self.provider_id, json.dumps(payload, sort_keys=True, default=str).encode(),
            datetime.now(timezone.utc), parameters, self.adapter_version, "GET /instruments",
            self.trust_tier, "not_applicable", "universe_membership")

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        records = self._records(json.loads(fetched.payload))
        symbols = [str(row.get("symbol", "")).strip().upper() for row in records]
        if not symbols or any(not symbol for symbol in symbols):
            raise ProviderResponseError("DNSE instrument response has no complete symbol list")
        return sorted(set(symbols))

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        parameters = {"bar_type": "STOCK", "query": {"symbol": symbol.upper(),
            "resolution": self.resolution, "from": unix_seconds(start), "to": unix_seconds(end)},
            "dry_run": False}
        response = self.client.get_ohlc(
            **parameters,
        )
        payload = response.json() if callable(getattr(response, "json", None)) else response
        return ProviderFetch(self.provider_id, json.dumps(payload, sort_keys=True, default=str).encode(),
            datetime.now(timezone.utc), parameters, self.adapter_version, "GET /price/ohlc",
            self.trust_tier, self.raw_price_unit, self.price_semantics)

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        symbol = str(fetched.request_parameters["query"]["symbol"])
        records = [dict(row, symbol=row.get("symbol", symbol)) for row in self._records(json.loads(fetched.payload))]
        date_field = self.field_map.get("trading_date")
        # [GUESS] The default schema treats numeric timestamps as Unix seconds.
        if date_field:
            for record in records:
                if isinstance(record.get(date_field), (int, float)):
                    record[date_field] = pd.to_datetime(
                        record[date_field], unit="s", utc=True, errors="raise"
                    ).date()
        return canonical_frame(
            records,
            field_map=self.field_map,
            provider_id=self.provider_id,
            price_multiplier=self.price_multiplier,
        )
