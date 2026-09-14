from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Mapping


def _utc(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True)
class RawSnapshot:
    """Immutable evidence captured before normalization."""

    snapshot_id: str
    provider: str
    ingested_at: datetime
    payload: bytes
    payload_sha256: str
    source_reference: str | None = None
    request_parameters: Mapping[str, Any] | None = None
    adapter_version: str | None = None
    trust_tier: str | None = None
    raw_price_unit: str | None = None
    price_semantics: str | None = None

    def __post_init__(self) -> None:
        import hashlib

        _utc(self.ingested_at, "ingested_at")
        actual = hashlib.sha256(self.payload).hexdigest()
        if actual != self.payload_sha256:
            raise ValueError("payload_sha256 does not match payload")


@dataclass(frozen=True)
class CanonicalBar:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    turnover: Decimal | None
    adj_close: Decimal | None
    provider: str
    ingested_at: datetime
    quality_flags: tuple[str, ...]
    raw_snapshot_id: str
    trust_tier: str = "unknown"
    raw_price_unit: str = "unknown"
    price_semantics: str = "unknown"
    request_parameters: str = "{}"
    adapter_version: str = "unknown"
    source_reference: str = "unknown"
    payload_sha256: str = "unknown"

    def __post_init__(self) -> None:
        _utc(self.timestamp, "timestamp")
        _utc(self.ingested_at, "ingested_at")
        if not self.raw_snapshot_id:
            raise ValueError("raw_snapshot_id is required for lineage")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close) or self.low > self.high:
            raise ValueError("OHLC values are inconsistent")


@dataclass(frozen=True)
class ProviderMetadata:
    provider: str
    display_name: str
    trust_tier: str
    access_basis: str
    schema_version: str
    raw_adjusted_policy: str
    timezone: str
    reviewed_at: datetime
    admitted: bool = False

    def __post_init__(self) -> None:
        _utc(self.reviewed_at, "reviewed_at")


class QualityStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class DataQualityResult:
    result_id: str
    checked_at: datetime
    status: QualityStatus
    code: str
    message: str
    provider: str | None = None
    symbol: str | None = None
    timestamp: datetime | None = None
    raw_snapshot_ids: tuple[str, ...] = ()
    canonical_revision: str | None = None

    def __post_init__(self) -> None:
        _utc(self.checked_at, "checked_at")
        if self.timestamp is not None:
            _utc(self.timestamp, "timestamp")


@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    action_type: str
    source: str
    source_snapshot_id: str
    ratio: float | None = None
    cash_amount: float | None = None
    announced_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_snapshot_id:
            raise ValueError("source_snapshot_id is required for lineage")
        if self.announced_at is not None:
            _utc(self.announced_at, "announced_at")


@dataclass(frozen=True)
class UniverseMembership:
    index_code: str
    symbol: str
    effective_from: date
    effective_to: date | None
    source: str
    source_snapshot_id: str

    def __post_init__(self) -> None:
        if not self.source_snapshot_id:
            raise ValueError("source_snapshot_id is required for lineage")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


@dataclass(frozen=True)
class SectorMembership:
    symbol: str
    sector_code: str
    sector_name: str
    taxonomy: str
    effective_from: date
    effective_to: date | None
    source: str
    source_snapshot_id: str

    def __post_init__(self) -> None:
        if not self.source_snapshot_id:
            raise ValueError("source_snapshot_id is required for lineage")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


@dataclass(frozen=True)
class IndexBar:
    timestamp: datetime
    index_code: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    turnover: Decimal | None
    provider: str
    ingested_at: datetime
    quality_flags: tuple[str, ...]
    raw_snapshot_id: str

    def __post_init__(self) -> None:
        _utc(self.timestamp, "timestamp")
        _utc(self.ingested_at, "ingested_at")
        if not self.raw_snapshot_id:
            raise ValueError("raw_snapshot_id is required for lineage")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close) or self.low > self.high:
            raise ValueError("OHLC values are inconsistent")


# Compatibility types used by the existing v3.3 feature pipeline.
@dataclass(frozen=True)
class Bar:
    symbol: str
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None
    provider: str = "unknown"


@dataclass(frozen=True)
class UniverseMember:
    symbol: str
    index_code: str = "VN100"
    effective_from: date | None = None
    effective_to: date | None = None
    source: str = "unknown"


@dataclass(frozen=True)
class DataIssue:
    severity: Literal["INFO", "WARN", "ERROR"]
    code: str
    message: str
    symbol: str | None = None
    trading_date: date | None = None


@dataclass(frozen=True)
class AdjustmentAnomaly:
    symbol: str
    trading_date: date
    factor_ratio: float
    note: str = "Adjustment-factor jump; action type is UNKNOWN until verified from official disclosure."
