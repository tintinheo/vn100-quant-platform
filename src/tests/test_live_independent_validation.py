from __future__ import annotations

from datetime import date, datetime, timezone
import json

import pandas as pd

from vnquant.data.base import DataMode, MarketDataProvider, ProviderFetch
from vnquant.data.live_validation import LiveIndependentValidationService
from vnquant.data.provider_registry import (
    AdmissionEvidence,
    ProviderRegistry,
    ProviderState,
    ValidationResult,
)
from vnquant.data.source_sync import SourceSyncOrchestrator
from vnquant.data.storage import Warehouse


class _FixtureProvider(MarketDataProvider):
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL

    def __init__(self, *, close=10.5, fail=False, raw_price_unit="VND"):
        self.close = close
        self.fail = fail
        self.raw_price_unit = raw_price_unit
        self.daily_calls = 0

    def _fetch(self, payload, parameters, source):
        if self.fail:
            raise RuntimeError("fixture provider outage")
        return ProviderFetch(
            self.provider_id,
            json.dumps(payload).encode(),
            datetime.now(timezone.utc),
            parameters,
            "fixture-adapter-1",
            source,
            "fixture_admitted",
            self.raw_price_unit,
            "raw",
        )

    def fetch_current_index_members(self, index_code="VN100"):
        return self._fetch(["AAA"], {"index_code": index_code}, f"test://{self.provider_id}/members")

    def normalize_index_members(self, fetched):
        return json.loads(fetched.payload)

    def fetch_daily_history(self, symbol, start, end):
        self.daily_calls += 1
        return self._fetch(
            [{
                "symbol": symbol,
                "trading_date": end.isoformat(),
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": self.close,
                "volume": 100,
                "value": 1050.0,
            }],
            {"symbol": symbol, "start": start.isoformat(), "end": end.isoformat()},
            f"test://{self.provider_id}/bars",
        )

    def normalize_daily_history(self, fetched):
        rows = json.loads(fetched.payload)
        for row in rows:
            row["trading_date"] = date.fromisoformat(row["trading_date"])
            row["provider"] = self.provider_id
        return pd.DataFrame(rows)


class PrimaryProvider(_FixtureProvider):
    provider_id = "dnse_openapi"


class SecondaryProvider(_FixtureProvider):
    provider_id = "vietstock_datafeed"


def _evidence():
    return AdmissionEvidence(
        record_version="fixture-v1",
        access_basis="fixture agreement",
        licence_reference="FIXTURE-LICENCE",
        capability_definitions={
            "daily_ohlcv": "fixture daily bars",
            "current_index_members": "fixture current members",
        },
        schema_and_units="VND prices and shares",
        timezone_date_semantics="Asia/Ho_Chi_Minh exchange date",
        raw_adjusted_policy="raw",
        revision_behavior="immutable fixture snapshots",
        quotas="fixture quota",
        history_depth="fixture range",
        universe_semantics="fixture membership",
        lineage_method="payload hash",
        validation_results=(
            ValidationResult("doctor", True, "fixture-doctor", date(2026, 9, 14)),
            ValidationResult("cross_validation", True, "fixture-cross", date(2026, 9, 14)),
        ),
        owner="fixture owner",
        reviewed_at=date(2026, 9, 14),
        next_review_at=date(2027, 9, 14),
    )


def _registry(primary, secondary):
    registry = ProviderRegistry()
    for provider in (primary, secondary):
        registry.register(provider, evidence=_evidence())
        registry.transition(provider.provider_id, ProviderState.DOCTOR_PASSED)
        registry.transition(provider.provider_id, ProviderState.CROSS_VALIDATED)
        registry.transition(provider.provider_id, ProviderState.ADMITTED)
    return registry


def _sync(tmp_path, primary, secondary):
    registry = _registry(primary, secondary)
    report = SourceSyncOrchestrator(
        tmp_path,
        registry=registry,
        today=lambda: date(2026, 9, 14),
    ).sync()
    assert report.provider_id == primary.provider_id
    assert report.actionable
    assert primary.daily_calls == 1
    assert secondary.daily_calls == 0
    return registry, report


