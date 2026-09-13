from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from ..base import CANONICAL_COLUMNS


class ProviderConfigurationError(RuntimeError):
    """Raised before I/O when an authorized provider contract is unavailable."""


class ProviderResponseError(RuntimeError):
    """Raised when a remote response cannot be mapped without guessing."""


def canonical_frame(
    records: list[Mapping[str, Any]],
    *,
    field_map: Mapping[str, str],
    provider_id: str,
    price_multiplier: float,
    volume_multiplier: float,
    value_multiplier: float,
) -> pd.DataFrame:
    """Map explicitly named provider fields into the existing canonical frame."""
    multipliers = (price_multiplier, volume_multiplier, value_multiplier)
    if any(not isinstance(value, (int, float)) or value <= 0 for value in multipliers):
        raise ProviderConfigurationError("unit multipliers must be positive numbers")
    required = {"trading_date", "open", "high", "low", "close", "volume"}
    missing_mapping = required.difference(field_map)
    if missing_mapping:
        raise ProviderConfigurationError(
            f"field mapping is incomplete: {sorted(missing_mapping)}"
        )

    rows: list[dict[str, Any]] = []
    for record in records:
        try:
            row = {
                canonical: record[provider_field]
                for canonical, provider_field in field_map.items()
                if canonical in set(CANONICAL_COLUMNS) - {"provider"}
            }
        except KeyError as exc:
            raise ProviderResponseError(f"mapped response field is absent: {exc.args[0]}") from exc
        row["provider"] = provider_id
        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    if "symbol" not in frame:
        raise ProviderResponseError("response has no mapped symbol field")
    frame["trading_date"] = pd.to_datetime(frame["trading_date"], errors="raise").dt.date
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise") * price_multiplier
    frame["volume"] = (
        pd.to_numeric(frame["volume"], errors="raise") * volume_multiplier
    )
    if "value" not in frame:
        frame["value"] = pd.NA
    else:
        frame["value"] = (
            pd.to_numeric(frame["value"], errors="raise") * value_multiplier
        )
    return frame[CANONICAL_COLUMNS]


def unix_seconds(value: date) -> int:
    return int(pd.Timestamp(value, tz="UTC").timestamp())
