"""Versioned provider-origin evidence used to prove source independence."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

import yaml


@dataclass(frozen=True)
class ProviderOriginEvidence:
    provider_id: str
    origin_id: str
    independence_verified: bool
    evidence_reference: str


@lru_cache(maxsize=1)
def provider_origin_evidence() -> tuple[ProviderOriginEvidence, ...]:
    path = files("vnquant.config").joinpath("provider_origins.v1.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported provider-origin schema_version")
    if not str(document.get("config_version", "")).strip():
        raise ValueError("provider-origin config_version is required")
    records = []
    for provider_id, value in document.get("providers", {}).items():
        records.append(ProviderOriginEvidence(
            provider_id=str(provider_id),
            origin_id=str(value.get("origin_id", "")).strip(),
            independence_verified=value.get("independence_verified") is True,
            evidence_reference=str(value.get("evidence_reference", "")).strip(),
        ))
    return tuple(records)


def verified_provider_origins() -> dict[str, str]:
    """Return only origin IDs backed by explicit independence evidence."""
    return {
        record.provider_id: record.origin_id
        for record in provider_origin_evidence()
        if record.independence_verified and record.origin_id and record.evidence_reference
    }
