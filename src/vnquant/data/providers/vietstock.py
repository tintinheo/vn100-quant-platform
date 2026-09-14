from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import json
from typing import Any

import pandas as pd

from ..base import DataMode, MarketDataProvider, ProviderFetch
from .common import ProviderConfigurationError, ProviderResponseError, canonical_frame


@dataclass(frozen=True)
class VietstockDataFeedContract:
    """Authorized vendor contract; deliberately has no guessed endpoint defaults."""

    authorized: bool = False
    base_url: str = ""
    authentication: Mapping[str, str] = field(default_factory=dict, repr=False)
    paths: Mapping[str, str] = field(default_factory=dict)
    parameters: Mapping[str, str] = field(default_factory=dict)
    schema_mapping: Mapping[str, str] = field(default_factory=dict)
    units: Mapping[str, str | float] = field(default_factory=dict)
    endpoint_semantics: str = ""
    revision_policy: str = ""
    rate_limits: str = ""
    retention_rights: str = ""
    usage_rights: str = ""

    def validate(self) -> None:
        missing: list[str] = []
        if self.authorized is not True:
            missing.append("authorized")
        scalar = {
            "base_url": self.base_url,
            "authentication": self.authentication,
            "endpoint_semantics": self.endpoint_semantics,
            "revision_policy": self.revision_policy,
            "rate_limits": self.rate_limits,
            "retention_rights": self.retention_rights,
            "usage_rights": self.usage_rights,
        }
        missing.extend(name for name, value in scalar.items() if not value)
        requirements = {
            "paths": {"current_index_members", "daily_history"},
            "parameters": {"index_code", "symbol", "start", "end"},
            "schema_mapping": {"symbol", "trading_date", "open", "high", "low", "close", "volume"},
            "units": {"price_multiplier"},
        }
        for name, keys in requirements.items():
            value = getattr(self, name)
            absent = keys.difference(value)
            if absent:
                missing.append(f"{name}[{','.join(sorted(absent))}]")
        if missing:
            raise ProviderConfigurationError(
                "incomplete authorized Vietstock DataFeed contract: " + ", ".join(missing)
            )


class VietstockDataFeedProvider(MarketDataProvider):
    provider_id = "vietstock_datafeed"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL
    adapter_version = "1"
    trust_tier = "licensed_candidate"

    def __init__(
        self,
        contract: VietstockDataFeedContract | None = None,
        *,
        transport: Callable[..., Any] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.contract = contract or VietstockDataFeedContract()
        self.transport = transport
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _request(self, operation: str, parameters: Mapping[str, str]) -> ProviderFetch:
        self.contract.validate()
        if self.transport is None:
            raise ProviderConfigurationError("authorized Vietstock transport is not injected")
        response = self.transport(
            base_url=self.contract.base_url,
            path=self.contract.paths[operation],
            authentication=dict(self.contract.authentication),
            parameters=dict(parameters),
        )
        payload = response.json() if callable(getattr(response, "json", None)) else response
        return ProviderFetch(self.provider_id, json.dumps(payload, sort_keys=True, default=str).encode(),
            self._now(), dict(parameters), self.adapter_version,
            self.contract.base_url + self.contract.paths[operation], self.trust_tier,
            str(self.contract.units.get("raw_price_unit", "contract_defined")),
            str(self.contract.units.get("price_semantics", "contract_defined")))

    @staticmethod
    def _rows(fetched: ProviderFetch) -> list[Mapping[str, Any]]:
        payload = json.loads(fetched.payload)
        if not isinstance(payload, list) or not all(isinstance(row, Mapping) for row in payload):
            raise ProviderResponseError("authorized Vietstock response is not a record list")
        return payload

    def fetch_current_index_members(self, index_code: str = "VN100") -> ProviderFetch:
        self.contract.validate()
        return self._request(
            "current_index_members", {self.contract.parameters["index_code"]: index_code}
        )

    def normalize_index_members(self, fetched: ProviderFetch) -> list[str]:
        rows = self._rows(fetched)
        symbol_field = self.contract.schema_mapping["symbol"]
        try:
            symbols = [str(row[symbol_field]).strip().upper() for row in rows]
        except KeyError as exc:
            raise ProviderResponseError(f"mapped response field is absent: {exc.args[0]}") from exc
        if not symbols or any(not symbol for symbol in symbols):
            raise ProviderResponseError("Vietstock response has no complete symbol list")
        return sorted(set(symbols))

    def fetch_daily_history(self, symbol: str, start: date, end: date) -> ProviderFetch:
        self.contract.validate()
        parameters = {
            self.contract.parameters["symbol"]: symbol.upper(),
            self.contract.parameters["start"]: start.isoformat(),
            self.contract.parameters["end"]: end.isoformat(),
        }
        return self._request("daily_history", parameters)

    def normalize_daily_history(self, fetched: ProviderFetch) -> pd.DataFrame:
        symbol_key = self.contract.parameters["symbol"]
        symbol = str(fetched.request_parameters[symbol_key])
        rows = [dict(row, **{self.contract.schema_mapping["symbol"]: row.get(self.contract.schema_mapping["symbol"], symbol)}) for row in self._rows(fetched)]
        return canonical_frame(
            rows,
            field_map=self.contract.schema_mapping,
            provider_id=self.provider_id,
            price_multiplier=float(self.contract.units["price_multiplier"]),
        )
