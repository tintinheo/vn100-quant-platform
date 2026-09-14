"""Governed, persisted source synchronization below UI and analytics layers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .base import DataMode
from .provider_registry import ProviderRegistry, default_provider_registry
from .quality import validate_bars
from .storage import Warehouse


class SyncMode(str, Enum):
    LIVE = "LIVE"
    CACHE_ONLY = "CACHE_ONLY"
    DEGRADED_CACHED_DATA = "DEGRADED_CACHED_DATA"
    STALE = "STALE"
    FAILED = "FAILED"


class SyncStatus(str, Enum):
    """Outcome consumed by every actionable application entry point."""

    READY = "READY"
    CACHE_STALE = "CACHE_STALE"
    SYNC_FAILED = "SYNC_FAILED"
    NO_ADMITTED_PROVIDER = "NO_ADMITTED_PROVIDER"


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
    last_accepted_market_date: str | None
    last_successful_sync: str | None
    data_age_days: int | None
    failure_reason: str | None
    mode: str
    actionable: bool
    status: str = SyncStatus.SYNC_FAILED.value
    cache_accepted: bool = False
    degraded_mode: bool = False

    @classmethod
    def from_dict(cls, value: dict) -> "SyncReport":
        value = dict(value)
        value["required_capabilities"] = tuple(value["required_capabilities"])
        # Results written before the synchronization-result contract was added
        # may prove cache lineage, but are never silently made actionable.
        value.setdefault("status", value.get("failure_reason") or "SYNC_FAILED")
        value.setdefault("cache_accepted", False)
        value.setdefault("degraded_mode", value.get("mode") in {"STALE", "DEGRADED_CACHED_DATA"})
        return cls(**value)


class SourceSyncOrchestrator:
    """Refresh canonical bars from an admitted provider, or fail closed.

    A cache is accepted only when a previous successful governed sync report
    identifies its provider, the last market date, and non-failing DQ status.
    Merely finding Parquet or publish artifacts never makes them trusted input.
    """

    REPORT_NAME = "source_sync_result.json"

    def __init__(
        self,
        data_dir: str | Path = "data",
        *,
        registry: ProviderRegistry | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.registry = registry or default_provider_registry()
        self.today = today
        self.report_path = self.data_dir / self.REPORT_NAME

    def load_result(self) -> SyncReport | None:
        if not self.report_path.exists():
            return None
        try:
            return SyncReport.from_dict(json.loads(self.report_path.read_text("utf-8")))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _accepted_cache(self, report: SyncReport | None) -> bool:
        return bool(
            report
            and report.provider_id
            and report.last_successful_sync
            and report.last_accepted_market_date
            and report.dq_status in {"PASS", "WARN"}
            and any((self.data_dir / "parquet" / "bars").glob("*.parquet"))
        )

    def _persist(self, report: SyncReport) -> SyncReport:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.report_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        temporary.replace(self.report_path)
        return report

    def _report(self, started: datetime, previous: SyncReport | None, **values) -> SyncReport:
        finished = datetime.now(timezone.utc)
        market_date = values.get("last_accepted_market_date")
        age = (self.today() - date.fromisoformat(market_date)).days if market_date else None
        return SyncReport(
            run_id=uuid4().hex, started_at=started.isoformat(), finished_at=finished.isoformat(),
            required_capabilities=("daily_ohlcv",), data_age_days=age,
            last_successful_sync=values.pop("last_successful_sync", None),
            **values,
        )

    def sync(self, required_capabilities: set[str] | None = None, *, force: bool = False) -> SyncReport:
        required = required_capabilities or {"daily_ohlcv"}
        if required != {"daily_ohlcv"}:
            raise ValueError("only the daily_ohlcv synchronization contract is implemented")
        started = datetime.now(timezone.utc)
        previous = self.load_result()
        accepted = self._accepted_cache(previous)
        expected = self.today()
        fresh = bool(accepted and previous.last_accepted_market_date == expected.isoformat())
        if fresh and not force:
            return previous

        admitted = self.registry.admitted_provider_ids("daily_ohlcv")
        if not admitted:
            if accepted:
                return self._persist(self._report(
                    started, previous, provider_id=previous.provider_id, fresh_before=False,
                    remote_fetch_performed=False, requested_range=None, canonical_rows_written=0,
                    dq_status=previous.dq_status, last_accepted_market_date=previous.last_accepted_market_date,
                    last_successful_sync=previous.last_successful_sync, failure_reason="NO_ADMITTED_PROVIDER",
                    mode=SyncMode.STALE.value, actionable=False,
                    status=SyncStatus.CACHE_STALE.value, cache_accepted=True, degraded_mode=True,
                ))
            return self._persist(self._report(
                started, previous, provider_id=None, fresh_before=False,
                remote_fetch_performed=False, requested_range=None, canonical_rows_written=0,
                dq_status="FAIL", last_accepted_market_date=None,
                failure_reason="NO_ADMITTED_PROVIDER", mode=SyncMode.FAILED.value, actionable=False,
                status=SyncStatus.NO_ADMITTED_PROVIDER.value, cache_accepted=False, degraded_mode=False,
            ))

        provider_id = admitted[0]
        provider = self.registry.select(provider_id=provider_id, capability="daily_ohlcv", mode=DataMode.REAL)
        start_date = (date.fromisoformat(previous.last_accepted_market_date)
                      if accepted else expected)
        try:
            wh = Warehouse(self.data_dir)
            members = provider.current_index_members("VN100")
            rows = 0
            worst = "PASS"
            for symbol in members:
                frame = provider.daily_history(symbol, start_date, expected)
                issues = validate_bars(frame)
                if any(issue.severity == "ERROR" for issue in issues):
                    worst = "FAIL"
                    raise RuntimeError(f"DQ failed for {symbol}")
                if issues:
                    worst = "WARN"
                if not frame.empty:
                    wh.write_bars(frame, symbol)
                    rows += len(frame)
            wh.write_table(pd.DataFrame({"symbol": members, "index_code": "VN100", "provider": provider_id}), "security_master")
            now = datetime.now(timezone.utc).isoformat()
            return self._persist(self._report(
                started, previous, provider_id=provider_id, fresh_before=False,
                remote_fetch_performed=True, requested_range=f"{start_date}/{expected}",
                canonical_rows_written=rows, dq_status=worst,
                last_accepted_market_date=expected.isoformat(), last_successful_sync=now,
                failure_reason=None, mode=SyncMode.LIVE.value, actionable=worst != "FAIL",
                status=SyncStatus.READY.value, cache_accepted=True, degraded_mode=False,
            ))
        except Exception as error:
            if accepted:
                return self._persist(self._report(
                    started, previous, provider_id=previous.provider_id, fresh_before=False,
                    remote_fetch_performed=True, requested_range=f"{start_date}/{expected}",
                    canonical_rows_written=0, dq_status=previous.dq_status,
                    last_accepted_market_date=previous.last_accepted_market_date,
                    last_successful_sync=previous.last_successful_sync,
                    failure_reason=f"{type(error).__name__}: {error}",
                    mode=SyncMode.DEGRADED_CACHED_DATA.value, actionable=False,
                    status=SyncStatus.CACHE_STALE.value, cache_accepted=True, degraded_mode=True,
                ))
            return self._persist(self._report(
                started, previous, provider_id=provider_id, fresh_before=False,
                remote_fetch_performed=True, requested_range=f"{start_date}/{expected}",
                canonical_rows_written=0, dq_status="FAIL", last_accepted_market_date=None,
                failure_reason=f"{type(error).__name__}: {error}", mode=SyncMode.FAILED.value,
                actionable=False, status=SyncStatus.SYNC_FAILED.value,
                cache_accepted=False, degraded_mode=False,
            ))
        finally:
            provider.close()
