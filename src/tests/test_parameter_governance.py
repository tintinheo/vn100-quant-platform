from __future__ import annotations

from importlib.resources import files

import yaml

from vnquant.config import parameter_record, parameters_version
from vnquant.data.quality import ACTIONABLE_BLOCK_THRESHOLD, CONFIDENCE_CAP_THRESHOLD


def test_versioned_registry_classifies_every_parameter_and_explains_guesses():
    path = files("vnquant.config").joinpath("quant_parameters.v1.yaml")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert document["schema_version"] == 1
    assert parameters_version().startswith("quant-parameters-v1-")
    assert document["parameters"]
    for record in document["parameters"].values():
        assert record["classification"] in {"[S]", "[M]", "[A]", "[D] [GUESS]"}
        assert record["requirement"]
        if record["classification"] == "[D] [GUESS]":
            assert "[GUESS]" in record["requirement"]


def test_dq_policy_uses_governed_brd_defaults():
    assert CONFIDENCE_CAP_THRESHOLD == parameter_record("dq.confidence_cap")["value"]
    assert ACTIONABLE_BLOCK_THRESHOLD == parameter_record("dq.actionable_block")["value"]
