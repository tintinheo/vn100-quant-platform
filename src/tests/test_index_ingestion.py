from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path

import pandas as pd

from vnquant.data.models import IndexBar, RawSnapshot
from vnquant.data.storage import Warehouse
from vnquant.jobs.pipeline import _official_cap_index


NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_app_never_describes_equal_weight_leg_as_cap_index_substitute():
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    assert "uses an equal-weight proxy" not in app_source
    assert "Official cap-index input unavailable" in app_source
    assert "Bull regime classification is disabled" in app_source


def test_canonical_index_storage_retains_raw_lineage_and_turnover(tmp_path):
    payload = b"official index response"
    snapshot = RawSnapshot("ix-1", "official-test", NOW, payload,
                           hashlib.sha256(payload).hexdigest(), source_reference="unknown")
    warehouse = Warehouse(tmp_path)
    warehouse.store_raw_snapshot(snapshot)
    warehouse.append_index_bars([IndexBar(
        NOW, "VNINDEX", Decimal("1000"), Decimal("1010"), Decimal("990"),
        Decimal("1005"), Decimal("123456789"), "official-test", NOW, (), "ix-1",
        payload_sha256=snapshot.payload_sha256,
    )])
    stored = warehouse.read_table("index_bars").iloc[0]
    assert stored.turnover == Decimal("123456789")
    assert stored.raw_snapshot_id == "ix-1"
    assert stored.payload_sha256 == snapshot.payload_sha256


def test_absent_or_stale_official_index_exposes_degraded_non_bull_input(tmp_path):
    unavailable, mode, warning = _official_cap_index(Warehouse(tmp_path), date(2026, 9, 14))
    assert unavailable[["close", "ma50", "ma200"]].isna().all()
    assert mode == "DEGRADED_PROXY_UNAVAILABLE"
    assert "absent" in warning

    warehouse = Warehouse(tmp_path)
    payload = b"stale official index response"
    snapshot = RawSnapshot("ix-stale", "official-test", NOW, payload,
                           hashlib.sha256(payload).hexdigest(), source_reference="unknown")
    warehouse.store_raw_snapshot(snapshot)
    warehouse.append_index_bars([IndexBar(
        datetime(2026, 9, 11, tzinfo=timezone.utc), "VNINDEX", Decimal("990"),
        Decimal("1010"), Decimal("980"), Decimal("1000"), Decimal("10"),
        "official-test", NOW, (), snapshot.snapshot_id,
        payload_sha256=snapshot.payload_sha256,
    )])
    unavailable, mode, warning = _official_cap_index(warehouse, date(2026, 9, 14))
    assert unavailable.isna().all()
    assert mode == "DEGRADED_PROXY_STALE"
    assert "missing" in warning


def test_cap_index_rejects_canonical_rows_without_verifiable_raw_lineage(tmp_path):
    (tmp_path / "parquet").mkdir()
    pd.DataFrame([{
        "index_code": "VNINDEX", "timestamp": NOW, "close": 1000, "turnover": 10,
        "provider": "official-test", "raw_snapshot_id": "missing",
        "payload_sha256": "missing", "source_reference": "test://missing",
    }]).to_parquet(tmp_path / "parquet" / "index_bars.parquet", index=False)

    unavailable, mode, warning = _official_cap_index(Warehouse(tmp_path), NOW.date())

    assert unavailable.isna().all()
    assert mode == "DEGRADED_PROXY_UNAVAILABLE"
    assert "raw-lineaged" in warning


def test_fresh_vn100_is_accepted_when_vnindex_is_stale(tmp_path):
    warehouse = Warehouse(tmp_path)
    bars = []
    for code, timestamp in (("VNINDEX", datetime(2026, 9, 11, tzinfo=timezone.utc)),
                            ("VN100", NOW)):
        payload = f"{code} official response".encode()
        snapshot = RawSnapshot(f"ix-{code}", "official-test", NOW, payload,
                               hashlib.sha256(payload).hexdigest(), source_reference="unknown")
        warehouse.store_raw_snapshot(snapshot)
        bars.append(IndexBar(timestamp, code, Decimal("990"), Decimal("1010"),
                    Decimal("980"), Decimal("1000"), Decimal("10"), "official-test",
                    NOW, (), snapshot.snapshot_id, payload_sha256=snapshot.payload_sha256))
    warehouse.append_index_bars(bars)

    row, mode, warning = _official_cap_index(warehouse, NOW.date())

    assert row.close == Decimal("1000")
    assert mode == "OFFICIAL_VN100"
    assert warning is None
