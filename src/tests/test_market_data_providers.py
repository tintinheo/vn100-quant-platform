from __future__ import annotations

from datetime import date

import pytest

from vnquant.data.provider_registry import (
    AdmissionEvidence,
    NoAdmittedProvider,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderState,
    default_provider_registry,
)
from vnquant.data.providers import (
    CafeFReferenceProvider,
    DNSECredentialSource,
    DNSECredentials,
    DNSEProvider,
    VietstockDataFeedContract,
    VietstockDataFeedProvider,
)
from vnquant.data.providers.common import ProviderConfigurationError
from vnquant.config.provider_configuration import ProviderConfiguration


class SuccessfulDNSEClient:
    def get_instruments(self, **kwargs):
        return {"data": [{"symbol": "VNM"}]}

    def get_ohlc(self, **kwargs):
        return {
            "data": [
                {
                    "time": 1_788_825_600,
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 1_000,
                }
            ]
        }


def test_default_implementations_are_registered_but_not_admitted():
    registry = default_provider_registry()

    assert registry.registration("dnse_openapi").state is ProviderState.CANDIDATE
    assert registry.registration("vietstock_datafeed").state is ProviderState.CANDIDATE
    assert registry.registration("cafef_reference").state is ProviderState.RESEARCH_ONLY
    assert registry.admitted_provider_ids("daily_ohlcv") == ()
    assert registry.registration("dnse_openapi").config_version == "1.0.0"
    assert registry.registration("dnse_openapi").role == "leading_read_only_candidate"
    assert registry.registration("dnse_openapi").enabled is True
    assert registry.registration("vietstock_datafeed").enabled is False
    assert registry.registration("cafef_reference").enabled is False
    assert registry.registration("dnse_openapi").evidence.record_version == "1.0.0"
    assert "schema_and_units" in registry.registration(
        "dnse_openapi"
    ).evidence.missing_requirements(DNSEProvider.capabilities)
    with pytest.raises(NoAdmittedProvider):
        registry.select(provider_id="dnse_openapi", capability="daily_ohlcv")


def _configured_dnse(state: str, *, doctor_passed: bool = True,
                     cross_validated: bool = True) -> ProviderConfiguration:
    validations = [
        {"check": "doctor", "passed": doctor_passed,
         "evidence_reference": "evidence/dnse-doctor.json",
         "validated_at": "2026-09-15"},
        {"check": "cross_validation", "passed": cross_validated,
         "evidence_reference": "evidence/dnse-reconciliation.json",
         "validated_at": "2026-09-15"},
    ]
    return ProviderConfiguration(
        provider_id="dnse_openapi", config_version="test-approved-record",
        enabled=True, role="leading_read_only_candidate", state=state,
        adapter="dnse",
        credentials={"api_key_reference": "DNSE_API_KEY",
                     "api_secret_reference": "DNSE_API_SECRET"},
        evidence={
            "record_version": "test-admission-v1",
            "access_basis": "fixture authorized access",
            "licence_reference": "fixture licence",
            "capability_definitions": {
                capability: "fixture verified capability"
                for capability in DNSEProvider.capabilities
            },
            "schema_and_units": "fixture schemas and units",
            "timezone_date_semantics": "fixture timezone and exchange date",
            "raw_adjusted_policy": "fixture raw policy",
            "revision_behavior": "fixture revision observations",
            "quotas": "fixture quotas",
            "history_depth": "fixture history coverage",
            "universe_semantics": "fixture official VN100 reconciliation",
            "lineage_method": "immutable raw fixture snapshots",
            "validation_results": validations,
            "owner": "fixture data owner",
            "reviewed_at": "2026-09-15",
            "next_review_at": "2026-12-15",
        },
    )


def test_default_registry_replays_approved_admission_record(monkeypatch):
    monkeypatch.setattr(
        "vnquant.config.provider_configurations",
        lambda: (_configured_dnse("ADMITTED"),),
    )

    registry = default_provider_registry()

    assert registry.registration("dnse_openapi").state is ProviderState.ADMITTED
    assert registry.admitted_provider_ids("daily_ohlcv") == ("dnse_openapi",)


