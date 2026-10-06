"""Independent-source OHLCV reconciliation for P0 data reliability.

The validator never averages conflicting observations and never infers source
independence from different provider names alone. Independence must be backed
by explicit upstream-origin evidence supplied by provider governance.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence

from vnquant.config import parameter_value

from .models import CanonicalBar


class ReconciliationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    WARNING = "WARNING"
    QUARANTINED = "QUARANTINED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class IndependentDataQualityResult:
    checked_at: datetime
    source_names: tuple[str, ...]
    independent_origins: tuple[str, ...]
    latest_trading_session: date | None
    freshness: str
    missing_sessions: int
    duplicate_sessions: int
    ohlc_consistency: bool
    price_disagreement: float
    volume_disagreement: float
    corporate_action_warnings: int
    overall_quality_score: int
    validation_status: ReconciliationStatus
    issues: tuple[str, ...]
    buy_sell_allowed: bool


class IndependentDataValidator:
    """Reconcile canonical observations without hiding disagreement.

    By default the validator uses exact cross-source comparison. Optional
    tolerances may be injected only by a governed caller. This strict baseline
    avoids inventing an undocumented market-data tolerance inside the engine.
    """

    def __init__(self, *, price_tolerance: float | None = None,
                 volume_tolerance: float | None = None) -> None:
        self.price_tolerance = 0.0 if price_tolerance is None else float(price_tolerance)
        self.volume_tolerance = 0.0 if volume_tolerance is None else float(volume_tolerance)
        if self.price_tolerance < 0 or self.volume_tolerance < 0:
            raise ValueError("reconciliation tolerances cannot be negative")

    def evaluate(
        self,
        bars: Sequence[CanonicalBar],
        *,
        provider_origins: Mapping[str, str],
        expected_latest_session: date | datetime | None = None,
        expected_sessions: set[datetime] | None = None,
        unresolved_corporate_actions: set[tuple[str, date]] | None = None,
    ) -> IndependentDataQualityResult:
        checked_at = datetime.now(timezone.utc)
        if not bars:
            return IndependentDataQualityResult(
                checked_at, (), (), None, "UNAVAILABLE", 0, 0, True, 0.0, 0.0,
                0, 0, ReconciliationStatus.UNAVAILABLE,
                ("DATA_UNAVAILABLE",), False,
            )

        sources = tuple(sorted({bar.provider for bar in bars}))
        known_origins = {
            origin.strip()
            for provider in sources
            if (origin := str(provider_origins.get(provider, ""))).strip()
        }
        independent_origins = tuple(sorted(known_origins))
        latest = max(bar.timestamp.date() for bar in bars)
        expected_day = (
            expected_latest_session.date()
            if isinstance(expected_latest_session, datetime)
            else expected_latest_session
        )
        freshness = "FRESH"
        issues: list[str] = []
        blocking: set[str] = set()
        warnings: set[str] = set()

        if expected_day is not None and latest < expected_day:
            freshness = "STALE"
            issues.append("DATA_STALE")
            blocking.add("DATA_STALE")

        exact_seen: set[tuple[str, datetime, str]] = set()
        duplicate_sessions = 0
        grouped: dict[tuple[str, datetime], list[CanonicalBar]] = {}
        for bar in bars:
            key = (bar.symbol, bar.timestamp, bar.provider)
            if key in exact_seen:
                duplicate_sessions += 1
            exact_seen.add(key)
            grouped.setdefault((bar.symbol, bar.timestamp), []).append(bar)
        if duplicate_sessions:
            issues.append("DUPLICATE_SESSION")
            blocking.add("DUPLICATE_SESSION")

        missing_sessions = 0
        if expected_sessions is not None:
            for symbol in {bar.symbol for bar in bars}:
                for provider in {bar.provider for bar in bars if bar.symbol == symbol}:
                    present = {
                        bar.timestamp
                        for bar in bars
                        if bar.symbol == symbol and bar.provider == provider
                    }
                    missing_sessions += len(expected_sessions - present)
        if missing_sessions:
            issues.append("MISSING_SESSION")
            blocking.add("MISSING_SESSION")

        ohlc_consistency = all(
            bar.high >= max(bar.open, bar.close)
            and bar.low <= min(bar.open, bar.close)
            and bar.low <= bar.high
            and min(bar.open, bar.high, bar.low, bar.close) > 0
            and bar.volume >= 0
            for bar in bars
        )
        if not ohlc_consistency:
            issues.append("OHLC_INCONSISTENT")
            blocking.add("OHLC_INCONSISTENT")

        # Cross-source numerical comparison is meaningful only when every
        # source is already normalized to the same explicit unit/semantics.
        if len(sources) >= 2:
            raw_units = {str(bar.raw_price_unit).strip().upper() for bar in bars}
            semantics = {str(bar.price_semantics).strip().lower() for bar in bars}
            if len(raw_units) != 1 or "UNKNOWN" in raw_units or "" in raw_units:
                issues.append("RAW_PRICE_UNIT_MISMATCH")
                blocking.add("RAW_PRICE_UNIT_MISMATCH")
            if len(semantics) != 1 or "unknown" in semantics or "" in semantics:
                issues.append("PRICE_SEMANTICS_MISMATCH")
                blocking.add("PRICE_SEMANTICS_MISMATCH")

        price_disagreement = 0.0
        volume_disagreement = 0.0
        independent_overlap = False
        for observations in grouped.values():
            for left_index, left in enumerate(observations):
                left_origin = str(provider_origins.get(left.provider, "")).strip()
                for right in observations[left_index + 1:]:
                    right_origin = str(provider_origins.get(right.provider, "")).strip()
                    if not left_origin or not right_origin or left_origin == right_origin:
                        continue
                    independent_overlap = True
                    price_disagreement = max(
                        price_disagreement,
                        max(
                            _relative_difference(getattr(left, field), getattr(right, field))
                            for field in ("open", "high", "low", "close")
                        ),
                    )
                    volume_disagreement = max(
                        volume_disagreement,
                        _relative_difference(left.volume, right.volume),
                    )

        if price_disagreement > self.price_tolerance:
            issues.append("DATA_SOURCE_PRICE_MISMATCH")
            blocking.add("DATA_SOURCE_PRICE_MISMATCH")
        if volume_disagreement > self.volume_tolerance:
            issues.append("DATA_SOURCE_VOLUME_MISMATCH")
            blocking.add("DATA_SOURCE_VOLUME_MISMATCH")

        ca_warnings = sum(
            1 for bar in bars
            if unresolved_corporate_actions
            and (bar.symbol, bar.timestamp.date()) in unresolved_corporate_actions
        )
        if ca_warnings:
            issues.append("UNRESOLVED_CORPORATE_ACTION")
            blocking.add("UNRESOLVED_CORPORATE_ACTION")

        if len(sources) >= 2 and len(independent_origins) < 2:
            issues.append("INDEPENDENCE_UNPROVEN")
            blocking.add("INDEPENDENCE_UNPROVEN")
        elif len(sources) == 1:
            issues.append("SINGLE_SOURCE_ONLY")
            warnings.add("SINGLE_SOURCE_ONLY")
        elif not independent_overlap:
            issues.append("NO_OVERLAPPING_INDEPENDENT_SESSION")
            warnings.add("NO_OVERLAPPING_INDEPENDENT_SESSION")

        fail_penalty = int(parameter_value("dq.fail_penalty"))
        warn_penalty = int(parameter_value("dq.warn_penalty"))
        score = max(0, 100 - fail_penalty * len(blocking) - warn_penalty * len(warnings))

        if blocking:
            status = ReconciliationStatus.QUARANTINED
        elif len(independent_origins) >= 2 and independent_overlap:
            status = ReconciliationStatus.VERIFIED
        else:
            status = ReconciliationStatus.WARNING
        return IndependentDataQualityResult(
            checked_at=checked_at,
            source_names=sources,
            independent_origins=independent_origins,
            latest_trading_session=latest,
            freshness=freshness,
            missing_sessions=missing_sessions,
            duplicate_sessions=duplicate_sessions,
            ohlc_consistency=ohlc_consistency,
            price_disagreement=price_disagreement,
            volume_disagreement=volume_disagreement,
            corporate_action_warnings=ca_warnings,
            overall_quality_score=score,
            validation_status=status,
            issues=tuple(issues),
            buy_sell_allowed=status not in {
                ReconciliationStatus.QUARANTINED,
                ReconciliationStatus.UNAVAILABLE,
            },
        )


def _relative_difference(left: Decimal | int | float, right: Decimal | int | float) -> float:
    left_value = float(left)
    right_value = float(right)
    denominator = max(abs(left_value), abs(right_value), 1e-12)
    return abs(left_value - right_value) / denominator
