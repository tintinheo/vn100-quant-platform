from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .base import DataMode, MarketDataProvider
from .providers.common import ProviderConfigurationError

NO_ADMITTED_PROVIDER = "NO_ADMITTED_PROVIDER"


class ProviderRegistryError(RuntimeError):
    code = "PROVIDER_REGISTRY_ERROR"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class NoAdmittedProvider(ProviderRegistryError):
    code = NO_ADMITTED_PROVIDER


class ProviderSelectionRequired(ProviderRegistryError):
    code = "PROVIDER_SELECTION_REQUIRED"


class ProviderNotAllowed(ProviderRegistryError):
    code = "PROVIDER_NOT_ALLOWED"


class ProviderState(str, Enum):
    """Governed admission lifecycle; only ``ADMITTED`` is runtime-selectable."""

    CANDIDATE = "CANDIDATE"
    DOCTOR_PASSED = "DOCTOR_PASSED"
    CROSS_VALIDATED = "CROSS_VALIDATED"
    ADMITTED = "ADMITTED"
    SUSPENDED = "SUSPENDED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class ValidationResult:
    """Auditable result supporting one admission milestone."""

    check: str
    passed: bool
    evidence_reference: str
    validated_at: date


@dataclass(frozen=True)
class AdmissionEvidence:
    """Versionable evidence required before a real provider can be admitted.

    Empty fields explicitly represent evidence gaps for candidates; they never
    act as permissive defaults. ``missing_requirements`` is the fail-closed gate.
    """

    record_version: str = "unversioned"
    access_basis: str = ""
    licence_reference: str = ""
    capability_definitions: Mapping[str, str] = field(default_factory=dict)
    schema_and_units: str = ""
    timezone_date_semantics: str = ""
    raw_adjusted_policy: str = ""
    revision_behavior: str = ""
    quotas: str = ""
    history_depth: str = ""
    universe_semantics: str = ""
    lineage_method: str = ""
    validation_results: tuple[ValidationResult, ...] = ()
    owner: str = ""
    reviewed_at: date | None = None
    next_review_at: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "capability_definitions", MappingProxyType(dict(self.capability_definitions))
        )
        object.__setattr__(self, "validation_results", tuple(self.validation_results))

    def missing_requirements(self, capabilities: frozenset[str]) -> tuple[str, ...]:
        values = {
            "access_basis": self.access_basis,
            "licence_reference": self.licence_reference,
            "schema_and_units": self.schema_and_units,
            "timezone_date_semantics": self.timezone_date_semantics,
            "raw_adjusted_policy": self.raw_adjusted_policy,
            "revision_behavior": self.revision_behavior,
            "quotas": self.quotas,
            "history_depth": self.history_depth,
            "universe_semantics": self.universe_semantics,
            "lineage_method": self.lineage_method,
            "validation_results": self.validation_results,
            "owner": self.owner,
            "reviewed_at": self.reviewed_at,
            "next_review_at": self.next_review_at,
        }
        missing = [name for name, value in values.items() if not value]
        undefined = capabilities.difference(self.capability_definitions)
        if undefined:
            missing.append(f"capability_definitions[{','.join(sorted(undefined))}]")
        if (
            self.reviewed_at is not None
            and self.next_review_at is not None
            and self.next_review_at <= self.reviewed_at
        ):
            missing.append("next_review_at_after_reviewed_at")
        return tuple(missing)

    def passed(self, check: str) -> bool:
        return any(
            result.check == check and result.passed and bool(result.evidence_reference.strip())
            for result in self.validation_results
        )


@dataclass(frozen=True)
class ProviderRegistration:
    provider: MarketDataProvider
    state: ProviderState
    evidence: AdmissionEvidence
    config_version: str = "unversioned"
    enabled: bool = True
    role: str = "unspecified"


