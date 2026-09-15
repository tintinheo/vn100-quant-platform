from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib

import pandas as pd
import pytest

from vnquant.data.models import CanonicalBar, RawSnapshot
from vnquant.data.schema import validate_canonical_bars
from vnquant.data.storage import Warehouse

NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def test_raw_snapshot_is_content_verified_and_read_only(tmp_path):
    payload = b"unaltered payload"
    snapshot = RawSnapshot("s1", "manual", NOW, payload, hashlib.sha256(payload).hexdigest())
    path = Warehouse(tmp_path).store_raw_snapshot(snapshot)
    assert path.read_bytes() == payload
    assert path.stat().st_mode & 0o222 == 0
    changed = RawSnapshot("s1", "manual", NOW, b"changed", hashlib.sha256(b"changed").hexdigest())
    # A lineage identifier names exactly one immutable payload.
    with pytest.raises(RuntimeError, match="already identifies different payload"):
        Warehouse(tmp_path).store_raw_snapshot(changed)
    assert path.read_bytes() == payload


def test_duplicate_bars_are_detected():
    bar = _bar("p1", "s1")
    assert any(result.code == "DUPLICATE_BAR" for result in validate_canonical_bars([bar, bar]))


def test_provider_disagreement_is_recorded_and_not_averaged():
    first = _bar("p1", "s1", close="10")
    second = _bar("p2", "s2", close="12")
    results = validate_canonical_bars([first, second])
    disagreement = next(result for result in results if result.code == "PROVIDER_DISAGREEMENT")
    assert disagreement.raw_snapshot_ids == ("s1", "s2")
    assert first.close == Decimal("10") and second.close == Decimal("12")


def test_missing_sessions_are_reported_without_forward_fill():
    missing = NOW + timedelta(days=1)
    bars = [_bar("p1", "s1")]
    results = validate_canonical_bars(bars, expected_sessions={NOW, missing})
    assert ("MISSING_SESSION", missing) in [(result.code, result.timestamp) for result in results]
    assert len(bars) == 1


def test_storage_requires_raw_lineage_and_rejects_existing_duplicate(tmp_path):
    wh = Warehouse(tmp_path)
    bar = _bar("p1", "s1")
    with pytest.raises(ValueError, match="unknown raw_snapshot_id"):
        wh.append_canonical_bars([bar])
    payload = b"raw"
    wh.store_raw_snapshot(RawSnapshot("s1", "p1", NOW, payload, hashlib.sha256(payload).hexdigest()))
    wh.append_canonical_bars([bar])
    stored = pd.read_parquet(tmp_path / "parquet" / "canonical_bars.parquet")
    assert stored.loc[0, "raw_snapshot_id"] == "s1"
    assert stored.loc[0, "canonical_revision"]
    with pytest.raises(ValueError, match="DUPLICATE_BAR"):
        wh.append_canonical_bars([bar])


def test_storage_persists_provider_disagreement_in_quality_table(tmp_path):
    wh = Warehouse(tmp_path)
    for provider, snapshot_id in (("p1", "s1"), ("p2", "s2")):
        payload = provider.encode()
        wh.store_raw_snapshot(RawSnapshot(snapshot_id, provider, NOW, payload,
                                           hashlib.sha256(payload).hexdigest()))
    wh.append_canonical_bars([_bar("p1", "s1", "10"), _bar("p2", "s2", "12")])
    bars = pd.read_parquet(tmp_path / "parquet" / "canonical_bars.parquet")
    quality = pd.read_parquet(tmp_path / "parquet" / "data_quality_results.parquet")
    assert bars.close.tolist() == [Decimal("10"), Decimal("12")]
    assert "PROVIDER_DISAGREEMENT" in quality.code.tolist()


def _bar(provider, snapshot, close="10"):
    return CanonicalBar(NOW, "AAA", Decimal("10"), Decimal("12"), Decimal("9"),
                        Decimal(close), 100, Decimal("1000"), Decimal("9"),
                        provider, NOW, (), snapshot)


def test_reference_records_require_existing_source_snapshot(tmp_path):
    from datetime import date
    from vnquant.data.models import SectorMembership, UniverseMembership

    warehouse = Warehouse(tmp_path)
    universe = UniverseMembership("VN100", "AAA", date(2026, 9, 14), None, "official", "missing")
    sector = SectorMembership("AAA", "10", "Banks", "ICB", date(2026, 9, 14), None,
                              "official", "missing")
    with pytest.raises(ValueError, match="raw_snapshot_id"):
        warehouse.write_records("universe_current", [universe])
    with pytest.raises(ValueError, match="raw_snapshot_id"):
        warehouse.write_records("sector_membership", [sector])


def test_raw_snapshot_id_cannot_be_reused_for_different_file(tmp_path):
    warehouse = Warehouse(tmp_path)
    first = b"first"
    second = b"second"
    warehouse.store_raw_snapshot(RawSnapshot("same", "manual", NOW, first,
                                             hashlib.sha256(first).hexdigest()))
    with pytest.raises(RuntimeError, match="already identifies different payload"):
        warehouse.store_raw_snapshot(RawSnapshot("same", "manual", NOW, second,
                                                 hashlib.sha256(second).hexdigest()))
