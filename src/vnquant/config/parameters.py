"""Loader for the governed quantitative-parameter registry."""
from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    path = files("vnquant.config").joinpath("quant_parameters.v1.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported quantitative parameter schema_version")
    for name, record in document.get("parameters", {}).items():
        classification = str(record.get("classification", ""))
        requirement = str(record.get("requirement", ""))
        if classification not in {"[S]", "[M]", "[A]", "[D] [GUESS]"}:
            raise ValueError(f"{name}: invalid parameter classification {classification!r}")
        if classification == "[D] [GUESS]" and "[GUESS]" not in requirement:
            raise ValueError(f"{name}: unverified default must state a literal [GUESS] requirement")
    return document


def parameters_version() -> str:
    return str(_registry()["config_version"])


def parameter_record(name: str) -> dict[str, Any]:
    """Return a copy so callers cannot mutate the process-wide registry."""
    try:
        return dict(_registry()["parameters"][name])
    except KeyError as error:
        raise KeyError(f"unknown governed parameter: {name}") from error


def parameter_value(name: str) -> Any:
    return parameter_record(name)["value"]
