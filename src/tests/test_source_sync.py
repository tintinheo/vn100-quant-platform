from __future__ import annotations

from datetime import date, datetime, timezone
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from vnquant.data.base import DataMode, MarketDataProvider, ProviderFetch
from vnquant.data.provider_registry import (
    AdmissionEvidence,
    ProviderRegistry,
    ProviderState,
    ValidationResult,
)
from vnquant.data.source_sync import SourceSyncOrchestrator, SyncMode, SyncStatus
from vnquant.jobs.pipeline import run as run_pipeline


class CountingProvider(MarketDataProvider):
    provider_id = "documented_feed"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def _fetch(self, payload, parameters, source):
        if self.fail:
            raise RuntimeError("temporary provider outage")
        return ProviderFetch(self.provider_id, json.dumps(payload).encode(),
            datetime.now(timezone.utc), parameters, "test-adapter-1", source,
            "admitted_test", "VND", "raw")

    def fetch_current_index_members(self, index_code="VN100"):
        return self._fetch(["AAA"], {"index_code": index_code}, "test://members")

    def normalize_index_members(self, fetched):
        return json.loads(fetched.payload)

    def fetch_daily_history(self, symbol, start, end):
        self.calls += 1
        return self._fetch([{"symbol": symbol, "trading_date": end.isoformat(), "open": 10.0,
            "high": 11.0, "low": 9.0, "close": 10.5, "volume": 100,
            "value": 1050.0}], {"symbol": symbol, "start": start.isoformat(),
            "end": end.isoformat()}, "test://bars")

    def normalize_daily_history(self, fetched):
        rows = json.loads(fetched.payload)
        for row in rows:
            row["trading_date"] = date.fromisoformat(row["trading_date"])
            row["provider"] = self.provider_id
        return pd.DataFrame(rows)


def registry_for(provider):
    registry = ProviderRegistry()
    evidence = AdmissionEvidence(
        access_basis="test agreement", licence_reference="TEST-LICENCE",
        capability_definitions={
            "daily_ohlcv": "test daily bars",
            "current_index_members": "test current members",
        },
        schema_and_units="test schema; VND/shares",
        timezone_date_semantics="Asia/Ho_Chi_Minh exchange date",
        raw_adjusted_policy="raw", revision_behavior="immutable test snapshots",
        quotas="test quota", lineage_method="test payload hash", owner="test owner",
        reviewed_at=date(2026, 9, 14), next_review_at=date(2027, 9, 14),
        validation_results=(
            ValidationResult("doctor", True, "test-doctor", date(2026, 9, 14)),
            ValidationResult("cross_validation", True, "test-cross", date(2026, 9, 14)),
        ),
    )
    registry.register(provider, evidence=evidence)
    registry.transition(provider.provider_id, ProviderState.DOCTOR_PASSED)
    registry.transition(provider.provider_id, ProviderState.CROSS_VALIDATED)
    registry.transition(provider.provider_id, ProviderState.ADMITTED)
    return registry


def test_app_run_invokes_source_sync_check():
    source = open("app.py", encoding="utf-8").read()
    assert "sync=run_startup_sync(force=force_refresh)" in source
    assert 'st.sidebar.button("Refresh now"' in source
    assert "st.error(sync.status)" in source
    for field in ("provider_id", "data_age_days", "last_successful_sync",
                  "dq_status", "degraded_mode", "cache_accepted"):
        assert f"sync.{field}" in source


def test_fresh_cache_avoids_duplicate_remote_fetch(tmp_path):
    provider = CountingProvider()
    sync = SourceSyncOrchestrator(tmp_path, registry=registry_for(provider),
                                  today=lambda: date(2026, 9, 13))
    first = sync.sync()
    second = sync.sync()
    assert first.remote_fetch_performed
    assert second.run_id == first.run_id
    assert provider.calls == 1
    reports = pd.read_parquet(tmp_path / "parquet" / "sync_reports.parquet")
    assert reports.run_id.tolist() == [first.run_id]


def test_streamlit_rerun_does_not_refetch_same_state(tmp_path):
    provider = CountingProvider()
    registry = registry_for(provider)
    SourceSyncOrchestrator(tmp_path, registry=registry,
                           today=lambda: date(2026, 9, 13)).sync()
    SourceSyncOrchestrator(tmp_path, registry=registry,
                           today=lambda: date(2026, 9, 13)).sync()
    assert provider.calls == 1


def test_stale_data_triggers_incremental_fetch(tmp_path):
    provider = CountingProvider()
    day = [date(2026, 9, 14)]
    sync = SourceSyncOrchestrator(tmp_path, registry=registry_for(provider), today=lambda: day[0])
    sync.sync()
    day[0] = date(2026, 9, 15)
    report = sync.sync()
    assert report.requested_range == "2026-09-14/2026-09-15"
    assert provider.calls == 2