@pytest.mark.parametrize(
    ("doctor_passed", "cross_validated", "message"),
    [
        (False, True, "passing 'doctor'"),
        (True, False, "passing 'cross_validation'"),
    ],
)
def test_configured_admission_record_fails_closed_on_failed_gates(
    monkeypatch, doctor_passed, cross_validated, message
):
    monkeypatch.setattr(
        "vnquant.config.provider_configurations",
        lambda: (_configured_dnse(
            "ADMITTED", doctor_passed=doctor_passed,
            cross_validated=cross_validated,
        ),),
    )

    with pytest.raises(ProviderNotAllowed, match=message):
        default_provider_registry()


def test_dnse_credentials_resolve_from_environment_without_storing_values(monkeypatch):
    monkeypatch.setenv("DNSE_API_KEY", "fake-key")
    monkeypatch.setenv("DNSE_API_SECRET", "fake-secret")
    source = DNSECredentialSource("DNSE_API_KEY", "DNSE_API_SECRET")

    assert source.resolve() == DNSECredentials("fake-key", "fake-secret")
    assert "fake-secret" not in repr(source)


def test_dnse_credentials_can_resolve_from_approved_secret_store():
    secrets = {"key-ref": "fake-key", "secret-ref": "fake-secret"}
    source = DNSECredentialSource("key-ref", "secret-ref", secret_store=secrets.get)

    assert source.resolve() == DNSECredentials("fake-key", "fake-secret")


def test_default_registry_wires_approved_secret_store_without_persisting_values():
    secrets = {"DNSE_API_KEY": "fake-key", "DNSE_API_SECRET": "fake-secret"}
    registry = default_provider_registry(secret_store=secrets.get)
    provider = registry.registration("dnse_openapi").provider

    assert provider._credential_source.resolve() == DNSECredentials("fake-key", "fake-secret")
    assert "fake-key" not in repr(registry.registration("dnse_openapi"))
    assert "fake-secret" not in repr(registry.registration("dnse_openapi"))


def test_environment_credentials_take_precedence_over_secret_store(monkeypatch):
    monkeypatch.setenv("DNSE_API_KEY", "environment-key")
    monkeypatch.setenv("DNSE_API_SECRET", "environment-secret")
    source = DNSECredentialSource(
        "DNSE_API_KEY", "DNSE_API_SECRET",
        secret_store={"DNSE_API_KEY": "stored-key", "DNSE_API_SECRET": "stored-secret"},
    )

    assert source.resolve() == DNSECredentials("environment-key", "environment-secret")


def test_missing_dnse_credentials_fail_redacted(monkeypatch):
    monkeypatch.delenv("DNSE_API_KEY", raising=False)
    monkeypatch.delenv("DNSE_API_SECRET", raising=False)
    registry = default_provider_registry()
    source = registry.registration("dnse_openapi").provider._credential_source

    with pytest.raises(ProviderConfigurationError) as caught:
        source.resolve()
    message = str(caught.value)
    assert "credentials are unavailable" in message
    assert "DNSE_API_KEY" not in message
    assert "DNSE_API_SECRET" not in message


def test_disabled_vietstock_cannot_be_promoted_even_with_future_evidence():
    registry = default_provider_registry()

    with pytest.raises(ProviderNotAllowed, match="disabled provider"):
        registry.transition("vietstock_datafeed", ProviderState.DOCTOR_PASSED)


def test_dnse_http_success_does_not_promote_admission():
    provider = DNSEProvider(client=SuccessfulDNSEClient())
    registry = ProviderRegistry()
    registry.register(provider, evidence=AdmissionEvidence())

    assert provider.current_index_members() == ["VNM"]
    assert not provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9)).empty
    assert registry.registration("dnse_openapi").state is ProviderState.CANDIDATE
    assert registry.admitted_provider_ids("daily_ohlcv") == ()


