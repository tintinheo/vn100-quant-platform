from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from .base import DataMode, MarketDataProvider

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


class InvalidProviderTransition(ProviderNotAllowed):
    code = "INVALID_PROVIDER_TRANSITION"


class InvalidAdmissionEvidence(ProviderNotAllowed):
    code = "INVALID_ADMISSION_EVIDENCE"


class ProviderState(str, Enum):
    """Authoritative production-admission lifecycle."""

    CANDIDATE = "CANDIDATE"
    DOCTOR_PASSED = "DOCTOR_PASSED"
    CROSS_VALIDATED = "CROSS_VALIDATED"
    ADMITTED = "ADMITTED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class AccessBasis(str, Enum):
    DOCUMENTED_PUBLIC_API = "DOCUMENTED_PUBLIC_API"
    LICENSED_CONTRACT = "LICENSED_CONTRACT"
    AUTHORIZED_EXPORT = "AUTHORIZED_EXPORT"
    UNDOCUMENTED_ENDPOINT = "UNDOCUMENTED_ENDPOINT"
    SYNTHETIC_OR_TEST = "SYNTHETIC_OR_TEST"


@dataclass(frozen=True)
class ProviderAdmissionEvidence:
    """Reviewable evidence required before a real provider can be admitted.

    References identify controlled documents or reports rather than containing
    credentials. The model is JSON serializable so the registry can retain the
    exact evidence used for each lifecycle decision.
    """

    access_basis: AccessBasis
    licence_reference: str
    schema_and_units: str
    timezone_and_date_semantics: str
    raw_adjusted_policy: str
    revision_behavior: str
    rate_limits: str
    lineage_method: str
    independent_validation_plan: str
    owner: str
    reviewed_at: date
    next_review_at: date
    doctor_report_reference: str | None = None
    doctor_passed_at: date | None = None
    cross_validation_report_reference: str | None = None
    cross_validated_at: date | None = None

    _REQUIRED_TEXT = (
        "licence_reference",
        "schema_and_units",
        "timezone_and_date_semantics",
        "raw_adjusted_policy",
        "revision_behavior",
        "rate_limits",
        "lineage_method",
        "independent_validation_plan",
        "owner",
    )

    def validate(self, *, as_of: date, state: ProviderState) -> None:
        missing = [name for name in self._REQUIRED_TEXT if not getattr(self, name).strip()]
        if missing:
            raise InvalidAdmissionEvidence(
                "missing admission evidence: " + ", ".join(missing)
            )
        if self.access_basis in {
            AccessBasis.UNDOCUMENTED_ENDPOINT,
            AccessBasis.SYNTHETIC_OR_TEST,
        }:
            raise InvalidAdmissionEvidence(
                f"access basis {self.access_basis.value} is not eligible for admission"
            )
        if self.reviewed_at > as_of:
            raise InvalidAdmissionEvidence("reviewed_at cannot be in the future")
        if self.next_review_at < self.reviewed_at:
            raise InvalidAdmissionEvidence("next_review_at precedes reviewed_at")
        if self.next_review_at < as_of:
            raise InvalidAdmissionEvidence("admission evidence review has expired")
        if state in {
            ProviderState.DOCTOR_PASSED,
            ProviderState.CROSS_VALIDATED,
            ProviderState.ADMITTED,
        } and (not self.doctor_report_reference or self.doctor_passed_at is None):
            raise InvalidAdmissionEvidence("a passed doctor report is required")
        if self.doctor_passed_at is not None and self.doctor_passed_at > as_of:
            raise InvalidAdmissionEvidence("doctor_passed_at cannot be in the future")
        if state in {ProviderState.CROSS_VALIDATED, ProviderState.ADMITTED} and (
            not self.cross_validation_report_reference
            or self.cross_validated_at is None
        ):
            raise InvalidAdmissionEvidence("independent cross-validation evidence is required")
        if self.cross_validated_at is not None and self.cross_validated_at > as_of:
            raise InvalidAdmissionEvidence("cross_validated_at cannot be in the future")
        if (
            self.doctor_passed_at is not None
            and self.cross_validated_at is not None
            and self.cross_validated_at < self.doctor_passed_at
        ):
            raise InvalidAdmissionEvidence("cross-validation predates the doctor gate")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["access_basis"] = self.access_basis.value
        for field in (
            "reviewed_at",
            "next_review_at",
            "doctor_passed_at",
            "cross_validated_at",
        ):
            value = payload[field]
            payload[field] = value.isoformat() if value is not None else None
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderAdmissionEvidence":
        values = dict(payload)
        values["access_basis"] = AccessBasis(values["access_basis"])
        for field in (
            "reviewed_at",
            "next_review_at",
            "doctor_passed_at",
            "cross_validated_at",
        ):
            if values.get(field) is not None:
                values[field] = date.fromisoformat(values[field])
        return cls(**values)


@dataclass(frozen=True)
class ProviderRegistration:
    provider: MarketDataProvider
    state: ProviderState
    evidence: ProviderAdmissionEvidence | None


