from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
from typing import Any, Protocol

import pandas as pd

from ..base import DataMode, MarketDataProvider, ProviderFetch
from .common import (
    DataProviderErrorCode,
    ProviderConfigurationError,
    ProviderResponseError,
    canonical_frame,
    decode_provider_json_response,
    unix_seconds,
)
from vnquant.config import parameter_value


class DNSEMarketDataClient(Protocol):
    """Only the documented read-only market-data surface used by this adapter."""

    def get_instruments(self, **kwargs: Any) -> Any: ...

    def get_ohlc(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, repr=False)
class DNSECredentials:
    api_key: str
    api_secret: str


class DNSECredentialSource:
    """Resolve DNSE data credentials without embedding or logging their values."""

    def __init__(self, api_key_reference: str, api_secret_reference: str, *, secret_store=None):
        self.api_key_reference = api_key_reference
        self.api_secret_reference = api_secret_reference
        self.secret_store = secret_store

    def resolve(self) -> DNSECredentials:
        def value(reference: str):
            environment_value = os.environ.get(reference)
            if environment_value:
                return environment_value
            if self.secret_store is None:
                return None
            getter = self.secret_store.get if isinstance(self.secret_store, Mapping) else self.secret_store
            try:
                return getter(reference)
            except (FileNotFoundError, KeyError):
                return None

        api_key = value(self.api_key_reference)
        api_secret = value(self.api_secret_reference)
        if not api_key or not api_secret:
            raise ProviderConfigurationError(
                "DNSE read-only credentials are unavailable from the configured environment/secret store"
            )
        return DNSECredentials(str(api_key), str(api_secret))


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
    capabilities = frozenset({"daily_ohlcv", "current_index_members", "index_daily_ohlct"})
    data_mode = DataMode.REAL
    read_only = True
    adapter_version = "2"
    trust_tier = "candidate"
    raw_price_unit = "provider_native_[GUESS]"
    price_semantics = "raw_ohlc_[GUESS]"

    def __init__(
        self,
        client: DNSEMarketDataClient | None = None,
        *,
        client_factory: Callable[[DNSECredentials], DNSEMarketDataClient] | None = None,
        credential_source: DNSECredentialSource | None = None,
        now: Callable[[], datetime] | None = None,
        resolution: str | None = None,
        index_name: str | None = None,
        field_map: Mapping[str, str] = DEFAULT_DNSE_FIELD_MAP,
        price_multiplier: float | None = None,
    ) -> None:
        self._client = client
        self._client_factory = client_factory
        self._credential_source = credential_source
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.resolution = resolution or str(parameter_value("provider.dnse_resolution"))
        self.index_name = index_name or str(parameter_value("provider.dnse_index_name"))
        self.field_map = dict(field_map)
        self.price_multiplier = float(price_multiplier if price_multiplier is not None else parameter_value("provider.dnse_price_multiplier"))

    @property
    def client(self) -> DNSEMarketDataClient:
        if self._client is None:
            if self._client_factory is None:
                raise ProviderConfigurationError(
                    "DNSE requires an injected official read-only SDK client/factory"
                )
            if self._credential_source is None:
                raise ProviderConfigurationError("DNSE credential source is not configured")
            self._client = self._client_factory(self._credential_source.resolve())
        return self._client

    @classmethod
    def _decode(cls, response: Any) -> Any:
        return decode_provider_json_response(response, provider_id=cls.provider_id)

    @classmethod
    def _records(cls, response: Any) -> list[Mapping[str, Any]]:
        payload = cls._decode(response)
        if isinstance(payload, Mapping):
            payload = payload.get("data", payload.get("items", payload.get("records")))
        if not isinstance(payload, list) or not all(isinstance(x, Mapping) for x in payload):
            raise ProviderResponseError(
                "unverified DNSE response does not contain a record list",
                code=DataProviderErrorCode.SCHEMA_ERROR,
                provider_id=cls.provider_id,
            )
        return payload

    def _provider_fetch(self, response: Any, parameters: Mapping[str, Any], source_reference: str,
                        raw_price_unit: str, price_semantics: str) -> ProviderFetch:
        payload = self._decode(response)
        if not isinstance(payload, (Mapping, list)):
            raise ProviderResponseError(
                "DNSE JSON root is not an object or record list",
                code=DataProviderErrorCode.SCHEMA_ERROR,
                provider_id=self.provider_id,
            )
        return ProviderFetch(
            self.provider_id,
            json.dumps(payload, sort_keys=True, default=str).encode(),
            self._now(),
            dict(parameters),
            self.adapter_version,
            source_reference,
            self.trust_tier,
            raw_price_unit,
            price_semantics,
        )

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        parameters = {"index_name": index_code or self.index_name, "limit": 100, "page": 1,
                      "dry_run": False}
        response = self.client.get_instruments(**parameters)
        return self._provider_fetch(
            response,
            parameters,
            "GET /instruments",
            "not_applicable",
            "universe_membership",
        )

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        records = self._records(json.loads(fetched.payload))
        symbols = [str(row.get("symbol", "")).strip().upper() for row in records]
        if not symbols or any(not symbol for symbol in symbols):
            raise ProviderResponseError(
                "DNSE instrument response has no complete symbol list",
                code=DataProviderErrorCode.SCHEMA_ERROR,
                provider_id=self.provider_id,
            )
        return sorted(set(symbols))

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        parameters = {"bar_type": "STOCK", "query": {"symbol": symbol.upper(),
            "resolution": self.resolution, "from": unix_seconds(start), "to": unix_seconds(end)},
            "dry_run": False}
        response = self.client.get_ohlc(**parameters)
        return self._provider_fetch(
            response,
            parameters,
            "GET /price/ohlc",
            self.raw_price_unit,
            self.price_semantics,
        )

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        symbol = str(fetched.request_parameters["query"]["symbol"])
        records = [dict(row, symbol=row.get("symbol", symbol)) for row in self._records(json.loads(fetched.payload))]
        date_field = self.field_map.get("trading_date")
        if date_field:
            try:
                for record in records:
                    if isinstance(record.get(date_field), (int, float)):
                        record[date_field] = pd.to_datetime(
                            record[date_field], unit="s", utc=True, errors="raise"
                        ).date()
            except (TypeError, ValueError, OverflowError) as exc:
                raise ProviderResponseError(
                    "DNSE trading-date field cannot be normalized",
                    code=DataProviderErrorCode.SCHEMA_ERROR,
                    provider_id=self.provider_id,
                ) from exc
        return canonical_frame(
            records,
            field_map=self.field_map,
            provider_id=self.provider_id,
            price_multiplier=self.price_multiplier,
        )

    def fetch_index_daily_history(self, index_code: str, start: date, end: date) -> ProviderFetch:
        parameters = {"bar_type": "INDEX", "query": {"symbol": index_code.upper(),
            "resolution": self.resolution, "from": unix_seconds(start), "to": unix_seconds(end)},
            "dry_run": False}
        response = self.client.get_ohlc(**parameters)
        return self._provider_fetch(
            response,
            parameters,
            "GET /price/ohlc",
            self.raw_price_unit,
            "official_index_raw_ohlc_[GUESS]",
        )

    def normalize_index_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        frame = self.normalize_daily_history(fetched)
        records = self._records(json.loads(fetched.payload))
        if records and all("value" in record for record in records):
            try:
                frame["value"] = pd.to_numeric([record["value"] for record in records], errors="raise")
            except (TypeError, ValueError) as exc:
                raise ProviderResponseError(
                    "DNSE index turnover field cannot be normalized",
                    code=DataProviderErrorCode.SCHEMA_ERROR,
                    provider_id=self.provider_id,
                ) from exc
        return frame.rename(columns={"symbol": "index_code", "value": "turnover"})