def test_live_secondary_matching_source_is_verified_and_cached(tmp_path):
    primary, secondary = PrimaryProvider(), SecondaryProvider()
    registry, sync = _sync(tmp_path, primary, secondary)
    service = LiveIndependentValidationService(
        tmp_path,
        registry=registry,
        provider_origins={
            primary.provider_id: "origin-primary",
            secondary.provider_id: "origin-secondary",
        },
    )

    first = service.validate(sync)
    second = service.validate(sync)

    assert first.validation_status == "VERIFIED"
    assert first.validator_provider_id == secondary.provider_id
    assert first.source_names == (primary.provider_id, secondary.provider_id)
    assert first.independent_origins == ("origin-primary", "origin-secondary")
    assert first.buy_sell_allowed
    assert first.raw_snapshot_ids
    assert secondary.daily_calls == 1
    assert second.cache_hit
    assert secondary.daily_calls == 1
    observations = Warehouse(tmp_path).read_table("independent_validation_observations")
    assert set(observations.provider.astype(str)) == {secondary.provider_id}


def test_live_price_mismatch_is_quarantined(tmp_path):
    primary, secondary = PrimaryProvider(), SecondaryProvider(close=10.8)
    registry, sync = _sync(tmp_path, primary, secondary)
    result = LiveIndependentValidationService(
        tmp_path,
        registry=registry,
        provider_origins={
            primary.provider_id: "origin-primary",
            secondary.provider_id: "origin-secondary",
        },
    ).validate(sync)

    assert result.validation_status == "QUARANTINED"
    assert "DATA_SOURCE_PRICE_MISMATCH" in result.issues
    assert not result.buy_sell_allowed


def test_same_upstream_origin_is_not_used_as_independent_validator(tmp_path):
    primary, secondary = PrimaryProvider(), SecondaryProvider()
    registry, sync = _sync(tmp_path, primary, secondary)
    result = LiveIndependentValidationService(
        tmp_path,
        registry=registry,
        provider_origins={
            primary.provider_id: "shared-origin",
            secondary.provider_id: "shared-origin",
        },
    ).validate(sync)

    assert result.validation_status == "WARNING"
    assert result.validator_provider_id is None
    assert "NO_INDEPENDENT_VALIDATOR_ADMITTED" in result.issues
    assert result.buy_sell_allowed
    assert secondary.daily_calls == 0


def test_secondary_outage_is_warning_not_fake_verified(tmp_path):
    primary, secondary = PrimaryProvider(), SecondaryProvider(fail=True)
    registry, sync = _sync(tmp_path, primary, secondary)
    result = LiveIndependentValidationService(
        tmp_path,
        registry=registry,
        provider_origins={
            primary.provider_id: "origin-primary",
            secondary.provider_id: "origin-secondary",
        },
    ).validate(sync)

    assert result.validation_status == "WARNING"
    assert result.validator_provider_id == secondary.provider_id
    assert any(issue.startswith("VALIDATOR_FETCH_FAILED:") for issue in result.issues)
    assert result.buy_sell_allowed
    assert secondary.daily_calls == 1


def test_different_raw_price_units_are_quarantined_before_numeric_trust(tmp_path):
    primary = PrimaryProvider(raw_price_unit="VND")
    secondary = SecondaryProvider(raw_price_unit="THOUSAND_VND")
    registry, sync = _sync(tmp_path, primary, secondary)
    result = LiveIndependentValidationService(
        tmp_path,
        registry=registry,
        provider_origins={
            primary.provider_id: "origin-primary",
            secondary.provider_id: "origin-secondary",
        },
    ).validate(sync)

    assert result.validation_status == "QUARANTINED"
    assert "RAW_PRICE_UNIT_MISMATCH" in result.issues
    assert not result.buy_sell_allowed
