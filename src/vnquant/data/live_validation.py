"""Live secondary-source validation without contaminating canonical analytics.

The primary provider remains the canonical analytics source. A secondary
provider is fetched only for reconciliation and its observations are persisted
in a separate validation table. No provider observations are averaged.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time as day_time, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping
from uuid import uuid4

import pandas as pd

from vnquant.config.provider_origins import (
    provider_origin_config_version,
    verified_provider_origins,
)

from .base import DataMode, ProviderFetch
from .models import CanonicalBar, RawSnapshot
from .provider_registry import ProviderRegistry
from .quality import validate_bars
from .reconciliation import (
    IndependentDataQualityResult,
    ReconciliationStatus,
)
from .reconciliation_frame import evaluate_canonical_frame
from .storage import Warehouse


@dataclass(frozen=True)
class LiveIndependentValidationReport:
    report_id: str
    validation_key: str
    sync_run_id: str
    checked_at: str
    data_as_of: str | None
    primary_provider_id: str | None
    validator_provider_id: str | None
    validation_status: str
    overall_quality_score: int
    source_names: tuple[str, ...]
    independent_origins: tuple[str, ...]
    issues: tuple[str, ...]
    symbol_statuses: Mapping[str, str]
    symbol_scores: Mapping[str, int]
    raw_snapshot_ids: tuple[str, ...]
    buy_sell_allowed: bool
    origin_config_version: str
    cache_hit: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "LiveIndependentValidationReport":
        data = dict(value)
        for field in ("source_names", "independent_origins", "issues", "raw_snapshot_ids"):
            data[field] = tuple(data.get(field, ()))
        data["symbol_statuses"] = dict(data.get("symbol_statuses", {}))
        data["symbol_scores"] = {
            str(key): int(score) for key, score in dict(data.get("symbol_scores", {})).items()
        }
        return cls(**data)


class LiveIndependentValidationService:
    """Fetch one governed secondary source and reconcile latest-session OHLCV.

    A provider is eligible only when it is ADMITTED for ``daily_ohlcv`` and
    both the primary and validator have explicit, verified, *different*
    upstream-origin IDs. Missing independent evidence yields WARNING rather
    than a fabricated VERIFIED result.
    """

    CACHE_NAME = "independent_validation_result.json"
    VALIDATION_TABLE = "independent_validation_observations"
    REPORT_TABLE = "independent_validation_reports"
    VALIDATOR_PREFERENCE = ("vietstock_datafeed",)

    def __init__(
        self,
        data_dir: str | Path,
        *,
        registry: ProviderRegistry,
        provider_origins: Mapping[str, str] | None = None,
        now: Callable[[], datetime] | None = None,
        price_tolerance: float | None = None,
        volume_tolerance: float | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.registry = registry
        self.provider_origins = dict(
            verified_provider_origins() if provider_origins is None else provider_origins
        )
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.price_tolerance = price_tolerance
        self.volume_tolerance = volume_tolerance
        self.cache_path = self.data_dir / self.CACHE_NAME

    def validate(self, sync_report, *, force: bool = False) -> LiveIndependentValidationReport:
        admitted = tuple(sorted(self.registry.admitted_provider_ids("daily_ohlcv")))
        expected = getattr(sync_report, "last_accepted_market_date", None)
        primary = getattr(sync_report, "provider_id", None)
        sync_run_id = str(getattr(sync_report, "run_id", ""))
        validation_key = self._validation_key(sync_run_id, primary, expected, admitted)
        if not force:
            cached = self._load_cache()
            if cached and cached.validation_key == validation_key:
                return replace(cached, cache_hit=True)

        if not getattr(sync_report, "actionable", False) or not primary or not expected:
            return self._persist(self._unavailable(
                validation_key, sync_run_id, primary, expected, "PRIMARY_SYNC_NOT_ACTIONABLE"
            ))

        expected_day = date.fromisoformat(str(expected))
        try:
            primary_frame = Warehouse(self.data_dir).read_table("canonical_bars")
            primary_frame = self._latest_primary_frame(primary_frame, primary, expected_day)
        except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
            return self._persist(self._unavailable(
                validation_key, sync_run_id, primary, expected, "PRIMARY_CANONICAL_DATA_UNAVAILABLE"
            ))
        if primary_frame.empty:
            return self._persist(self._unavailable(
                validation_key, sync_run_id, primary, expected, "PRIMARY_LATEST_SESSION_UNAVAILABLE"
            ))

        validator_id = self._select_validator(primary, admitted)
        report_id = uuid4().hex
        raw_snapshot_ids: list[str] = []
        symbol_results: dict[str, IndependentDataQualityResult] = {}
        validation_observations: list[dict] = []
        validator = None
        try:
            if validator_id is not None:
                validator = self.registry.select(
                    provider_id=validator_id,
                    capability="daily_ohlcv",
                    mode=DataMode.REAL,
                )

            for symbol in sorted(primary_frame.symbol.astype(str).str.upper().unique()):
                primary_symbol = primary_frame[
                    primary_frame.symbol.astype(str).str.upper() == symbol
                ].copy()
                if validator is None:
                    result = evaluate_canonical_frame(
                        primary_symbol,
                        provider_origins=self.provider_origins,
                        expected_latest_session=expected_day,
                        price_tolerance=self.price_tolerance,
                        volume_tolerance=self.volume_tolerance,
                    )
                    code = (
                        "PRIMARY_ORIGIN_UNVERIFIED"
                        if primary not in self.provider_origins
                        else "NO_INDEPENDENT_VALIDATOR_ADMITTED"
                    )
                    symbol_results[symbol] = self._warning(result, code)
                    continue

                try:
                    fetched = validator.fetch_daily_history(symbol, expected_day, expected_day)
                    snapshot = self._store_fetch(fetched)
                    raw_snapshot_ids.append(snapshot.snapshot_id)
                    frame = validator.normalize_daily_history(fetched)
                    issues = validate_bars(frame)
                    if frame.empty or any(issue.severity == "ERROR" for issue in issues):
                        raise ValueError("validator DQ failed")
                    frame = frame[pd.to_datetime(frame.trading_date).dt.date == expected_day].copy()
                    if frame.empty:
                        raise ValueError("validator latest session is absent")
                    secondary = pd.DataFrame([
                        asdict(self._canonical(row, fetched, snapshot))
                        for _, row in frame.iterrows()
                    ])
                    secondary["validation_report_id"] = report_id
                    validation_observations.extend(secondary.to_dict("records"))
                    combined = pd.concat([primary_symbol, secondary], ignore_index=True, sort=False)
                    symbol_results[symbol] = evaluate_canonical_frame(
                        combined,
                        provider_origins=self.provider_origins,
                        expected_latest_session=expected_day,
                        price_tolerance=self.price_tolerance,
                        volume_tolerance=self.volume_tolerance,
                    )
                except Exception as error:  # Provider boundary: record type, never secret/message.
                    result = evaluate_canonical_frame(
                        primary_symbol,
                        provider_origins=self.provider_origins,
                        expected_latest_session=expected_day,
                        price_tolerance=self.price_tolerance,
                        volume_tolerance=self.volume_tolerance,
                    )
                    symbol_results[symbol] = self._warning(
                        result, f"VALIDATOR_FETCH_FAILED:{type(error).__name__}"
                    )
        finally:
            if validator is not None:
                validator.close()

        report = self._aggregate(
            report_id=report_id,
            validation_key=validation_key,
            sync_run_id=sync_run_id,
            expected=str(expected),
            primary=primary,
            validator_id=validator_id,
            symbol_results=symbol_results,
            raw_snapshot_ids=tuple(raw_snapshot_ids),
        )
        if validation_observations:
            self._append_table(pd.DataFrame(validation_observations), self.VALIDATION_TABLE)
        return self._persist(report)

    def _select_validator(self, primary: str, admitted: tuple[str, ...]) -> str | None:
        primary_origin = self.provider_origins.get(primary)
        if not primary_origin:
            return None
        eligible = [
            provider_id for provider_id in admitted
            if provider_id != primary
            and self.provider_origins.get(provider_id)
            and self.provider_origins[provider_id] != primary_origin
        ]
        for provider_id in self.VALIDATOR_PREFERENCE:
            if provider_id in eligible:
                return provider_id
        return sorted(eligible)[0] if eligible else None

    @staticmethod
    def _latest_primary_frame(frame: pd.DataFrame, primary: str, expected: date) -> pd.DataFrame:
        required = {
            "symbol", "timestamp", "provider", "open", "high", "low", "close", "volume",
            "ingested_at", "raw_snapshot_id", "payload_sha256", "source_reference",
        }
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"canonical frame missing fields: {sorted(missing)}")
        values = frame.copy()
        values["timestamp"] = pd.to_datetime(values.timestamp, utc=True, errors="coerce")
        values = values[values.timestamp.notna()]
        values = values[
            (values.provider.astype(str) == primary)
            & (values.timestamp.dt.date == expected)
        ]
        return values

    def _validation_key(
        self,
        sync_run_id: str,
        primary: str | None,
        expected: str | None,
        admitted: tuple[str, ...],
    ) -> str:
        value = {
            "sync_run_id": sync_run_id,
            "primary": primary,
            "expected": expected,
            "admitted": admitted,
            "origins": self.provider_origins,
            "origin_config_version": provider_origin_config_version(),
            "price_tolerance": self.price_tolerance,
            "volume_tolerance": self.volume_tolerance,
        }
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def _store_fetch(self, fetched: ProviderFetch) -> RawSnapshot:
        digest = hashlib.sha256(fetched.payload).hexdigest()
        identity = json.dumps({
            "retrieved_at": fetched.retrieved_at.isoformat(),
            "request_parameters": fetched.request_parameters,
            "adapter_version": fetched.adapter_version,
            "source_reference": fetched.source_reference,
        }, sort_keys=True).encode()
        snapshot_id = f"{fetched.provider}-{hashlib.sha256(identity).hexdigest()[:24]}"
        snapshot = RawSnapshot(
            snapshot_id, fetched.provider, fetched.retrieved_at, fetched.payload, digest,
            fetched.source_reference, dict(fetched.request_parameters), fetched.adapter_version,
            fetched.trust_tier, fetched.raw_price_unit, fetched.price_semantics,
        )
        Warehouse(self.data_dir).store_raw_snapshot(snapshot)
        return snapshot

    @staticmethod
    def _canonical(row, fetched: ProviderFetch, snapshot: RawSnapshot) -> CanonicalBar:
        decimal = lambda value: None if pd.isna(value) else Decimal(str(value))
        return CanonicalBar(
            datetime.combine(row.trading_date, day_time.min, tzinfo=timezone.utc),
            str(row.symbol), decimal(row.open), decimal(row.high), decimal(row.low),
            decimal(row.close), int(row.volume), decimal(row.get("value")),
            decimal(row.get("adj_close")), fetched.provider, fetched.retrieved_at, (),
            snapshot.snapshot_id, fetched.trust_tier, fetched.raw_price_unit,
            fetched.price_semantics, json.dumps(fetched.request_parameters, sort_keys=True),
            fetched.adapter_version, fetched.source_reference, snapshot.payload_sha256,
        )

    @staticmethod
    def _warning(result: IndependentDataQualityResult, code: str) -> IndependentDataQualityResult:
        if result.validation_status in {
            ReconciliationStatus.QUARANTINED,
            ReconciliationStatus.UNAVAILABLE,
        }:
            return result
        issues = tuple(dict.fromkeys((*result.issues, code)))
        return replace(
            result,
            validation_status=ReconciliationStatus.WARNING,
            overall_quality_score=max(0, result.overall_quality_score - 10),
            issues=issues,
            buy_sell_allowed=True,
        )

    def _aggregate(
        self,
        *,
        report_id: str,
        validation_key: str,
        sync_run_id: str,
        expected: str,
        primary: str,
        validator_id: str | None,
        symbol_results: Mapping[str, IndependentDataQualityResult],
        raw_snapshot_ids: tuple[str, ...],
    ) -> LiveIndependentValidationReport:
        results = tuple(symbol_results.values())
        if not results:
            return self._unavailable(
                validation_key, sync_run_id, primary, expected, "NO_SYMBOL_VALIDATION_RESULTS"
            )
        statuses = {result.validation_status for result in results}
        if ReconciliationStatus.QUARANTINED in statuses:
            status = ReconciliationStatus.QUARANTINED
        elif ReconciliationStatus.UNAVAILABLE in statuses:
            status = ReconciliationStatus.UNAVAILABLE
        elif statuses == {ReconciliationStatus.VERIFIED}:
            status = ReconciliationStatus.VERIFIED
        else:
            status = ReconciliationStatus.WARNING
        sources = tuple(sorted({source for result in results for source in result.source_names}))
        origins = tuple(sorted({origin for result in results for origin in result.independent_origins}))
        issues = tuple(sorted({issue for result in results for issue in result.issues}))
        return LiveIndependentValidationReport(
            report_id=report_id,
            validation_key=validation_key,
            sync_run_id=sync_run_id,
            checked_at=self.now().isoformat(),
            data_as_of=expected,
            primary_provider_id=primary,
            validator_provider_id=validator_id,
            validation_status=status.value,
            overall_quality_score=min(result.overall_quality_score for result in results),
            source_names=sources,
            independent_origins=origins,
            issues=issues,
            symbol_statuses={
                symbol: result.validation_status.value
                for symbol, result in sorted(symbol_results.items())
            },
            symbol_scores={
                symbol: result.overall_quality_score
                for symbol, result in sorted(symbol_results.items())
            },
            raw_snapshot_ids=raw_snapshot_ids,
            buy_sell_allowed=status not in {
                ReconciliationStatus.QUARANTINED,
                ReconciliationStatus.UNAVAILABLE,
            },
            origin_config_version=provider_origin_config_version(),
        )

    def _unavailable(
        self,
        validation_key: str,
        sync_run_id: str,
        primary: str | None,
        expected: str | None,
        issue: str,
    ) -> LiveIndependentValidationReport:
        return LiveIndependentValidationReport(
            report_id=uuid4().hex,
            validation_key=validation_key,
            sync_run_id=sync_run_id,
            checked_at=self.now().isoformat(),
            data_as_of=expected,
            primary_provider_id=primary,
            validator_provider_id=None,
            validation_status=ReconciliationStatus.UNAVAILABLE.value,
            overall_quality_score=0,
            source_names=tuple(filter(None, (primary,))),
            independent_origins=tuple(),
            issues=(issue,),
            symbol_statuses={},
            symbol_scores={},
            raw_snapshot_ids=(),
            buy_sell_allowed=False,
            origin_config_version=provider_origin_config_version(),
        )

    def _persist(self, report: LiveIndependentValidationReport) -> LiveIndependentValidationReport:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_name(f".{self.cache_path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.cache_path)
        row = asdict(report)
        for key in ("source_names", "independent_origins", "issues", "raw_snapshot_ids",
                    "symbol_statuses", "symbol_scores"):
            row[key] = json.dumps(row[key], sort_keys=True)
        self._append_table(pd.DataFrame([row]), self.REPORT_TABLE)
        return report

    def _load_cache(self) -> LiveIndependentValidationReport | None:
        try:
            return LiveIndependentValidationReport.from_dict(
                json.loads(self.cache_path.read_text("utf-8"))
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _append_table(self, incoming: pd.DataFrame, name: str) -> None:
        warehouse = Warehouse(self.data_dir)
        try:
            existing = warehouse.read_table(name)
        except (FileNotFoundError, OSError):
            existing = pd.DataFrame()
        if not existing.empty:
            incoming = pd.concat([existing, incoming], ignore_index=True, sort=False)
        warehouse.write_table(incoming, name)
