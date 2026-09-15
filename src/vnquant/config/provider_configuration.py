"""Strict loader for versioned provider policy and admission records."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml


@dataclass(frozen=True)
class ProviderConfiguration:
    provider_id: str
    config_version: str
    enabled: bool
    role: str
    state: str
    adapter: str
    credentials: dict[str, str]
    evidence: dict[str, Any]
    disabled_reason: str = ""


@lru_cache(maxsize=1)
def _document() -> dict[str, Any]:
    path = files("vnquant.config").joinpath("providers.v1.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported provider configuration schema_version")
    if not str(document.get("config_version", "")).strip():
        raise ValueError("provider config_version is required")
    return document


def provider_configurations() -> tuple[ProviderConfiguration, ...]:
    document = _document()
    records = []
    for provider_id, value in document.get("providers", {}).items():
        evidence = dict(value.get("evidence", {}))
        if not str(evidence.get("record_version", "")).strip():
            raise ValueError(f"{provider_id}: admission evidence record_version is required")
        records.append(
            ProviderConfiguration(
                provider_id=str(provider_id),
                config_version=str(document["config_version"]),
                enabled=value.get("enabled") is True,
                role=str(value.get("role", "")),
                state=str(value.get("state", "")),
                adapter=str(value.get("adapter", "")),
                credentials=dict(value.get("credentials", {})),
                evidence=evidence,
                disabled_reason=str(value.get("disabled_reason", "")),
            )
        )
    return tuple(records)
