from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from ..base import DataMode, MarketDataProvider
from .common import ProviderConfigurationError, ProviderResponseError, canonical_frame


@dataclass(frozen=True)
class VietstockDataFeedContract:
    """Authorized vendor contract; deliberately has no guessed endpoint defaults."""

    authorized: bool = False
    base_url: str = ""
    authentication: Mapping[str, str] = field(default_factory=dict, repr=False)
    paths: Mapping[str, str] = field(default_factory=dict)
    parameters: Mapping[str, str] = field(default_factory=dict)
    response_record_paths: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    schema_mapping: Mapping[str, str] = field(default_factory=dict)
    units: Mapping[str, str | float] = field(default_factory=dict)
    revision_policy: str = ""
    rate_limits: str = ""
    usage_rights: str = ""

    def validate(self) -> None:
        missing: list[str] = []
        if self.authorized is not True:
            missing.append("authorized")
        scalar = {
            "base_url": self.base_url,
            "authentication": self.authentication,
            "revision_policy": self.revision_policy,
            "rate_limits": self.rate_limits,
            "usage_rights": self.usage_rights,
        }
        missing.extend(name for name, value in scalar.items() if not value)
        requirements = {
            "paths": {"current_index_members", "daily_history"},
            "parameters": {"index_code", "symbol", "start", "end"},
            "response_record_paths": {"current_index_members", "daily_history"},
            "schema_mapping": {"symbol", "trading_date", "open", "high", "low", "close", "volume"},
            "units": {"price_multiplier", "volume_multiplier", "value_multiplier"},
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
        try:
            multipliers = tuple(
                float(self.units[name])
                for name in ("price_multiplier", "volume_multiplier", "value_multiplier")
            )
        except (TypeError, ValueError) as exc:
            raise ProviderConfigurationError(
                "Vietstock unit multipliers must be numeric"
            ) from exc
        if any(value <= 0 for value in multipliers):
            raise ProviderConfigurationError(
                "Vietstock unit multipliers must be positive"
            )


class VietstockDataFeedProvider(MarketDataProvider):
    provider_id = "vietstock_datafeed"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL

    def __init__(
        self,
        contract: VietstockDataFeedContract | None = None,
        *,
        transport: Callable[..., Any] | None = None,
    ) -> None:
        self.contract = contract or VietstockDataFeedContract()
        self.transport = transport

    def _request(self, operation: str, parameters: Mapping[str, str]) -> list[Mapping[str, Any]]:
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
        for component in self.contract.response_record_paths[operation]:
            if not isinstance(payload, Mapping) or component not in payload:
                raise ProviderResponseError(
                    f"authorized Vietstock response lacks record path component {component!r}"
                )
            payload = payload[component]
        if not isinstance(payload, list) or not all(isinstance(row, Mapping) for row in payload):
            raise ProviderResponseError("authorized Vietstock response is not a record list")
        return payload

    def current_index_members(self, index_code: str = "VN100") -> list[str]:
        self.contract.validate()
        rows = self._request(
            "current_index_members", {self.contract.parameters["index_code"]: index_code}
        )
        symbol_field = self.contract.schema_mapping["symbol"]
        try:
            symbols = [str(row[symbol_field]).strip().upper() for row in rows]
        except KeyError as exc:
            raise ProviderResponseError(f"mapped response field is absent: {exc.args[0]}") from exc
        if not symbols or any(not symbol for symbol in symbols):
            raise ProviderResponseError("Vietstock response has no complete symbol list")
        return sorted(set(symbols))

    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        self.contract.validate()
        parameters = {
            self.contract.parameters["symbol"]: symbol.upper(),
            self.contract.parameters["start"]: start.isoformat(),
            self.contract.parameters["end"]: end.isoformat(),
        }
        symbol_field = self.contract.schema_mapping["symbol"]
        rows = [
            dict(row, **{symbol_field: row.get(symbol_field, symbol.upper())})
            for row in self._request("daily_history", parameters)
        ]
        return canonical_frame(
            rows,
            field_map=self.contract.schema_mapping,
            provider_id=self.provider_id,
            price_multiplier=float(self.contract.units["price_multiplier"]),
            volume_multiplier=float(self.contract.units["volume_multiplier"]),
            value_multiplier=float(self.contract.units["value_multiplier"]),
        )
