"""Canonical data-quality service used by ingestion, storage, and recommendations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable, Mapping, Sequence
from uuid import uuid4

import pandas as pd

from .models import CanonicalBar, DataIssue, DataQualityResult, QualityStatus

REQUIRED = {"symbol", "trading_date", "open", "high", "low", "close", "volume", "provider"}
CONFIDENCE_CAP_THRESHOLD = 70  # [D], BRD section 17
ACTIONABLE_BLOCK_THRESHOLD = 50  # [D], BRD section 17
_PENALTY = {QualityStatus.FAIL: 35, QualityStatus.WARN: 10, QualityStatus.PASS: 0}
HARD_BLOCK_CODES = frozenset({
    "INVALID_DATE", "MISSING_SESSION", "STALE_DATA", "PRICE_BAND_BREACH",
    "TRADING_STATUS_BLOCKED", "UNIT_UNKNOWN", "RAW_ADJUSTED_AMBIGUOUS",
    "LINEAGE_MISSING", "PROVIDER_NOT_ADMITTED", "UNRESOLVED_CORPORATE_ACTION",
    "DUPLICATE_BAR", "OHLC_LOGIC", "NEGATIVE_VOLUME", "NONPOSITIVE_PRICE",
})


@dataclass(frozen=True)
class DQEvaluation:
    evaluation_id: str
    canonical_revision: str
    checked_at: datetime
    results: tuple[DataQualityResult, ...]
    score: int
    status: QualityStatus
    confidence_capped: bool
    actionable: bool


class DataQualityService:
    """Evaluate canonical observations without repairing or averaging them."""

    def evaluate(
        self, bars: Sequence[CanonicalBar], *, expected_sessions: set[datetime] | None = None,
        expected_latest_session: date | datetime | None = None,
        admitted_providers: Iterable[str] | None = None,
        venues: Mapping[str, str] | None = None,
        venue_bands: Mapping[str, Decimal | float] | None = None,
        reference_prices: Mapping[tuple[str, date], Decimal | float] | None = None,
        trading_statuses: Mapping[tuple[str, date], str] | None = None,
        unresolved_corporate_actions: set[tuple[str, date]] | None = None,
        canonical_revision: str | None = None,
    ) -> DQEvaluation:
        checked = datetime.now(timezone.utc)
        revision = canonical_revision or uuid4().hex
        results: list[DataQualityResult] = []
        admitted = set(admitted_providers) if admitted_providers is not None else None
        exact: dict[tuple[str, datetime, str], CanonicalBar] = {}
        logical: dict[tuple[str, datetime], list[CanonicalBar]] = {}

        for bar in bars:
            key = (bar.symbol, bar.timestamp, bar.provider)
            if key in exact:
                results.append(self._result(checked, QualityStatus.FAIL, "DUPLICATE_BAR", "duplicate symbol/timestamp/provider", bar, revision))
            exact[key] = bar
            logical.setdefault((bar.symbol, bar.timestamp), []).append(bar)
            if admitted is not None and bar.provider not in admitted:
                results.append(self._result(checked, QualityStatus.FAIL, "PROVIDER_NOT_ADMITTED", "provider is not admitted for canonical use", bar, revision))
            if not bar.raw_snapshot_id or not bar.payload_sha256 or bar.payload_sha256 == "unknown" or not bar.source_reference or bar.source_reference == "unknown":
                results.append(self._result(checked, QualityStatus.FAIL, "LINEAGE_MISSING", "raw snapshot, payload hash, and source reference are required", bar, revision))
            if not bar.raw_price_unit or bar.raw_price_unit.lower() == "unknown":
                results.append(self._result(checked, QualityStatus.FAIL, "UNIT_UNKNOWN", "raw price unit is unknown", bar, revision))
            semantics = (bar.price_semantics or "").lower()
            if semantics not in {"raw", "adjusted"}:
                results.append(self._result(checked, QualityStatus.FAIL, "RAW_ADJUSTED_AMBIGUOUS", "price semantics must explicitly be raw or adjusted", bar, revision))
            day = bar.timestamp.date()
            if unresolved_corporate_actions and (bar.symbol, day) in unresolved_corporate_actions:
                results.append(self._result(checked, QualityStatus.FAIL, "UNRESOLVED_CORPORATE_ACTION", "corporate action remains unresolved", bar, revision))
            status = (trading_statuses or {}).get((bar.symbol, day), "NORMAL").upper()
            if status not in {"NORMAL", "TRADING"}:
                results.append(self._result(checked, QualityStatus.FAIL, "TRADING_STATUS_BLOCKED", f"trading status is {status}", bar, revision))
            ref = (reference_prices or {}).get((bar.symbol, day))
            venue = (venues or {}).get(bar.symbol)
            band = (venue_bands or {}).get(venue) if venue else None
            if ref is not None and band is not None:
                lower, upper = Decimal(str(ref)) * (1 - Decimal(str(band))), Decimal(str(ref)) * (1 + Decimal(str(band)))
                if bar.low < lower or bar.high > upper:
                    results.append(self._result(checked, QualityStatus.FAIL, "PRICE_BAND_BREACH", "OHLC exceeds the supplied venue price band", bar, revision))

        compared = ("open", "high", "low", "close", "volume", "turnover", "adj_close")
        for observations in logical.values():
            if len({bar.provider for bar in observations}) >= 2 and any(
                getattr(observations[0], field) != getattr(bar, field)
                for bar in observations[1:] for field in compared
            ):
                first = observations[0]
                results.append(DataQualityResult(str(uuid4()), checked, QualityStatus.WARN,
                    "PROVIDER_DISAGREEMENT", "providers disagree; observations retained separately and were not averaged",
                    first.provider, first.symbol, first.timestamp,
                    tuple(bar.raw_snapshot_id for bar in observations), revision))

        if expected_sessions is not None:
            for symbol in {bar.symbol for bar in bars}:
                present = {bar.timestamp for bar in bars if bar.symbol == symbol}
                for missing in sorted(expected_sessions - present):
                    results.append(DataQualityResult(str(uuid4()), checked, QualityStatus.FAIL,
                        "MISSING_SESSION", "expected session is absent; no bar was forward-filled",
                        symbol=symbol, timestamp=missing, canonical_revision=revision))
        if expected_latest_session is not None and bars:
            expected_day = expected_latest_session.date() if isinstance(expected_latest_session, datetime) else expected_latest_session
            for symbol in {bar.symbol for bar in bars}:
                newest = max(bar.timestamp.date() for bar in bars if bar.symbol == symbol)
                if newest < expected_day:
                    sample = next(bar for bar in bars if bar.symbol == symbol)
                    results.append(self._result(checked, QualityStatus.FAIL, "STALE_DATA", f"latest bar {newest} precedes expected session {expected_day}", sample, revision))

        score = max(0, 100 - sum(_PENALTY[result.status] for result in results))
        hard_block = any(result.code in HARD_BLOCK_CODES for result in results)
        status = QualityStatus.FAIL if hard_block or score < ACTIONABLE_BLOCK_THRESHOLD else (QualityStatus.WARN if results else QualityStatus.PASS)
        return DQEvaluation(uuid4().hex, revision, checked, tuple(results), score, status,
                            score < CONFIDENCE_CAP_THRESHOLD, score >= ACTIONABLE_BLOCK_THRESHOLD and not hard_block)

    @staticmethod
    def _result(checked, status, code, message, bar, revision):
        return DataQualityResult(str(uuid4()), checked, status, code, message, bar.provider,
                                 bar.symbol, bar.timestamp, (bar.raw_snapshot_id,), revision)


def validate_canonical_bars(bars: list[CanonicalBar], **kwargs) -> list[DataQualityResult]:
    """Compatibility facade; all canonical validation is implemented here."""
    return list(DataQualityService().evaluate(bars, **kwargs).results)


def validate_bars(df: pd.DataFrame) -> list[DataIssue]:
    """Validate pre-canonical provider frames through the canonical DQ boundary."""
    issues: list[DataIssue] = []
    missing = REQUIRED - set(df.columns)
    if missing:
        return [DataIssue("ERROR", "SCHEMA_MISSING", f"Missing columns: {sorted(missing)}")]
    if df.empty:
        return [DataIssue("ERROR", "EMPTY", "No bars returned")]
    parsed = pd.to_datetime(df["trading_date"], errors="coerce")
    if parsed.isna().any():
        issues.append(DataIssue("ERROR", "INVALID_DATE", f"{int(parsed.isna().sum())} invalid trading dates"))
    if df.duplicated(["symbol", "trading_date"]).any():
        issues.append(DataIssue("ERROR", "DUPLICATE", "Duplicate symbol/date rows"))
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1)) | (df["low"] > df["high"])
    if bad.any(): issues.append(DataIssue("ERROR", "OHLC_LOGIC", f"{int(bad.sum())} rows violate OHLC invariants"))
    if (df["volume"] < 0).any(): issues.append(DataIssue("ERROR", "NEGATIVE_VOLUME", "Negative volume found"))
    for column in ["open", "high", "low", "close"]:
        if (df[column] <= 0).any(): issues.append(DataIssue("ERROR", "NONPOSITIVE_PRICE", f"Non-positive {column}"))
    if not parsed.dropna().is_monotonic_increasing: issues.append(DataIssue("WARN", "UNSORTED", "Bars are not sorted by trading_date"))
    return issues


def quality_score(issues: Sequence[DataIssue | DataQualityResult]) -> int:
    severity = {"ERROR": 35, "FAIL": 35, "WARN": 10, "INFO": 0, "PASS": 0}
    return max(0, 100 - sum(severity[getattr(item.severity if isinstance(item, DataIssue) else item.status, "value", item.severity if isinstance(item, DataIssue) else item.status)] for item in issues))


def apply_dq_policy(confidence: float, dq_score: int) -> tuple[float, bool]:
    """Apply BRD §17 [D] thresholds; confidence is capped to the DQ score."""
    return (min(confidence, float(dq_score)) if dq_score < CONFIDENCE_CAP_THRESHOLD else confidence,
            dq_score >= ACTIONABLE_BLOCK_THRESHOLD)