@pytest.mark.parametrize(
    "state",
    [
        ProviderState.CANDIDATE,
        ProviderState.RESEARCH_ONLY,
        ProviderState.SUSPENDED,
    ],
)
def test_every_non_admitted_governance_state_remains_unselectable(state):
    provider = DNSEProvider(client=SuccessfulDNSEClient())
    registry = ProviderRegistry()
    initial = ProviderState.CANDIDATE if state is ProviderState.SUSPENDED else state
    registry.register(provider, state=initial, evidence=AdmissionEvidence())
    if state is ProviderState.SUSPENDED:
        registry.transition(provider.provider_id, state)

    # A successful provider response is operational evidence, not admission.
    assert provider.current_index_members() == ["VNM"]
    assert registry.registration(provider.provider_id).state is state
    with pytest.raises(NoAdmittedProvider):
        registry.select(provider_id=provider.provider_id, capability="daily_ohlcv")


def test_dnse_surface_has_no_brokerage_execution_methods():
    forbidden = {"order", "place_order", "otp", "trading_token", "execute_trade"}
    assert forbidden.isdisjoint(dir(DNSEProvider))


def test_vietstock_incomplete_contract_fails_before_transport():
    transport_called = False

    def transport(**kwargs):
        nonlocal transport_called
        transport_called = True
        return []

    provider = VietstockDataFeedProvider(transport=transport)
    with pytest.raises(ProviderConfigurationError, match="incomplete authorized"):
        provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9))
    assert transport_called is False


def test_authorized_vietstock_http_success_still_does_not_admit_provider():
    contract = VietstockDataFeedContract(
        authorized=True,
        base_url="https://licensed.example",
        authentication={"Authorization": "fake-test-value"},
        paths={"current_index_members": "/members", "daily_history": "/history"},
        parameters={"index_code": "index", "symbol": "ticker", "start": "from", "end": "to"},
        schema_mapping={
            "symbol": "ticker", "trading_date": "date", "open": "o", "high": "h",
            "low": "l", "close": "c", "volume": "v",
        },
        units={"price_multiplier": 1},
        endpoint_semantics="vendor contract operation definitions",
        revision_policy="vendor contract revision clause",
        rate_limits="vendor contract quota",
        retention_rights="raw and normalized records may be retained",
        usage_rights="authorized for internal research",
    )
    provider = VietstockDataFeedProvider(contract, transport=lambda **kwargs: [{"ticker": "VNM"}])
    registry = ProviderRegistry()
    registry.register(provider, evidence=AdmissionEvidence())

    assert provider.current_index_members() == ["VNM"]
    assert registry.registration("vietstock_datafeed").state is ProviderState.CANDIDATE
    assert registry.admitted_provider_ids("current_index_members") == ()


def test_cafef_is_disabled_and_reference_only():
    provider = CafeFReferenceProvider(page_fetcher=lambda url: "<html></html>")
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9))
    assert provider.reference_only is True
    assert provider.primary_eligible is False
    assert "daily_ohlcv" not in provider.capabilities


def test_cafef_cannot_be_promoted_to_admitted_provider():
    registry = ProviderRegistry()
    provider = CafeFReferenceProvider(allow_reference_source=True, page_fetcher=lambda url: "")
    registry.register(provider, state=ProviderState.RESEARCH_ONLY, evidence=AdmissionEvidence())

    with pytest.raises(ProviderNotAllowed, match="RESEARCH_ONLY -> ADMITTED"):
        registry.transition(provider.provider_id, ProviderState.ADMITTED)


def test_incomplete_vietstock_contract_cannot_pass_doctor_state():
    registry = ProviderRegistry()
    provider = VietstockDataFeedProvider()
    registry.register(provider, evidence=AdmissionEvidence())

    with pytest.raises(ProviderNotAllowed, match="provider contract is incomplete"):
        registry.transition(provider.provider_id, ProviderState.DOCTOR_PASSED)
