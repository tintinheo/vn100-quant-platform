"""Canonical v3.3 table contracts and cross-row integrity checks."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from uuid import uuid4

from .models import CanonicalBar, DataQualityResult, QualityStatus

CANONICAL_BAR_FIELDS = (
    "timestamp", "symbol", "open", "high", "low", "close", "volume",
    "turnover", "adj_close", "provider", "ingested_at", "quality_flags",
    "raw_snapshot_id",
    "trust_tier", "raw_price_unit", "price_semantics", "request_parameters",
    "adapter_version", "source_reference", "payload_sha256",
)


def assert_canonical_bar_schema() -> None:
    actual = tuple(field.name for field in fields(CanonicalBar))
    if actual != CANONICAL_BAR_FIELDS:
        raise AssertionError(f"CanonicalBar schema changed: {actual!r}")


def validate_canonical_bars(
    bars: list[CanonicalBar], *, expected_sessions: set[datetime] | None = None
) -> list[DataQualityResult]:
    """Report duplicates, gaps, and disagreements without modifying observations."""
    now = datetime.now(timezone.utc)
    results: list[DataQualityResult] = []
    exact_keys: dict[tuple[str, datetime, str], CanonicalBar] = {}
    logical: dict[tuple[str, datetime], list[CanonicalBar]] = {}
    for bar in bars:
        key = (bar.symbol, bar.timestamp, bar.provider)
        if key in exact_keys:
            results.append(_result(now, QualityStatus.FAIL, "DUPLICATE_BAR", "duplicate symbol/timestamp/provider", bar))
        else:
            exact_keys[key] = bar
        logical.setdefault((bar.symbol, bar.timestamp), []).append(bar)

    compared = ("open", "high", "low", "close", "volume", "turnover", "adj_close")
    for observations in logical.values():
        if len({bar.provider for bar in observations}) < 2:
            continue
        if any(getattr(observations[0], field) != getattr(bar, field)
               for bar in observations[1:] for field in compared):
            first = observations[0]
            results.append(DataQualityResult(
                result_id=str(uuid4()), checked_at=now, status=QualityStatus.WARN,
                code="PROVIDER_DISAGREEMENT",
                message="providers disagree; observations retained separately and were not averaged",
                symbol=first.symbol, timestamp=first.timestamp,
                raw_snapshot_ids=tuple(bar.raw_snapshot_id for bar in observations),
            ))

    if expected_sessions is not None:
        symbols = {bar.symbol for bar in bars}
        for symbol in symbols:
            present = {bar.timestamp for bar in bars if bar.symbol == symbol}
            for missing in sorted(expected_sessions - present):
                results.append(DataQualityResult(
                    result_id=str(uuid4()), checked_at=now, status=QualityStatus.FAIL,
                    code="MISSING_SESSION", message="expected session is absent; no bar was forward-filled",
                    symbol=symbol, timestamp=missing,
                ))
    return results


def _result(checked_at: datetime, status: QualityStatus, code: str,
            message: str, bar: CanonicalBar) -> DataQualityResult:
    return DataQualityResult(str(uuid4()), checked_at, status, code, message,
                             bar.provider, bar.symbol, bar.timestamp, (bar.raw_snapshot_id,))