def test_no_admitted_provider_fails_closed(tmp_path):
    report = SourceSyncOrchestrator(tmp_path, registry=ProviderRegistry()).sync()
    assert report.failure_reason == "NO_ADMITTED_PROVIDER"
    assert report.status == SyncStatus.NO_ADMITTED_PROVIDER.value
    assert not report.actionable


def test_recommendation_generation_blocked_without_accepted_sync(tmp_path):
    result = run_pipeline(str(tmp_path), str(tmp_path / "publish"))
    assert result["status"] == "NO_ADMITTED_PROVIDER"
    assert result["candidate_count"] == 0
    assert not (tmp_path / "publish" / "candidates.csv").exists()
    published = pd.read_json(tmp_path / "publish" / "market.json", typ="series")
    assert published["status"] == "NO_ADMITTED_PROVIDER"


def test_direct_pipeline_removes_stale_analytics_artifacts(tmp_path):
    publish = tmp_path / "publish"
    publish.mkdir()
    for name in ("candidates.csv", "sector_scores.csv"):
        (publish / name).write_text("stale,data\n", encoding="utf-8")

    result = run_pipeline(str(tmp_path), str(publish))

    assert result["status"] == "NO_ADMITTED_PROVIDER"
    assert not (publish / "candidates.csv").exists()
    assert not (publish / "sector_scores.csv").exists()


def test_provider_failure_never_falls_back_to_undocumented_source(tmp_path):
    successful = CountingProvider()
    SourceSyncOrchestrator(tmp_path, registry=registry_for(successful),
                           today=lambda: date(2026, 9, 14)).sync()
    failing = CountingProvider(fail=True)
    report = SourceSyncOrchestrator(tmp_path, registry=registry_for(failing),
                                    today=lambda: date(2026, 9, 15)).sync()
    assert report.mode == SyncMode.DEGRADED_CACHED_DATA.value
    assert report.provider_id == "documented_feed"
    assert report.data_age_days == 1
    assert not report.actionable
    assert "outage" in report.failure_reason


def test_accepted_cache_exposes_stale_lineage_without_provider(tmp_path):
    provider = CountingProvider()
    SourceSyncOrchestrator(tmp_path, registry=registry_for(provider),
                           today=lambda: date(2026, 9, 11)).sync()
    report = SourceSyncOrchestrator(tmp_path, registry=ProviderRegistry(),
                                    today=lambda: date(2026, 9, 14)).sync()
    assert report.mode == SyncMode.STALE.value
    assert report.provider_id == provider.provider_id
    assert report.data_age_days == 3
    assert report.last_successful_sync
    assert report.dq_status == "PASS"
    assert report.failure_reason == "NO_ADMITTED_PROVIDER"
    assert report.cache_accepted
    assert report.degraded_mode


def test_unusable_cache_does_not_bypass_provider_gate(tmp_path):
    bars = tmp_path / "parquet" / "bars"
    bars.mkdir(parents=True)
    (bars / "UNTRUSTED.parquet").write_bytes(b"not governed data")

    report = SourceSyncOrchestrator(tmp_path, registry=ProviderRegistry()).sync()

    assert report.status == "NO_ADMITTED_PROVIDER"
    assert not report.cache_accepted
    assert report.provider_id is None


def test_manual_file_is_not_required_for_normal_startup(tmp_path):
    report = SourceSyncOrchestrator(tmp_path, registry=ProviderRegistry()).sync()
    assert report.mode == SyncMode.FAILED.value
    assert not list(tmp_path.glob("*.csv"))


def test_force_refresh_rechecks_provider_and_remains_idempotent(tmp_path):
    provider = CountingProvider()
    sync = SourceSyncOrchestrator(tmp_path, registry=registry_for(provider),
                                  today=lambda: date(2026, 9, 14))
    first = sync.sync()
    forced = sync.sync(force=True)
    assert provider.calls == 2
    assert forced.remote_fetch_performed
    assert forced.canonical_changes["daily_ohlcv"] == 0
    assert forced.raw_snapshot_ids
    assert forced.run_id != first.run_id


def test_concurrent_reruns_share_cross_instance_lock(tmp_path):
    provider = CountingProvider()
    registry = registry_for(provider)

    def run_once():
        return SourceSyncOrchestrator(tmp_path, registry=registry,
            today=lambda: date(2026, 9, 14)).sync()

    with ThreadPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(lambda _: run_once(), range(4)))
    assert provider.calls == 1
    assert len({report.run_id for report in reports}) == 1


def test_expected_session_skips_weekend_and_watermarks_each_capability(tmp_path):
    provider = CountingProvider()
    sync = SourceSyncOrchestrator(tmp_path, registry=registry_for(provider),
                                  today=lambda: date(2026, 9, 13))
    report = sync.sync()
    watermarks = sync.load_watermarks()
    assert report.last_accepted_market_date == "2026-09-11"
    assert set(report.providers) == {"daily_ohlcv", "current_index_members"}
    assert {watermark.capability for watermark in watermarks.values()} == set(report.providers)
    assert report.dq_result == {"current_index_members": "PASS", "daily_ohlcv": "PASS"}