class ProviderRegistry:
    """Explicit, evidence-backed provider admission and selection boundary."""

    _RETIRED_PROVIDER_IDS = frozenset({"ssi", "ssi_fastconnect", "ssi_fastconnect_v3"})
    _TRANSITIONS = {
        ProviderState.CANDIDATE: frozenset(
            {ProviderState.DOCTOR_PASSED, ProviderState.SUSPENDED, ProviderState.RETIRED}
        ),
        ProviderState.DOCTOR_PASSED: frozenset(
            {ProviderState.CROSS_VALIDATED, ProviderState.SUSPENDED, ProviderState.RETIRED}
        ),
        ProviderState.CROSS_VALIDATED: frozenset(
            {ProviderState.ADMITTED, ProviderState.SUSPENDED, ProviderState.RETIRED}
        ),
        ProviderState.ADMITTED: frozenset({ProviderState.SUSPENDED, ProviderState.RETIRED}),
        ProviderState.SUSPENDED: frozenset({ProviderState.CANDIDATE, ProviderState.RETIRED}),
        ProviderState.RESEARCH_ONLY: frozenset({ProviderState.RETIRED}),
        ProviderState.RETIRED: frozenset(),
    }

    def __init__(self) -> None:
        self._registrations: dict[str, ProviderRegistration] = {}

    @staticmethod
    def _provider_id(provider: MarketDataProvider) -> str:
        provider_id = getattr(provider, "provider_id", "").strip().lower()
        if not provider_id:
            raise ProviderNotAllowed("provider_id is required")
        return provider_id

    def register(
        self,
        provider: MarketDataProvider,
        *,
        evidence: AdmissionEvidence,
        state: ProviderState = ProviderState.CANDIDATE,
        config_version: str = "unversioned",
        enabled: bool = True,
        role: str = "unspecified",
    ) -> None:
        provider_id = self._provider_id(provider)
        if provider_id in self._RETIRED_PROVIDER_IDS or provider_id.startswith("ssi_"):
            raise ProviderNotAllowed(f"retired provider {provider_id!r} cannot be registered")
        if state not in {ProviderState.CANDIDATE, ProviderState.RESEARCH_ONLY}:
            raise ProviderNotAllowed("new providers must start as CANDIDATE or RESEARCH_ONLY")
        if not evidence.record_version.strip() or not config_version.strip():
            raise ProviderNotAllowed("provider configuration and evidence versions are required")
        self._registrations[provider_id] = ProviderRegistration(
            provider, state, evidence, config_version, enabled, role
        )

    def update_evidence(self, provider_id: str, evidence: AdmissionEvidence) -> None:
        registration = self.registration(provider_id)
        if registration.state is ProviderState.RETIRED:
            raise ProviderNotAllowed("retired provider evidence cannot be changed")
        self._registrations[provider_id.strip().lower()] = replace(
            registration, evidence=evidence
        )

    def transition(self, provider_id: str, target: ProviderState) -> None:
        normalized = provider_id.strip().lower()
        registration = self.registration(normalized)
        if target not in self._TRANSITIONS[registration.state]:
            raise ProviderNotAllowed(
                f"invalid provider transition {registration.state.value} -> {target.value}"
            )
        if target in {
            ProviderState.DOCTOR_PASSED,
            ProviderState.CROSS_VALIDATED,
            ProviderState.ADMITTED,
        }:
            self._validate_promotion(registration, target)
        self._registrations[normalized] = replace(registration, state=target)

    @staticmethod
    def _validate_promotion(
        registration: ProviderRegistration, target: ProviderState
    ) -> None:
        provider = registration.provider
        if not registration.enabled:
            raise ProviderNotAllowed("a disabled provider cannot enter admission states")
        if provider.data_mode is not DataMode.REAL:
            raise ProviderNotAllowed("synthetic/test providers cannot enter admission states")
        if getattr(provider, "reference_only", False):
            raise ProviderNotAllowed("a reference-only provider cannot enter admission states")

        contract = getattr(provider, "contract", None)
        if contract is not None and callable(getattr(contract, "validate", None)):
            try:
                contract.validate()
            except ProviderConfigurationError as error:
                raise ProviderNotAllowed(f"provider contract is incomplete: {error}") from error

        evidence = registration.evidence
        missing = evidence.missing_requirements(provider.capabilities)
        if missing:
            raise ProviderNotAllowed("incomplete admission evidence: " + ", ".join(missing))
        required_check = {
            ProviderState.DOCTOR_PASSED: "doctor",
            ProviderState.CROSS_VALIDATED: "cross_validation",
            ProviderState.ADMITTED: "cross_validation",
        }[target]
        if not evidence.passed(required_check):
            raise ProviderNotAllowed(
                f"passing {required_check!r} validation evidence is required"
            )

    def admitted_provider_ids(self, capability: str) -> tuple[str, ...]:
        return tuple(
            provider_id
            for provider_id, registration in self._registrations.items()
            if registration.state is ProviderState.ADMITTED
            and registration.enabled
            and not registration.evidence.missing_requirements(
                registration.provider.capabilities
            )
            and registration.provider.data_mode is DataMode.REAL
            and capability in registration.provider.capabilities
        )

    def registration(self, provider_id: str) -> ProviderRegistration:
        normalized = provider_id.strip().lower()
        registration = self._registrations.get(normalized)
        if registration is None:
            raise ProviderNotAllowed(f"provider {normalized!r} is not registered")
        return registration

    def select(
        self,
        *,
        provider_id: str | None,
        capability: str,
        mode: DataMode = DataMode.REAL,
    ) -> MarketDataProvider:
        if mode is DataMode.REAL:
            admitted = self.admitted_provider_ids(capability)
            if not admitted:
                raise NoAdmittedProvider(
                    f"real-data capability {capability!r} has no admitted provider"
                )
            if provider_id is None:
                raise ProviderSelectionRequired(
                    f"choose an admitted provider explicitly from {admitted}"
                )
        elif provider_id is None:
            raise ProviderSelectionRequired(f"provider is required for {mode.value} mode")

        normalized = provider_id.strip().lower()
        registration = self._registrations.get(normalized)
        if registration is None:
            raise ProviderNotAllowed(f"provider {normalized!r} is not registered")
        if registration.provider.data_mode is not mode:
            raise ProviderNotAllowed(
                f"provider {normalized!r} is {registration.provider.data_mode.value}, not {mode.value}"
            )
        if mode is DataMode.REAL and registration.state is not ProviderState.ADMITTED:
            raise NoAdmittedProvider(f"provider {normalized!r} is not admitted")
        if capability not in registration.provider.capabilities:
            raise ProviderNotAllowed(
                f"provider {normalized!r} lacks capability {capability!r}"
            )
        return registration.provider


