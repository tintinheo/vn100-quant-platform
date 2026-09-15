"""Freshness-driven, provider-governed synchronization below the UI.

Operational durations and the weekday-only calendar in this module are
configurable ``[GUESS]`` defaults.  They are not market/trading thresholds.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Callable, Mapping
from uuid import uuid4
from datetime import time as day_time
from decimal import Decimal

import pandas as pd

from .base import DataMode
from .models import CanonicalBar, IndexBar, RawSnapshot, UniverseMembership
from .provider_registry import ProviderRegistry, default_provider_registry
from .quality import DataQualityService, validate_bars
from .storage import Warehouse


class SyncMode(str, Enum):
    LIVE = "LIVE"
    CACHE_ONLY = "CACHE_ONLY"
    DEGRADED_CACHED_DATA = "DEGRADED_CACHED_DATA"
    STALE = "STALE"
    FAILED = "FAILED"


class SyncStatus(str, Enum):
    READY = "READY"
    CACHE_STALE = "CACHE_STALE"
    SYNC_FAILED = "SYNC_FAILED"
    NO_ADMITTED_PROVIDER = "NO_ADMITTED_PROVIDER"


class DQStatus(str, Enum):
    """Whether validation ran, rather than whether synchronization succeeded."""

    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class FreshnessPolicy:
    """Policy for one independently refreshed provider capability."""

    capability: str
    recheck_sessions: int = 1  # [GUESS], configurable vendor revision window
    max_degraded_age_days: int = 3  # [GUESS], actionable remains blocked
    version: str = "1"

    def request_start(self, watermark: date | None, expected: date) -> date:
        if watermark is None:
            return expected
        return watermark - timedelta(days=max(0, self.recheck_sessions - 1))


@dataclass(frozen=True)
class ProviderWatermark:
    provider_id: str
    capability: str
    last_accepted_session: str
    updated_at: str


@dataclass(frozen=True)
class SyncReport:
    run_id: str
    started_at: str
    finished_at: str
    required_capabilities: tuple[str, ...]
    provider_id: str | None
    fresh_before: bool
    remote_fetch_performed: bool
    requested_range: str | None
    canonical_rows_written: int
    dq_status: str
    dq_score: int
    last_accepted_market_date: str | None
    last_successful_sync: str | None
    data_age_days: int | None
    failure_reason: str | None
    mode: str
    actionable: bool
    status: str = SyncStatus.SYNC_FAILED.value
    cache_accepted: bool = False
    degraded_mode: bool = False
    providers: Mapping[str, str] = field(default_factory=dict)
    requested_ranges: Mapping[str, str] = field(default_factory=dict)
    raw_snapshot_ids: tuple[str, ...] = ()
    canonical_changes: Mapping[str, int] = field(default_factory=dict)
    dq_result: Mapping[str, str] = field(default_factory=dict)
    freshness_key: str = ""
    runtime_mode: str = "APP_START"
    # Stable, presentation-facing aliases.  The older names above remain for
    # compatibility with already persisted reports and pipeline consumers.
    data_as_of: str | None = None
    last_sync_at: str | None = None
    rows_written: int = 0
    canonical_revision: str | None = None
    expected_session_status: str = "UNKNOWN"
    lineage_status: str = "UNKNOWN"
    universe_status: str = "UNKNOWN"
    sector_status: str = "NOT_EVALUATED"
    corporate_action_status: str = "UNKNOWN"
    reconciliation_status: str = "UNKNOWN"
    next_action: str | None = None

    @classmethod
    def from_dict(cls, value: dict) -> "SyncReport":
        value = dict(value)
        value["required_capabilities"] = tuple(value["required_capabilities"])
        value["raw_snapshot_ids"] = tuple(value.get("raw_snapshot_ids", ()))
        value.setdefault("status", value.get("failure_reason") or "SYNC_FAILED")
        value.setdefault("dq_score", 100 if value.get("dq_status") == "PASS" else 0)
        value.setdefault("cache_accepted", False)
        value.setdefault("degraded_mode", value.get("mode") in {"STALE", "DEGRADED_CACHED_DATA"})
        value.setdefault("providers", {})
        value.setdefault("requested_ranges", {})
        value.setdefault("canonical_changes", {})
        value.setdefault("dq_result", {})
        value.setdefault("freshness_key", "")
        value.setdefault("runtime_mode", "APP_START")
        value.setdefault("data_as_of", value.get("last_accepted_market_date"))
        value.setdefault("last_sync_at", value.get("last_successful_sync"))
        value.setdefault("rows_written", value.get("canonical_rows_written", 0))
        value.setdefault("canonical_revision", None)
        value.setdefault("expected_session_status", "UNKNOWN")
        value.setdefault("lineage_status", "UNKNOWN")
        value.setdefault("universe_status", "UNKNOWN")
        value.setdefault("sector_status", "NOT_EVALUATED")
        value.setdefault("corporate_action_status", "UNKNOWN")
        value.setdefault("reconciliation_status", "UNKNOWN")
        value.setdefault("next_action", None)
        return cls(**value)


class _SyncLock:
    """Cross-thread/process lock implemented with an atomic lock directory."""

    _thread_lock = threading.Lock()

    def __init__(self, path: Path, timeout: float = 30.0) -> None:
        self.path, self.timeout = path, timeout

    def __enter__(self):
        self._thread_lock.acquire()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.path.mkdir(parents=False)
                (self.path / "owner").write_text(f"{os.getpid()}\n", encoding="ascii")
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    self._thread_lock.release()
                    raise TimeoutError("source synchronization lock timed out")
                time.sleep(0.02)

    def __exit__(self, *_):
        (self.path / "owner").unlink(missing_ok=True)
        self.path.rmdir()
        self._thread_lock.release()


def expected_latest_vietnam_session(today: date, holidays: frozenset[date] = frozenset()) -> date:
    """Return the latest weekday not in configured holidays.

    The holiday set must be supplied from an authoritative calendar in live
    deployments; weekday-only behavior is explicitly a ``[GUESS]`` fallback.
    """
    candidate = today
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate


class SourceSyncOrchestrator:
    REPORT_NAME = "source_sync_result.json"
    WATERMARK_NAME = "provider_watermarks.json"
    # [GUESS] BRD v3.5 routing preference. Admission remains the hard gate;
    # this order never makes a candidate selectable and never fans out a run.
    PROVIDER_PREFERENCE = ("dnse_openapi", "vietstock_datafeed")

    def __init__(self, data_dir: str | Path = "data", *, registry: ProviderRegistry | None = None,
                 today: Callable[[], date] = date.today,
                 now: Callable[[], datetime] | None = None,
                 policies: Mapping[str, FreshnessPolicy] | None = None,
                 expected_session: Callable[[date], date] = expected_latest_vietnam_session,
                 runtime_mode: str = "APP_START") -> None:
        self.data_dir = Path(data_dir)
        self.registry = registry or default_provider_registry()
        self.today, self.now = today, now or (lambda: datetime.now(timezone.utc))
        self.expected_session, self.runtime_mode = expected_session, runtime_mode
        self.policies = dict(policies or {
            "daily_ohlcv": FreshnessPolicy("daily_ohlcv"),
            "current_index_members": FreshnessPolicy("current_index_members", recheck_sessions=1),
            "index_daily_ohlct": FreshnessPolicy("index_daily_ohlct"),
        })
        self.report_path = self.data_dir / self.REPORT_NAME
        self.watermark_path = self.data_dir / self.WATERMARK_NAME
        self.lock_path = self.data_dir / ".source_sync.lock"

    def load_result(self) -> SyncReport | None:
        try:
            return SyncReport.from_dict(json.loads(self.report_path.read_text("utf-8")))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def load_watermarks(self) -> dict[str, ProviderWatermark]:
        try:
            raw = json.loads(self.watermark_path.read_text("utf-8"))
            return {key: ProviderWatermark(**value) for key, value in raw.items()}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {}

    def _write_json(self, path: Path, value: object) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)

    def _persist(self, report: SyncReport) -> SyncReport:
        report = SyncReport(**{
            **asdict(report),
            "data_as_of": report.data_as_of or report.last_accepted_market_date,
            "last_sync_at": report.last_sync_at or report.last_successful_sync,
            "rows_written": report.canonical_rows_written,
        })
        self._write_json(self.report_path, asdict(report))
        Warehouse(self.data_dir).persist_sync_report(report)
        return report

    def _accepted_cache(self, report: SyncReport | None) -> bool:
        return bool(report and report.provider_id and report.last_successful_sync
                    and report.last_accepted_market_date and report.dq_status in {"PASS", "WARN"}
                    and (self.data_dir / "parquet" / "canonical_bars.parquet").exists())

    def _freshness_key(self, required: tuple[str, ...], expected: date,
                       providers: Mapping[str, str], watermarks: Mapping[str, ProviderWatermark]) -> str:
        state = {"required": required, "expected": expected.isoformat(), "providers": dict(providers),
                 "policies": {c: asdict(self.policies[c]) for c in required},
                 "watermarks": {c: asdict(watermarks[c]) if c in watermarks else None for c in required}}
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def _resolve(self, capabilities: tuple[str, ...]) -> tuple[dict[str, str], str | None]:
        selected = {}
        for capability in capabilities:
            admitted = self.registry.admitted_provider_ids(capability)
            if not admitted:
                return selected, "NO_ADMITTED_PROVIDER"
            selected[capability] = next(
                (provider_id for provider_id in self.PROVIDER_PREFERENCE if provider_id in admitted),
                admitted[0],
            )
        return selected, None

    def _make_report(self, started: datetime, *, expected: date, **values) -> SyncReport:
        market_date = values.get("last_accepted_market_date")
        return SyncReport(run_id=uuid4().hex, started_at=started.isoformat(),
                          finished_at=self.now().isoformat(),
                          data_age_days=(self.today() - date.fromisoformat(market_date)).days if market_date else None,
                          runtime_mode=self.runtime_mode, **values)

    def sync(self, required_capabilities: set[str] | None = None, *, force: bool = False) -> SyncReport:
        requested = set(required_capabilities or {"daily_ohlcv"})
        unknown = requested.difference(self.policies)
        if unknown:
            raise ValueError(f"missing freshness policy for: {', '.join(sorted(unknown))}")
        # Daily bars need membership to enumerate symbols, but it remains its own capability/watermark.
        operational = requested | ({"current_index_members"} if "daily_ohlcv" in requested else set())
        required = tuple(sorted(operational))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with _SyncLock(self.lock_path):
            return self._sync_locked(required, force=force)

    def _sync_locked(self, required: tuple[str, ...], *, force: bool) -> SyncReport:
        started, previous = self.now(), self.load_result()
        accepted, expected = self._accepted_cache(previous), self.expected_session(self.today())
        providers, resolution_failure = self._resolve(required)
        watermarks = self.load_watermarks()
        keyed = {c: watermarks.get(f"{providers.get(c, '')}:{c}") for c in required}
        key = self._freshness_key(required, expected, providers, {c: w for c, w in keyed.items() if w})
        all_fresh = bool(providers) and all(w and w.last_accepted_session >= expected.isoformat() for w in keyed.values())
        if not force and all_fresh and previous and previous.freshness_key == key:
            return previous

        if resolution_failure:
            return self._failure_report(started, previous, accepted, expected, providers,
                                        resolution_failure, key, fetched=False)

        ranges, snapshots, changes, dq, dq_scores = {}, [], {}, {}, []
        pending_members: pd.DataFrame | None = None
        pending_memberships: list[UniverseMembership] = []
        pending_bars: list[tuple[str, pd.DataFrame, list[CanonicalBar]]] = []
        pending_index: list[IndexBar] = []
        provider_objects = {}
        fetched = False
        try:
            for capability in required:
                provider_id = providers[capability]
                provider = provider_objects.setdefault(provider_id, self.registry.select(
                    provider_id=provider_id, capability=capability, mode=DataMode.REAL))
                watermark = keyed[capability]
                if not force and watermark and watermark.last_accepted_session >= expected.isoformat():
                    continue
                start = self.policies[capability].request_start(
                    date.fromisoformat(watermark.last_accepted_session) if watermark else None, expected)
                ranges[capability] = f"{start}/{expected}"
                fetched = True
                if capability == "current_index_members":
                    raw = provider.fetch_current_index_members("VN100")
                    snapshot = self._store_fetch(raw)
                    snapshots.append(snapshot.snapshot_id)
                    members = provider.normalize_index_members(raw)
                    pending_memberships = [UniverseMembership(
                        "VN100", symbol, expected, None, provider_id, snapshot.snapshot_id
                    ) for symbol in members]
                    master = pd.DataFrame([{
                        "symbol": record.symbol, "index_code": record.index_code,
                        "provider": record.source,
                        "source_snapshot_id": record.source_snapshot_id,
                    } for record in pending_memberships])
                    pending_members = master
                    changes[capability] = len(master)
                    dq[capability] = "PASS" if members else "FAIL"
                    if not members:
                        raise RuntimeError("DQ failed: empty VN100 membership")
                elif capability == "daily_ohlcv":
                    members = (sorted(pending_members.symbol.astype(str).str.upper().unique())
                               if pending_members is not None else self._members())
                    count, worst = 0, "PASS"
                    for symbol in members:
                        raw = provider.fetch_daily_history(symbol, start, expected)
                        snapshot = self._store_fetch(raw)
                        snapshots.append(snapshot.snapshot_id)
                        frame = provider.normalize_daily_history(raw)
                        issues = validate_bars(frame)
                        if any(issue.severity == "ERROR" for issue in issues):
                            raise RuntimeError(f"DQ failed for {symbol}")
                        worst = "WARN" if issues else worst
                        canonical = [self._canonical(row, raw, snapshot) for _, row in frame.iterrows()]
                        evaluation = DataQualityService().evaluate(canonical,
                            expected_latest_session=expected, admitted_providers={provider_id})
                        dq_scores.append(evaluation.score)
                        if not evaluation.actionable:
                            codes = ", ".join(result.code for result in evaluation.results)
                            raise RuntimeError(f"DQ failed for {symbol}: {codes}")
                        canonical_path = self.data_dir / "parquet" / "canonical_bars.parquet"
                        if canonical_path.exists():
                            existing = pd.read_parquet(canonical_path)
                            keys = set(zip(existing.symbol, existing.timestamp, existing.provider))
                            canonical = [bar for bar in canonical
                                if (bar.symbol, bar.timestamp, bar.provider) not in keys]
                        pending_bars.append((symbol, frame, canonical))
                        count += self._merged_bar_count(frame, symbol)
                    changes[capability], dq[capability] = count, worst
                elif capability == "index_daily_ohlct":
                    # [GUESS] VNINDEX is the configured baseline index until its live
                    # provider literal/schema is verified during admission.
                    raw = provider.fetch_index_daily_history("VNINDEX", start, expected)
                    snapshot = self._store_fetch(raw)
                    snapshots.append(snapshot.snapshot_id)
                    frame = provider.normalize_index_daily_history(raw)
                    required_columns = {"index_code", "trading_date", "open", "high", "low", "close", "turnover"}
                    if frame.empty or not required_columns.issubset(frame.columns):
                        raise RuntimeError("DQ failed: incomplete official index OHLC/turnover")
                    if max(frame.trading_date) < expected:
                        raise RuntimeError("DQ failed: stale official index series")
                    canonical = [self._canonical_index(row, raw, snapshot) for _, row in frame.iterrows()]
                    path = self.data_dir / "parquet" / "index_bars.parquet"
                    if path.exists():
                        existing = pd.read_parquet(path)
                        keys = set(zip(existing.index_code, existing.timestamp, existing.provider))
                        canonical = [bar for bar in canonical
                                     if (bar.index_code, bar.timestamp, bar.provider) not in keys]
                    pending_index.extend(canonical)
                    changes[capability], dq[capability] = len(canonical), "PASS"
                now = self.now().isoformat()
                watermarks[f"{provider_id}:{capability}"] = ProviderWatermark(
                    provider_id, capability, expected.isoformat(), now)

            # Nothing canonical is exposed until every capability has fetched,
            # normalized, and passed DQ.  Individual file replacement is atomic;
            # the synchronization lock prevents application readers observing the
            # accepted revision while this publication block is in progress.
            warehouse = Warehouse(self.data_dir)
            canonical_revision = uuid4().hex if any(bars for _, _, bars in pending_bars) else (
                previous.canonical_revision if previous else None)
            if pending_members is not None:
                warehouse.write_records("universe_current", pending_memberships)
                warehouse.write_table(pending_members, "security_master")
            for _, _, canonical in pending_bars:
                if canonical:
                    warehouse.append_canonical_bars(canonical, canonical_revision=canonical_revision)
            if pending_index:
                warehouse.append_index_bars(pending_index)
            self._write_json(self.watermark_path, {k: asdict(v) for k, v in watermarks.items()})
            now = self.now().isoformat()
            report = self._make_report(started, expected=expected, required_capabilities=required,
                provider_id=providers.get("daily_ohlcv") or next(iter(providers.values())), providers=providers,
                fresh_before=all_fresh, remote_fetch_performed=fetched,
                requested_range=ranges.get("daily_ohlcv"), requested_ranges=ranges,
                raw_snapshot_ids=tuple(snapshots), canonical_rows_written=sum(changes.values()),
                canonical_changes=changes, dq_status="WARN" if "WARN" in dq.values() else "PASS",
                dq_score=min(dq_scores, default=100),
                dq_result=dq, last_accepted_market_date=expected.isoformat(), last_successful_sync=now,
                failure_reason=None, mode=SyncMode.LIVE.value if fetched else SyncMode.CACHE_ONLY.value,
                actionable=True, status=SyncStatus.READY.value, cache_accepted=True,
                degraded_mode=False, freshness_key=key,
                canonical_revision=canonical_revision,
                expected_session_status="COMPLETE", lineage_status="COMPLETE",
                universe_status="CURRENT_COMPLETE", corporate_action_status="CLEAR",
                reconciliation_status="DISAGREEMENT" if "WARN" in dq.values() else "CLEAR")
            # The new watermarks define a new deterministic state key.
            new_keyed = {c: watermarks[f"{providers[c]}:{c}"] for c in required}
            report = SyncReport(**{**asdict(report), "freshness_key": self._freshness_key(required, expected, providers, new_keyed)})
            return self._persist(report)
        except Exception as error:
            return self._failure_report(started, previous, accepted, expected, providers,
                f"{type(error).__name__}: {error}", key, fetched=fetched, ranges=ranges, snapshots=snapshots)
        finally:
            for provider in provider_objects.values():
                provider.close()

    def _store_fetch(self, fetched) -> RawSnapshot:
        digest = hashlib.sha256(fetched.payload).hexdigest()
        identity = json.dumps({"retrieved_at": fetched.retrieved_at.isoformat(),
            "request_parameters": fetched.request_parameters, "adapter_version": fetched.adapter_version,
            "source_reference": fetched.source_reference}, sort_keys=True).encode()
        snapshot_id = f"{fetched.provider}-{hashlib.sha256(identity).hexdigest()[:24]}"
        snapshot = RawSnapshot(snapshot_id, fetched.provider,
            fetched.retrieved_at, fetched.payload, digest, fetched.source_reference,
            dict(fetched.request_parameters), fetched.adapter_version, fetched.trust_tier,
            fetched.raw_price_unit, fetched.price_semantics)
        Warehouse(self.data_dir).store_raw_snapshot(snapshot)
        return snapshot

    @staticmethod
    def _canonical(row, fetched, snapshot) -> CanonicalBar:
        decimal = lambda value: None if pd.isna(value) else Decimal(str(value))
        return CanonicalBar(
            datetime.combine(row.trading_date, day_time.min, tzinfo=timezone.utc),
            str(row.symbol), decimal(row.open), decimal(row.high), decimal(row.low),
            decimal(row.close), int(row.volume), decimal(row.get("value")),
            decimal(row.get("adj_close")), fetched.provider, fetched.retrieved_at, (),
            snapshot.snapshot_id, fetched.trust_tier, fetched.raw_price_unit,
            fetched.price_semantics, json.dumps(fetched.request_parameters, sort_keys=True),
            fetched.adapter_version, fetched.source_reference, snapshot.payload_sha256)

    @staticmethod
    def _canonical_index(row, fetched, snapshot) -> IndexBar:
        decimal = lambda value: None if pd.isna(value) else Decimal(str(value))
        return IndexBar(
            datetime.combine(row.trading_date, day_time.min, tzinfo=timezone.utc),
            str(row.index_code).upper(), decimal(row.open), decimal(row.high),
            decimal(row.low), decimal(row.close), decimal(row.turnover),
            fetched.provider, fetched.retrieved_at, (), snapshot.snapshot_id,
            fetched.trust_tier, fetched.raw_price_unit, fetched.price_semantics,
            json.dumps(fetched.request_parameters, sort_keys=True), fetched.adapter_version,
            fetched.source_reference, snapshot.payload_sha256)

    def _members(self) -> list[str]:
        table = self.data_dir / "parquet" / "security_master.parquet"
        if not table.exists():
            raise RuntimeError("current_index_members cache is unavailable")
        return sorted(pd.read_parquet(table).symbol.astype(str).str.upper().unique())

    def _merged_bar_count(self, incoming: pd.DataFrame, symbol: str) -> int:
        """Calculate new canonical observations without publishing compatibility bars."""
        path = self.data_dir / "parquet" / "canonical_bars.parquet"
        if not path.exists():
            return len(incoming)
        existing = pd.read_parquet(path)
        provider = str(incoming.provider.iloc[0]) if not incoming.empty else ""
        keys = set(zip(existing.symbol.astype(str), pd.to_datetime(existing.timestamp).dt.date,
                       existing.provider.astype(str)))
        return sum((str(row.symbol), row.trading_date, provider) not in keys
                   for row in incoming.itertuples())

    def _failure_report(self, started, previous, accepted, expected, providers, reason, key,
                        *, fetched, ranges=None, snapshots=None):
        if accepted:
            mode = (SyncMode.STALE.value if reason == "NO_ADMITTED_PROVIDER"
                    else SyncMode.DEGRADED_CACHED_DATA.value)
            status = SyncStatus.CACHE_STALE.value
            provider_id, market_date = previous.provider_id, previous.last_accepted_market_date
            dq_status, last_sync = previous.dq_status, previous.last_successful_sync
        else:
            mode, status = SyncMode.FAILED.value, (SyncStatus.NO_ADMITTED_PROVIDER.value
                if reason.startswith("NO_ADMITTED_PROVIDER") else SyncStatus.SYNC_FAILED.value)
            provider_id, market_date, last_sync = None, None, None
            # A transport/configuration failure is not a failed DQ evaluation.
            # FAIL is reserved for a blocking result produced by validation.
            dq_status = (DQStatus.FAIL.value if "DQ failed" in reason
                         else DQStatus.NOT_RUN.value)
        if reason.startswith("NO_ADMITTED_PROVIDER"):
            next_action = "Configure and complete Source Admission for DNSE."
        elif "credential" in reason.lower():
            next_action = "Configure DNSE market-data credentials, then retry synchronization."
        elif dq_status == DQStatus.FAIL.value:
            next_action = "Review the blocking data-quality findings before retrying synchronization."
        else:
            next_action = "Retry synchronization after resolving the provider failure."
        return self._persist(self._make_report(started, expected=expected,
            required_capabilities=tuple(providers) or ("daily_ohlcv",), provider_id=provider_id,
            providers=providers, fresh_before=False, remote_fetch_performed=fetched,
            requested_range=(ranges or {}).get("daily_ohlcv"), requested_ranges=ranges or {},
            raw_snapshot_ids=tuple(snapshots or ()), canonical_rows_written=0, canonical_changes={},
            dq_status=dq_status, dq_score=(previous.dq_score if accepted else 0), dq_result={}, last_accepted_market_date=market_date,
            last_successful_sync=last_sync, failure_reason=reason, mode=mode, actionable=False,
            status=status, cache_accepted=accepted, degraded_mode=accepted, freshness_key=key,
            next_action=next_action))
