from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


class ProviderState(str, Enum):
    CANDIDATE = "CANDIDATE"
    ADMITTED = "ADMITTED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class ProviderRegistration:
    provider: MarketDataProvider
    state: ProviderState
    documented_access: bool


class ProviderRegistry:
    """Explicit provider admission and runtime selection boundary.

    The default registry is deliberately empty. Registration never implies
    admission, and a real-data caller must name an admitted provider.
    """

    _RETIRED_PROVIDER_IDS = frozenset({"ssi", "ssi_fastconnect", "ssi_fastconnect_v3"})

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
        state: ProviderState = ProviderState.CANDIDATE,
        documented_access: bool = False,
    ) -> None:
        provider_id = self._provider_id(provider)
        if provider_id in self._RETIRED_PROVIDER_IDS or provider_id.startswith("ssi_"):
            raise ProviderNotAllowed(f"retired provider {provider_id!r} cannot be registered")
        if state is ProviderState.ADMITTED and not documented_access:
            raise ProviderNotAllowed("an undocumented provider cannot be admitted")
        self._registrations[provider_id] = ProviderRegistration(
            provider=provider,
            state=state,
            documented_access=documented_access,
        )

    def admitted_provider_ids(self, capability: str) -> tuple[str, ...]:
        return tuple(
            provider_id
            for provider_id, registration in self._registrations.items()
            if registration.state is ProviderState.ADMITTED
            and registration.documented_access
            and registration.provider.data_mode is DataMode.REAL
            and capability in registration.provider.capabilities
        )

    def registration(self, provider_id: str) -> ProviderRegistration:
        """Expose immutable governance metadata without deriving state from I/O."""
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


def default_provider_registry() -> ProviderRegistry:
    """Return implemented providers in policy-safe, non-admitted states."""
    from .providers import CafeFReferenceProvider, DNSEProvider, VietstockDataFeedProvider

    registry = ProviderRegistry()
    registry.register(DNSEProvider(), state=ProviderState.CANDIDATE, documented_access=True)
    registry.register(
        VietstockDataFeedProvider(),
        state=ProviderState.CANDIDATE,
        documented_access=False,
    )
    registry.register(
        CafeFReferenceProvider(),
        state=ProviderState.RESEARCH_ONLY,
        documented_access=False,
    )
    return registry
