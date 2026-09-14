from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib

import pytest

from vnquant.data.models import (
    CanonicalBar, CorporateAction, IndexBar, RawSnapshot,
    SectorMembership, UniverseMembership,
)
from vnquant.data.schema import CANONICAL_BAR_FIELDS, assert_canonical_bar_schema

UTC = timezone.utc
NOW = datetime(2026, 9, 13, tzinfo=UTC)


def test_canonical_daily_bar_schema_is_stable_and_keeps_lineage():
    assert_canonical_bar_schema()
    assert CANONICAL_BAR_FIELDS[:12] == (
        "timestamp", "symbol", "open", "high", "low", "close", "volume",
        "turnover", "adj_close", "provider", "ingested_at", "quality_flags",
    )
    assert "raw_snapshot_id" in CANONICAL_BAR_FIELDS
    assert CANONICAL_BAR_FIELDS[-1] == "payload_sha256"


def test_raw_and_adjusted_prices_are_distinct_fields():
    bar = _bar(open="100", high="101", low="99", close="100", adj_close="80")
    assert bar.close == Decimal("100")
    assert bar.adj_close == Decimal("80")


def test_models_are_immutable_and_effective_dated_models_have_lineage():
    raw = b"provider evidence"
    snapshot = RawSnapshot("snap-1", "manual", NOW, raw, hashlib.sha256(raw).hexdigest())
    with pytest.raises(FrozenInstanceError):
        snapshot.provider = "changed"
    universe = UniverseMembership("VN100", "AAA", date(2026, 1, 1), None, "HOSE", "snap-1")
    sector = SectorMembership("AAA", "10", "Banks", "ICB", date(2026, 1, 1), None, "official", "snap-1")
    assert universe.source_snapshot_id == sector.source_snapshot_id == "snap-1"


def test_ohlc_inconsistency_is_rejected_for_security_and_index_bars():
    with pytest.raises(ValueError, match="OHLC"):
        _bar(high="9")
    with pytest.raises(ValueError, match="OHLC"):
        IndexBar(NOW, "VNINDEX", Decimal("10"), Decimal("9"), Decimal("8"),
                 Decimal("10"), None, "manual", NOW, (), "snap-1")


def test_corporate_action_requires_official_lineage_not_an_inferred_type():
    with pytest.raises(ValueError, match="lineage"):
        CorporateAction("AAA", date(2026, 1, 1), "UNKNOWN", "ratio", "")


def _bar(**changes):
    values = dict(timestamp=NOW, symbol="AAA", open=Decimal("10"),
                  high=Decimal("11"), low=Decimal("9"), close=Decimal("10"),
                  volume=100, turnover=Decimal("1000"), adj_close=Decimal("9"),
                  provider="manual", ingested_at=NOW, quality_flags=(),
                  raw_snapshot_id="snap-1")
    for key, value in changes.items():
        values[key] = Decimal(value) if key in {"open", "high", "low", "close", "adj_close"} else value
    return CanonicalBar(**values)
