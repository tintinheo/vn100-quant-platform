"""DataFrame adapter for the canonical independent-source validator."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Mapping

import pandas as pd

from .models import CanonicalBar
from .reconciliation import IndependentDataQualityResult, IndependentDataValidator


def evaluate_canonical_frame(
    frame: pd.DataFrame,
    *,
    provider_origins: Mapping[str, str],
    expected_latest_session: date | datetime | None = None,
    price_tolerance: float | None = None,
    volume_tolerance: float | None = None,
) -> IndependentDataQualityResult:
    if frame is None or frame.empty:
        return IndependentDataValidator(
            price_tolerance=price_tolerance,
            volume_tolerance=volume_tolerance,
        ).evaluate([], provider_origins=provider_origins,
                   expected_latest_session=expected_latest_session)

    bars = [_bar_from_row(row) for row in frame.itertuples(index=False)]
    return IndependentDataValidator(
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
    ).evaluate(
        bars,
        provider_origins=provider_origins,
        expected_latest_session=expected_latest_session,
    )


def _bar_from_row(row) -> CanonicalBar:
    timestamp = _utc_datetime(getattr(row, "timestamp"))
    ingested_at = _utc_datetime(getattr(row, "ingested_at"))
    flags = getattr(row, "quality_flags", ())
    if flags is None or (isinstance(flags, float) and pd.isna(flags)):
        flags = ()
    elif not isinstance(flags, tuple):
        flags = tuple(flags) if isinstance(flags, (list, set)) else (str(flags),)
    return CanonicalBar(
        timestamp=timestamp,
        symbol=str(getattr(row, "symbol")),
        open=Decimal(str(getattr(row, "open"))),
        high=Decimal(str(getattr(row, "high"))),
        low=Decimal(str(getattr(row, "low"))),
        close=Decimal(str(getattr(row, "close"))),
        volume=int(getattr(row, "volume")),
        turnover=_decimal_or_none(getattr(row, "turnover", None)),
        adj_close=_decimal_or_none(getattr(row, "adj_close", None)),
        provider=str(getattr(row, "provider")),
        ingested_at=ingested_at,
        quality_flags=flags,
        raw_snapshot_id=str(getattr(row, "raw_snapshot_id")),
        trust_tier=str(getattr(row, "trust_tier", "unknown")),
        raw_price_unit=str(getattr(row, "raw_price_unit", "unknown")),
        price_semantics=str(getattr(row, "price_semantics", "unknown")),
        request_parameters=str(getattr(row, "request_parameters", "{}")),
        adapter_version=str(getattr(row, "adapter_version", "unknown")),
        source_reference=str(getattr(row, "source_reference", "unknown")),
        payload_sha256=str(getattr(row, "payload_sha256", "unknown")),
    )


def _utc_datetime(value) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(timezone.utc)
    else:
        timestamp = timestamp.tz_convert(timezone.utc)
    return timestamp.to_pydatetime()


def _decimal_or_none(value):
    if value is None or pd.isna(value):
        return None
    return Decimal(str(value))
