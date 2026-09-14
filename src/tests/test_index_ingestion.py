from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib

import pandas as pd

from vnquant.data.models import IndexBar, RawSnapshot
from vnquant.data.storage import Warehouse
from vnquant.jobs.pipeline import _official_cap_index


NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_canonical_index_storage_retains_raw_lineage_and_turnover(tmp_path):
    payload = b"official index response"
    snapshot = RawSnapshot("ix-1", "official-test", NOW, payload,
                           hashlib.sha256(payload).hexdigest())
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

    pd.DataFrame([{
        "index_code": "VNINDEX", "timestamp": datetime(2026, 9, 11, tzinfo=timezone.utc),
        "close": 1000, "turnover": 10,
    }]).to_parquet(tmp_path / "parquet" / "index_bars.parquet", index=False)
    unavailable, mode, warning = _official_cap_index(Warehouse(tmp_path), date(2026, 9, 14))
    assert unavailable.isna().all()
    assert mode == "DEGRADED_PROXY_STALE"
    assert "stale" in warning
