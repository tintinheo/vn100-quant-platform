from datetime import date
import hashlib
import json

import pandas as pd

from vnquant.data.csv_provider import CSVProvider
from vnquant.data.provider_registry import (
    AdmissionEvidence, ProviderRegistry, ProviderState, ValidationResult,
)
from vnquant.jobs.bootstrap import run


def _registry(provider):
    evidence = AdmissionEvidence(
        access_basis="authorized test files", licence_reference="TEST",
        capability_definitions={"daily_ohlcv": "bars", "current_index_members": "members"},
        schema_and_units="fixture schema in VND", timezone_date_semantics="UTC test dates",
        raw_adjusted_policy="raw", revision_behavior="immutable files", quotas="local",
        lineage_method="SHA-256", owner="tests", reviewed_at=date(2026, 9, 14),
        next_review_at=date(2027, 9, 14), validation_results=(
            ValidationResult("doctor", True, "test", date(2026, 9, 14)),
            ValidationResult("cross_validation", True, "test", date(2026, 9, 14)),
        ))
    registry = ProviderRegistry()
    registry.register(provider, evidence=evidence)
    for state in (ProviderState.DOCTOR_PASSED, ProviderState.CROSS_VALIDATED,
                  ProviderState.ADMITTED):
        registry.transition(provider.provider_id, state)
    return registry


def test_csv_bootstrap_snapshots_exact_files_before_canonical_write(tmp_path, monkeypatch):
    monkeypatch.setattr("vnquant.data.storage.Warehouse.build_duckdb_views", lambda self: None)
    source, warehouse = tmp_path / "input", tmp_path / "warehouse"
    source.mkdir()
    universe = b"symbol\nAAA\n"
    prices = (b"trading_date,open,high,low,close,volume,value\n"
              b"2026-09-14,10,11,9,10.5,100,1050\n")
    (source / "vn100_universe.csv").write_bytes(universe)
    (source / "AAA.csv").write_bytes(prices)

    provider = CSVProvider(source)
    assert run(provider_id=provider.provider_id, start=date(2026, 9, 14),
               end=date(2026, 9, 14), data_dir=str(warehouse),
               registry=_registry(provider)) == 0

    raw_files = list((warehouse / "raw" / provider.provider_id).glob("*.bin"))
    assert {path.read_bytes() for path in raw_files} == {universe, prices}
    bars = pd.read_parquet(warehouse / "parquet" / "canonical_bars.parquet")
    assert bars.loc[0, "payload_sha256"] == hashlib.sha256(prices).hexdigest()
    assert bars.loc[0, "raw_price_unit"] == "file_declared_or_VND_[GUESS]"
    assert json.loads(bars.loc[0, "request_parameters"])["symbol"] == "AAA"
    metadata = json.loads(next(path for path in
        (warehouse / "raw" / provider.provider_id).glob("*.bin.json")
        if json.loads(path.read_text())["raw_price_unit"] != "not_applicable").read_text())
    assert metadata["payload_sha256"] == hashlib.sha256(prices).hexdigest()


def test_csv_fetch_does_not_normalize_or_mutate_raw_bytes(tmp_path):
    payload = b"trading_date,open,high,low,close,volume\r\n2026-09-14,1,1,1,1,1\r\n"
    (tmp_path / "AAA.csv").write_bytes(payload)
    fetched = CSVProvider(tmp_path).fetch_daily_history(
        "AAA", date(2026, 9, 14), date(2026, 9, 14))
    assert fetched.payload == payload
    assert hashlib.sha256(fetched.payload).hexdigest() == hashlib.sha256(payload).hexdigest()
