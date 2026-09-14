"""Canonical v3.3 table contracts and cross-row integrity checks."""
from __future__ import annotations

from dataclasses import fields
from .models import CanonicalBar, DataQualityResult

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
    """Compatibility import; :mod:`quality` is the sole DQ implementation."""
    from .quality import validate_canonical_bars as canonical_validate
    return canonical_validate(bars, expected_sessions=expected_sessions)