def default_provider_registry(*, secret_store=None) -> ProviderRegistry:
    """Build the fail-closed registry from the packaged, versioned policy file.

    ``secret_store`` may be an approved mapping/getter such as
    ``st.secrets.get``.  Credential values are resolved lazily by the adapter
    and are never copied into registry records or admission evidence.
    """
    from vnquant.config import provider_configurations
    from .providers import (
        CafeFReferenceProvider,
        DNSECredentialSource,
        DNSEProvider,
        VietstockDataFeedProvider,
    )

    registry = ProviderRegistry()
    adapters = {
        "dnse": lambda record: DNSEProvider(
            credential_source=DNSECredentialSource(
                record.credentials["api_key_reference"],
                record.credentials["api_secret_reference"],
                secret_store=secret_store,
            )
        ),
        "vietstock": lambda record: VietstockDataFeedProvider(),
        "cafef": lambda record: CafeFReferenceProvider(allow_reference_source=False),
    }
    for record in provider_configurations():
        try:
            provider = adapters[record.adapter](record)
            state = ProviderState(record.state)
        except (KeyError, ValueError) as error:
            raise ProviderNotAllowed(
                f"invalid versioned configuration for {record.provider_id!r}"
            ) from error
        if provider.provider_id != record.provider_id:
            raise ProviderNotAllowed(f"configured provider id {record.provider_id!r} mismatches adapter")
        evidence_fields = AdmissionEvidence.__dataclass_fields__
        evidence = AdmissionEvidence(
            **{key: value for key, value in record.evidence.items() if key in evidence_fields}
        )
        registry.register(
            provider,
            state=state,
            evidence=evidence,
            config_version=record.config_version,
            enabled=record.enabled,
            role=record.role,
        )
    return registry
