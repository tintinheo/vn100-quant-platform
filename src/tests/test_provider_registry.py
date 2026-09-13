from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from vnquant.data.base import DataMode, MarketDataProvider
from vnquant.data.provider_registry import (
    NO_ADMITTED_PROVIDER,
    AccessBasis,
    InvalidAdmissionEvidence,
    InvalidProviderTransition,
    NoAdmittedProvider,
    ProviderAdmissionEvidence,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderSelectionRequired,
    ProviderState,
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


def complete_evidence(
    *, access_basis: AccessBasis = AccessBasis.DOCUMENTED_PUBLIC_API
) -> ProviderAdmissionEvidence:
    return ProviderAdmissionEvidence(
        access_basis=access_basis,
        licence_reference="controlled-doc:terms-2026-01",
        schema_and_units="controlled-doc:schema-3; prices VND; volume shares",
        timezone_and_date_semantics="Asia/Ho_Chi_Minh; exchange trading date",
        raw_adjusted_policy="raw OHLC; separately identified adjusted close",
        revision_behavior="vendor corrections identified by revision timestamp",
        rate_limits="contract schedule A",
        lineage_method="immutable raw payload, request metadata and SHA-256",
        independent_validation_plan="report:sample-reconciliation-2026-01",
        owner="data-governance@example.invalid",
        reviewed_at=date(2026, 1, 1),
        next_review_at=date(2027, 1, 1),
        doctor_report_reference="doctor:2026-01-02",
        doctor_passed_at=date(2026, 1, 2),
        cross_validation_report_reference="cross-validation:2026-01-03",
        cross_validated_at=date(2026, 1, 3),
    )


def admit(
    registry: ProviderRegistry, provider: StubProvider, evidence: ProviderAdmissionEvidence
) -> None:
    registry.register(provider, evidence=evidence)
    registry.transition(
        provider.provider_id, ProviderState.DOCTOR_PASSED, evidence=evidence,
        as_of=date(2026, 1, 4),
    )
    registry.transition(
        provider.provider_id, ProviderState.CROSS_VALIDATED, evidence=evidence,
        as_of=date(2026, 1, 4),
    )
    registry.transition(
        provider.provider_id, ProviderState.ADMITTED, evidence=evidence,
        as_of=date(2026, 1, 4),
    )


@pytest.mark.parametrize("provider_id", ["ssi", "ssi_fastconnect", "ssi_fastconnect_v3"])
def test_ssi_cannot_become_active_accidentally(provider_id):
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotAllowed, match="retired provider"):
        registry.register(StubProvider(provider_id), evidence=complete_evidence())


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


def test_candidate_cannot_jump_directly_to_admitted():
    registry = ProviderRegistry()
    registry.register(StubProvider("documented_feed"), evidence=complete_evidence())

    with pytest.raises(InvalidProviderTransition, match="CANDIDATE -> ADMITTED"):
        registry.transition(
            "documented_feed", ProviderState.ADMITTED,
            evidence=complete_evidence(), as_of=date(2026, 1, 4),
        )


def test_documented_access_boolean_cannot_register_admitted_provider():
    registry = ProviderRegistry()

    with pytest.raises(InvalidProviderTransition, match="directly as ADMITTED"):
        registry.register(
            StubProvider("documented_feed"),
            state=ProviderState.ADMITTED,
            documented_access=True,
        )


def test_undocumented_endpoint_cannot_pass_doctor_gate():
    registry = ProviderRegistry()
    evidence = complete_evidence(access_basis=AccessBasis.UNDOCUMENTED_ENDPOINT)
    registry.register(StubProvider("browser_xhr"), evidence=evidence)

    with pytest.raises(InvalidAdmissionEvidence, match="not eligible"):
        registry.transition(
            "browser_xhr", ProviderState.DOCTOR_PASSED,
            evidence=evidence, as_of=date(2026, 1, 4),
        )


def test_incomplete_vietstock_contract_cannot_pass_doctor_gate():
    registry = ProviderRegistry()
    evidence = replace(
        complete_evidence(access_basis=AccessBasis.LICENSED_CONTRACT),
        schema_and_units="",
        rate_limits="",
    )
    registry.register(StubProvider("vietstock_datafeed"), evidence=evidence)

    with pytest.raises(InvalidAdmissionEvidence, match="schema_and_units, rate_limits"):
        registry.transition(
            "vietstock_datafeed", ProviderState.DOCTOR_PASSED,
            evidence=evidence, as_of=date(2026, 1, 4),
        )


def test_expired_review_blocks_real_selection():
    registry = ProviderRegistry()
    provider = StubProvider("licensed_feed")
    admit(registry, provider, complete_evidence())

    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        registry.select(
            provider_id="licensed_feed", capability="daily_ohlcv",
            mode=DataMode.REAL, as_of=date(2027, 1, 2),
        )


@pytest.mark.parametrize("mode", [DataMode.SYNTHETIC, DataMode.TEST])
def test_synthetic_and_test_providers_are_never_admission_eligible(mode):
    registry = ProviderRegistry()
    provider = StubProvider(f"{mode.value}_fixture", mode)
    registry.register(provider, evidence=complete_evidence())

    with pytest.raises(ProviderNotAllowed, match="never admission eligible"):
        registry.transition(
            provider.provider_id, ProviderState.DOCTOR_PASSED,
            evidence=complete_evidence(), as_of=date(2026, 1, 4),
        )
    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        registry.select(
            provider_id=provider.provider_id,
            capability="daily_ohlcv",
            mode=DataMode.REAL,
            as_of=date(2026, 1, 4),
        )
    assert registry.select(
        provider_id=provider.provider_id, capability="daily_ohlcv", mode=mode
    ) is provider


def test_admitted_evidence_and_state_are_persisted(tmp_path):
    path = tmp_path / "provider-admission.json"
    provider = StubProvider("licensed_feed")
    registry = ProviderRegistry(path)
    admit(registry, provider, complete_evidence())

    restarted = ProviderRegistry(path)
    restarted.register(provider)

    assert restarted.select(
        provider_id="licensed_feed", capability="daily_ohlcv",
        as_of=date(2026, 1, 4),
    ) is provider
    assert '"state": "ADMITTED"' in path.read_text(encoding="utf-8")
    assert '"licence_reference"' in path.read_text(encoding="utf-8")


def test_provider_selection_is_explicit():
    registry = ProviderRegistry()
    provider = StubProvider("licensed_feed")
    admit(registry, provider, complete_evidence())

    with pytest.raises(ProviderSelectionRequired, match="explicitly"):
        registry.select(
            provider_id=None, capability="daily_ohlcv", as_of=date(2026, 1, 4)
        )
    assert registry.select(
        provider_id="licensed_feed", capability="daily_ohlcv",
        as_of=date(2026, 1, 4),
    ) is provider


def test_no_ssi_runtime_dependency_or_module():
    source_root = Path(__file__).parents[1]

    assert "ssi-sdk" not in (source_root / "requirements-local.txt").read_text().lower()
    assert not (source_root / "vnquant" / "data" / "ssi.py").exists()
