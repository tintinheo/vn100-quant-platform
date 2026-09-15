"""Offline acceptance tests for BRD §28.7 and SRD §§25.2/26.8.

Every provider boundary uses an in-memory SDK/transport or a checked-in fixture.
No test in this module performs network I/O.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
from pathlib import Path
from threading import Lock

import pandas as pd
import pytest

from vnquant.data.provider_registry import (
    AdmissionEvidence,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderState,
    ValidationResult,
)
from vnquant.data.providers import (
    CafeFReferenceProvider,
    DNSEProvider,
    VietstockDataFeedContract,
    VietstockDataFeedProvider,
)
from vnquant.data.source_sync import SourceSyncOrchestrator, SyncMode, SyncStatus


FIXTURES = Path(__file__).with_name("fixtures")
NOW = datetime(2026, 9, 14, 10, 30, tzinfo=timezone.utc)


class FakeDNSESDK:
    """Deterministic fake of only the documented, read-only DNSE SDK surface."""

    def __init__(self) -> None:
        self.instrument_calls = 0
        self.ohlc_calls: list[dict] = []
        self.fail = False
        self._lock = Lock()

    def get_instruments(self, **kwargs):
        with self._lock:
            self.instrument_calls += 1
        if self.fail:
            raise RuntimeError("fake DNSE outage")
        return {"data": [{"symbol": "AAA"}]}

    def get_ohlc(self, **kwargs):
        with self._lock:
            self.ohlc_calls.append(kwargs)
        if self.fail:
            raise RuntimeError("fake DNSE outage")
        query = kwargs["query"]
        return {"data": [{
            "time": query["to"], "open": 10, "high": 11, "low": 9,
            "close": 10.5, "volume": 100,
        }]}


def complete_evidence(provider) -> AdmissionEvidence:
    return AdmissionEvidence(
        access_basis="offline acceptance fixture",
        licence_reference="TEST-ONLY",
        capability_definitions={capability: f"fixture {capability}"
                                for capability in provider.capabilities},
        schema_and_units="fixture schema; VND and shares",
        timezone_date_semantics="deterministic UTC fixture mapped to exchange date",
        raw_adjusted_policy="raw",
        revision_behavior="immutable fixture response",
        quotas="local fixture only",
        history_depth="fixture range verified", universe_semantics="fixture membership verified",
        lineage_method="SHA-256 raw snapshot",
        validation_results=(
            ValidationResult("doctor", True, "fixture-doctor", date(2026, 9, 14)),
            ValidationResult("cross_validation", True, "fixture-cross", date(2026, 9, 14)),
        ),
        owner="test suite",
        reviewed_at=date(2026, 9, 14),
        next_review_at=date(2027, 9, 14),
    )


def admitted_dnse(client: FakeDNSESDK) -> tuple[ProviderRegistry, DNSEProvider]:
    provider = DNSEProvider(client=client, now=lambda: NOW)
    # Live units/semantics remain unverified; these values describe only this fixture.
    provider.raw_price_unit = "VND"
    provider.price_semantics = "raw"
    registry = ProviderRegistry()
    registry.register(provider, evidence=complete_evidence(provider))
    for state in (ProviderState.DOCTOR_PASSED, ProviderState.CROSS_VALIDATED,
                  ProviderState.ADMITTED):
        registry.transition(provider.provider_id, state)
    return registry, provider


def orchestrator(tmp_path, client, day=lambda: date(2026, 9, 14)):
    registry, _ = admitted_dnse(client)
    return SourceSyncOrchestrator(
        tmp_path, registry=registry, today=day, now=lambda: NOW,
        expected_session=lambda today: today,
    )


def test_admission_transitions_require_ordered_evidence_and_contract_fixture():
    client = FakeDNSESDK()
    registry, dnse = admitted_dnse(client)
    assert registry.registration(dnse.provider_id).state is ProviderState.ADMITTED

    contract = VietstockDataFeedContract(**json.loads(
        (FIXTURES / "vietstock_contract.json").read_text(encoding="utf-8")))
    vietstock = VietstockDataFeedProvider(
        contract, transport=lambda **_: [{"ticker": "AAA"}], now=lambda: NOW)
    registry.register(vietstock, evidence=complete_evidence(vietstock))
    with pytest.raises(ProviderNotAllowed, match="CANDIDATE -> ADMITTED"):
        registry.transition(vietstock.provider_id, ProviderState.ADMITTED)
    for state in (ProviderState.DOCTOR_PASSED, ProviderState.CROSS_VALIDATED,
                  ProviderState.ADMITTED):
        registry.transition(vietstock.provider_id, state)
    assert registry.registration(vietstock.provider_id).state is ProviderState.ADMITTED


def test_no_admitted_provider_blocks_real_mode(tmp_path):
    report = SourceSyncOrchestrator(
        tmp_path, registry=ProviderRegistry(), today=lambda: date(2026, 9, 14),
        now=lambda: NOW, expected_session=lambda today: today).sync()
    assert report.status == SyncStatus.NO_ADMITTED_PROVIDER.value
    assert report.mode == SyncMode.FAILED.value
    assert not report.actionable
    assert not report.cache_accepted


@pytest.mark.parametrize("force", [False, True])
def test_no_synthetic_or_undocumented_fallback(tmp_path, force):
    client = FakeDNSESDK()
    client.fail = True
    registry, _ = admitted_dnse(client)
    calls = {"cafef": 0, "vietstock": 0}
    html = (FIXTURES / "cafef_history.html").read_text(encoding="utf-8")
    cafef = CafeFReferenceProvider(
        allow_reference_source=True,
        page_fetcher=lambda _: calls.__setitem__("cafef", calls["cafef"] + 1) or html,
        now=lambda: NOW,
    )
    contract = VietstockDataFeedContract(**json.loads(
        (FIXTURES / "vietstock_contract.json").read_text(encoding="utf-8")))
    vietstock = VietstockDataFeedProvider(
        contract,
        transport=lambda **_: calls.__setitem__("vietstock", calls["vietstock"] + 1),
        now=lambda: NOW,
    )
    registry.register(cafef, state=ProviderState.RESEARCH_ONLY,
                      evidence=complete_evidence(cafef))
    registry.register(vietstock, evidence=complete_evidence(vietstock))

    report = SourceSyncOrchestrator(
        tmp_path, registry=registry, today=lambda: date(2026, 9, 14),
        now=lambda: NOW, expected_session=lambda today: today).sync(force=force)

    assert report.status == SyncStatus.SYNC_FAILED.value
    assert report.provider_id is None
    assert calls == {"cafef": 0, "vietstock": 0}


def test_local_cafef_html_fixture_is_explicit_reference_only():
    html = (FIXTURES / "cafef_history.html").read_text(encoding="utf-8")
    provider = CafeFReferenceProvider(
        allow_reference_source=True, page_fetcher=lambda _: html, now=lambda: NOW)
    fetched = provider.fetch_daily_history("AAA", date(2026, 9, 14), date(2026, 9, 14))
    frame = provider.normalize_daily_history(fetched)
    assert frame.loc[0, "close"] == 10_500
    assert fetched.retrieved_at == NOW
    assert provider.primary_eligible is False


def test_raw_response_snapshotted_before_normalization_and_canonical_commit(tmp_path):
    client = FakeDNSESDK()
    sync = orchestrator(tmp_path, client)
    provider = sync.registry.registration("dnse_openapi").provider
    original_members = provider.normalize_index_members
    original_bars = provider.normalize_daily_history

    def normalize_members(fetched):
        assert list((tmp_path / "raw" / provider.provider_id).glob("*.bin"))
        return original_members(fetched)

    def normalize_bars(fetched):
        raw = list((tmp_path / "raw" / provider.provider_id).glob("*.bin"))
        assert any(path.read_bytes() == fetched.payload for path in raw)
        assert not (tmp_path / "parquet" / "canonical_bars.parquet").exists()
        return original_bars(fetched)

    provider.normalize_index_members = normalize_members
    provider.normalize_daily_history = normalize_bars
    report = sync.sync()
    assert report.status == SyncStatus.READY.value


def test_sync_lineage_records_provider_and_fetch_time(tmp_path):
    report = orchestrator(tmp_path, FakeDNSESDK()).sync()
    canonical = pd.read_parquet(tmp_path / "parquet" / "canonical_bars.parquet").iloc[0]
    metadata_files = list((tmp_path / "raw" / "dnse_openapi").glob("*.bin.json"))
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_files]
    bar_metadata = next(item for item in metadata
                        if item["snapshot_id"] == canonical.raw_snapshot_id)
    assert report.provider_id == canonical.provider == "dnse_openapi"
    assert canonical.ingested_at == NOW
    assert bar_metadata["ingested_at"] == NOW.isoformat()
    assert bar_metadata["payload_sha256"] == canonical.payload_sha256


def test_fresh_cache_avoids_duplicate_remote_fetch(tmp_path):
    client = FakeDNSESDK()
    sync = orchestrator(tmp_path, client)
    first, second = sync.sync(), sync.sync()
    assert second.run_id == first.run_id
    assert client.instrument_calls == 1
    assert len(client.ohlc_calls) == 1


def test_stale_data_triggers_incremental_fetch(tmp_path):
    client, day = FakeDNSESDK(), [date(2026, 9, 14)]
    sync = orchestrator(tmp_path, client, day=lambda: day[0])
    sync.sync()
    day[0] = date(2026, 9, 15)
    report = sync.sync()
    assert report.requested_range == "2026-09-14/2026-09-15"
    assert client.ohlc_calls[-1]["query"]["from"] == int(
        pd.Timestamp("2026-09-14", tz="UTC").timestamp())


def test_sync_is_idempotent_for_same_freshness_state(tmp_path):
    client = FakeDNSESDK()
    first = orchestrator(tmp_path, client).sync()
    second = orchestrator(tmp_path, client).sync()
    bars = pd.read_parquet(tmp_path / "parquet" / "canonical_bars.parquet")
    canonical = pd.read_parquet(tmp_path / "parquet" / "canonical_bars.parquet")
    assert first.run_id == second.run_id
    assert len(bars) == len(canonical) == 1


def test_concurrent_reruns_share_sync_lock(tmp_path):
    client = FakeDNSESDK()
    registry, _ = admitted_dnse(client)

    def run_once(_):
        return SourceSyncOrchestrator(
            tmp_path, registry=registry, today=lambda: date(2026, 9, 14),
            now=lambda: NOW, expected_session=lambda today: today).sync()

    with ThreadPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(run_once, range(4)))
    assert len({report.run_id for report in reports}) == 1
    assert len(client.ohlc_calls) == 1


def test_provider_failure_records_degraded_state_and_data_age(tmp_path):
    client, day = FakeDNSESDK(), [date(2026, 9, 14)]
    sync = orchestrator(tmp_path, client, day=lambda: day[0])
    good = sync.sync()
    day[0] = date(2026, 9, 16)
    client.fail = True
    degraded = sync.sync()
    assert good.status == SyncStatus.READY.value
    assert degraded.mode == SyncMode.DEGRADED_CACHED_DATA.value
    assert degraded.data_age_days == 2
    assert degraded.provider_id == "dnse_openapi"
    assert degraded.last_successful_sync == NOW.isoformat()
    assert degraded.failure_reason == "RuntimeError: fake DNSE outage"
    assert not degraded.actionable


def test_manual_file_not_required_for_normal_startup(tmp_path, monkeypatch):
    def forbidden_file_access(*args, **kwargs):
        raise AssertionError("manual provider must not be constructed or read")

    monkeypatch.setattr("vnquant.data.csv_provider.CSVProvider.__init__", forbidden_file_access)
    report = orchestrator(tmp_path, FakeDNSESDK()).sync()
    assert report.status == SyncStatus.READY.value
    assert not list(tmp_path.glob("*.csv"))
