from __future__ import annotations

from datetime import date

from vnquant.data.base import DataMode, MarketDataProvider
from vnquant.data.provider_registry import (
    AdmissionEvidence,
    ProviderRegistry,
    ProviderState,
    ValidationResult,
)
from vnquant.data.providers.common import ProviderConfigurationError
from vnquant.jobs.doctor import run


class FailingDoctorProvider(MarketDataProvider):
    provider_id = "doctor_fixture"
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})
    data_mode = DataMode.REAL

    def __init__(self) -> None:
        self.closed = False

    def fetch_current_index_members(self, index_code="VN100"):
        raise ProviderConfigurationError("fixture contract is unavailable")

    def close(self) -> None:
        self.closed = True


def _admitted(provider: MarketDataProvider) -> ProviderRegistry:
    evidence = AdmissionEvidence(
        access_basis="test agreement",
        licence_reference="TEST-LICENCE",
        capability_definitions={capability: "fixture" for capability in provider.capabilities},
        schema_and_units="fixture VND/shares",
        timezone_date_semantics="fixture exchange date",
        raw_adjusted_policy="raw",
        revision_behavior="fixture snapshots",
        quotas="fixture quota",
        history_depth="fixture range verified", universe_semantics="fixture membership verified",
        lineage_method="fixture hash",
        validation_results=(
            ValidationResult("doctor", True, "fixture-doctor", date(2026, 9, 15)),
            ValidationResult("cross_validation", True, "fixture-cross", date(2026, 9, 15)),
        ),
        owner="test owner",
        reviewed_at=date(2026, 9, 15),
        next_review_at=date(2027, 9, 15),
    )
    registry = ProviderRegistry()
    registry.register(provider, evidence=evidence)
    for state in (
        ProviderState.DOCTOR_PASSED,
        ProviderState.CROSS_VALIDATED,
        ProviderState.ADMITTED,
    ):
        registry.transition(provider.provider_id, state)
    return registry


def test_doctor_reports_expected_provider_failure_and_closes(capsys):
    provider = FailingDoctorProvider()

    result = run(provider_id=provider.provider_id, registry=_admitted(provider))

    assert result == 2
    assert "DOCTOR_FAILED: fixture contract is unavailable" in capsys.readouterr().out
    assert provider.closed is True