class ProviderRegistry:
    """Persisted provider admission and explicit runtime selection boundary."""

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
        ProviderState.ADMITTED: frozenset(
            {ProviderState.SUSPENDED, ProviderState.RETIRED}
        ),
        ProviderState.SUSPENDED: frozenset({ProviderState.RETIRED}),
        ProviderState.RETIRED: frozenset(),
    }

    def __init__(self, evidence_path: str | Path | None = None) -> None:
        self._registrations: dict[str, ProviderRegistration] = {}
        self._evidence_path = Path(evidence_path) if evidence_path is not None else None
        self._persisted = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._evidence_path is None or not self._evidence_path.exists():
            return {}
        payload = json.loads(self._evidence_path.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("providers"), dict):
            raise InvalidAdmissionEvidence("unsupported provider evidence store")
        return payload["providers"]

    def _save(self) -> None:
        if self._evidence_path is None:
            return
        providers = {
            provider_id: {
                "state": registration.state.value,
                "evidence": (
                    registration.evidence.to_dict() if registration.evidence else None
                ),
            }
            for provider_id, registration in sorted(self._registrations.items())
        }
        self._evidence_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._evidence_path.with_suffix(self._evidence_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"version": 1, "providers": providers}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._evidence_path)

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
        evidence: ProviderAdmissionEvidence | None = None,
        state: ProviderState = ProviderState.CANDIDATE,
        documented_access: bool | None = None,
    ) -> None:
        """Register a candidate without granting admission.

        ``documented_access`` remains accepted only to make legacy callers fail
        closed: its value is deliberately not admission evidence.
        """
        provider_id = self._provider_id(provider)
        if provider_id in self._RETIRED_PROVIDER_IDS or provider_id.startswith("ssi_"):
            raise ProviderNotAllowed(f"retired provider {provider_id!r} cannot be registered")
        persisted = self._persisted.get(provider_id)
        if persisted:
            state = ProviderState(persisted["state"])
            stored_evidence = persisted.get("evidence")
            evidence = (
                ProviderAdmissionEvidence.from_dict(stored_evidence)
                if stored_evidence is not None
                else evidence
            )
        else:
            if state is not ProviderState.CANDIDATE:
                raise InvalidProviderTransition(
                    f"new provider cannot register directly as {state.value}"
                )
            state = ProviderState.CANDIDATE
        self._registrations[provider_id] = ProviderRegistration(provider, state, evidence)
        self._save()

    def transition(
        self,
        provider_id: str,
        to_state: ProviderState,
        *,
        evidence: ProviderAdmissionEvidence,
        as_of: date | None = None,
    ) -> None:
        normalized = provider_id.strip().lower()
        registration = self._registrations.get(normalized)
        if registration is None:
            raise ProviderNotAllowed(f"provider {normalized!r} is not registered")
        if registration.provider.data_mode is not DataMode.REAL:
            raise ProviderNotAllowed("synthetic/test providers are never admission eligible")
        if to_state not in self._TRANSITIONS[registration.state]:
            raise InvalidProviderTransition(
                f"{registration.state.value} -> {to_state.value} is not permitted"
            )
        review_date = as_of or date.today()
        if to_state not in {ProviderState.SUSPENDED, ProviderState.RETIRED}:
            evidence.validate(as_of=review_date, state=to_state)
        self._registrations[normalized] = ProviderRegistration(
            registration.provider, to_state, evidence
        )
        self._save()

    def _is_selectable(self, registration: ProviderRegistration, *, as_of: date) -> bool:
        if (
            registration.state is not ProviderState.ADMITTED
            or registration.provider.data_mode is not DataMode.REAL
            or registration.evidence is None
        ):
            return False
        try:
            registration.evidence.validate(as_of=as_of, state=ProviderState.ADMITTED)
        except InvalidAdmissionEvidence:
            return False
        return True

    def admitted_provider_ids(
        self, capability: str, *, as_of: date | None = None
    ) -> tuple[str, ...]:
        review_date = as_of or date.today()
        return tuple(
            provider_id
            for provider_id, registration in self._registrations.items()
            if self._is_selectable(registration, as_of=review_date)
            and capability in registration.provider.capabilities
        )

    def select(
        self,
        *,
        provider_id: str | None,
        capability: str,
        mode: DataMode = DataMode.REAL,
        as_of: date | None = None,
    ) -> MarketDataProvider:
        review_date = as_of or date.today()
        if mode is DataMode.REAL:
            admitted = self.admitted_provider_ids(capability, as_of=review_date)
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
        if mode is DataMode.REAL and not self._is_selectable(
            registration, as_of=review_date
        ):
            raise NoAdmittedProvider(f"provider {normalized!r} is not validly admitted")
        if capability not in registration.provider.capabilities:
            raise ProviderNotAllowed(
                f"provider {normalized!r} lacks capability {capability!r}"
            )
        return registration.provider


def default_provider_registry() -> ProviderRegistry:
    """Return the registry; no automated provider is admitted by default."""
    return ProviderRegistry()
