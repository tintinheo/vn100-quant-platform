from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from vnquant.data.base import DataMode, MarketDataProvider
from vnquant.data.provider_registry import (
    AdmissionEvidence,
    NO_ADMITTED_PROVIDER,
    NoAdmittedProvider,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderSelectionRequired,
    ProviderState,
    ValidationResult,
)
from vnquant.jobs.bootstrap import run as run_bootstrap
from vnquant.jobs.doctor import run as run_doctor


class StubProvider(MarketDataProvider):
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})

    def __init__(self, provider_id: str, data_mode: DataMode = DataMode.REAL):
        self.provider_id = provider_id
        self.data_mode = data_mode

    def current_index_members(self, index_code: str = "VN100") -> list[str]:
        return ["VNM"]

    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        raise AssertionError("test selection must not fetch data")


def complete_evidence(*, cross_validated: bool = True) -> AdmissionEvidence:
    checks = [ValidationResult("doctor", True, "doctor-run-42", date(2026, 9, 14))]
    if cross_validated:
        checks.append(
            ValidationResult(
                "cross_validation", True, "comparison-report-7", date(2026, 9, 14)
            )
        )
    return AdmissionEvidence(
        access_basis="signed internal-use data agreement",
        licence_reference="LIC-2026-09",
        capability_definitions={
            "daily_ohlcv": "daily raw OHLCV in VND and shares",
            "current_index_members": "effective current VN100 constituents",
        },
        schema_and_units="schema-v2: prices VND; volume shares",
        timezone_date_semantics="Asia/Ho_Chi_Minh; exchange trading date",
        raw_adjusted_policy="OHLC raw; adjusted close separately identified",
        revision_behavior="vendor revisions append immutable snapshots",
        quotas="120 requests/minute under LIC-2026-09",
        lineage_method="request metadata plus immutable payload SHA-256",
        validation_results=tuple(checks),
        owner="market-data owner",
        reviewed_at=date(2026, 9, 14),
        next_review_at=date(2026, 12, 14),
    )


def admit(registry: ProviderRegistry, provider: MarketDataProvider) -> None:
    registry.register(provider, evidence=complete_evidence())
    registry.transition(provider.provider_id, ProviderState.DOCTOR_PASSED)
    registry.transition(provider.provider_id, ProviderState.CROSS_VALIDATED)
    registry.transition(provider.provider_id, ProviderState.ADMITTED)


@pytest.mark.parametrize("provider_id", ["ssi", "ssi_fastconnect", "ssi_fastconnect_v3"])
def test_ssi_cannot_become_active_accidentally(provider_id):
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotAllowed, match="retired provider"):
        registry.register(
            StubProvider(provider_id),
            evidence=complete_evidence(),
        )


def test_application_starts_without_ssi_credentials(monkeypatch, capsys):
    for name in ("SSI_CLIENT_ID", "SSI_API_KEY", "SSI_API_SECRET"):
        monkeypatch.delenv(name, raising=False)

    assert run_doctor() == 2
    assert NO_ADMITTED_PROVIDER in capsys.readouterr().out


def test_real_data_ingestion_fails_safely_without_admitted_provider(tmp_path):
    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        run_bootstrap(
            provider_id=None,
            start=date(2026, 1, 1),
            end=date(2026, 1, 2),
            data_dir=str(tmp_path),
        )

    assert list(tmp_path.iterdir()) == []


def test_synthetic_provider_cannot_masquerade_as_real_data():
    registry = ProviderRegistry()
    provider = StubProvider("fixture_generator", DataMode.SYNTHETIC)
    registry.register(provider, evidence=complete_evidence())

    with pytest.raises(ProviderNotAllowed, match="synthetic/test"):
        registry.transition("fixture_generator", ProviderState.DOCTOR_PASSED)

    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        registry.select(
            provider_id="fixture_generator",
            capability="daily_ohlcv",
            mode=DataMode.REAL,
        )
    assert registry.select(provider_id="fixture_generator", capability="daily_ohlcv",
                           mode=DataMode.SYNTHETIC) is provider


def test_provider_selection_is_explicit():
    registry = ProviderRegistry()
    provider = StubProvider("licensed_feed")
    admit(registry, provider)

    with pytest.raises(ProviderSelectionRequired, match="explicitly"):
        registry.select(provider_id=None, capability="daily_ohlcv")
    assert registry.select(
        provider_id="licensed_feed", capability="daily_ohlcv"
    ) is provider


def test_missing_evidence_blocks_admission_progress():
    registry = ProviderRegistry()
    registry.register(StubProvider("undocumented"), evidence=AdmissionEvidence())

    with pytest.raises(ProviderNotAllowed, match="incomplete admission evidence"):
        registry.transition("undocumented", ProviderState.DOCTOR_PASSED)


def test_candidate_cannot_promote_directly_to_admitted():
    registry = ProviderRegistry()
    registry.register(StubProvider("licensed_feed"), evidence=complete_evidence())

    with pytest.raises(ProviderNotAllowed, match="CANDIDATE -> ADMITTED"):
        registry.transition("licensed_feed", ProviderState.ADMITTED)


def test_invalid_transition_and_suspension_require_revalidation_path():
    registry = ProviderRegistry()
    provider = StubProvider("licensed_feed")
    admit(registry, provider)
    registry.transition(provider.provider_id, ProviderState.SUSPENDED)

    with pytest.raises(ProviderNotAllowed, match="SUSPENDED -> ADMITTED"):
        registry.transition(provider.provider_id, ProviderState.ADMITTED)
    registry.transition(provider.provider_id, ProviderState.CANDIDATE)
    assert registry.registration(provider.provider_id).state is ProviderState.CANDIDATE


def test_no_ssi_runtime_dependency_or_module():
    source_root = Path(__file__).parents[1]

    assert "ssi-sdk" not in (source_root / "requirements-local.txt").read_text().lower()
    assert not (source_root / "vnquant" / "data" / "ssi.py").exists()
