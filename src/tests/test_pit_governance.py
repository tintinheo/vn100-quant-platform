from datetime import date

import pytest

from vnquant.backtest.governance import govern_backtest_result
from vnquant.data.models import SectorMembership
from vnquant.data.official_evidence import ingest_vn100_review
from vnquant.data.sector_membership import SectorMode
from vnquant.data.sector_taxonomy import SectorTaxonomyStore
from vnquant.data.storage import Warehouse
from vnquant.data.universe import UniverseMode, UniverseStore


def test_official_review_ingestion_preserves_snapshot_lineage(tmp_path):
    warehouse = Warehouse(tmp_path / "warehouse")
    store = UniverseStore(tmp_path / "universe.csv")
    result = ingest_vn100_review(
        b"symbol,index_code\nAAA,VN100\nBBB,VN100\nCCC,VN30\n",
        source_reference="https://www.hsx.vn/official-review.pdf",
        effective_from=date(2020, 2, 3), universe_store=store, warehouse=warehouse,
    )
    resolved = store.resolve(date(2020, 3, 1))
    assert resolved.symbols == ("AAA", "BBB")
    assert resolved.source_snapshot_ids == (result.snapshot_id,)
    assert result.evidence_path.read_bytes().startswith(b"symbol,index_code")


def test_effective_dated_sector_taxonomy_has_required_lineage(tmp_path):
    store = SectorTaxonomyStore(tmp_path / "sectors.csv")
    store.append([
        SectorMembership("AAA", "10", "Banks", "ICB-2020", date(2020, 1, 1),
                         date(2020, 12, 31), "official-taxonomy", "sector-snap-1"),
        SectorMembership("AAA", "20", "Technology", "ICB-2020", date(2021, 1, 1),
                         None, "official-taxonomy", "sector-snap-2"),
    ])
    record = store.resolve("AAA", date(2021, 6, 1), "ICB-2020")
    assert (record.sector_code, record.sector_name, record.source_snapshot_id) == (
        "20", "Technology", "sector-snap-2")


def test_proxy_runs_cannot_claim_historical_vn100_or_qualify_capital():
    with pytest.raises(ValueError, match="requires STRICT_PIT"):
        govern_backtest_result("Historical VN100 backtest", UniverseMode.CURRENT_UNIVERSE_PROXY,
                               SectorMode.CURRENT_ICB_PROXY)
    governed = govern_backtest_result("Exploratory backtest", UniverseMode.CURRENT_UNIVERSE_PROXY,
                                      SectorMode.CURRENT_ICB_PROXY)
    assert not governed.capital_qualification_eligible
    assert "NOT_ELIGIBLE_FOR_REAL_CAPITAL_STRATEGY_QUALIFICATION" in governed.warnings


def test_only_strict_universe_and_sector_are_capital_qualification_eligible():
    governed = govern_backtest_result("Historical VN100 backtest", UniverseMode.STRICT_PIT,
                                      SectorMode.STRICT_PIT)
    assert governed.capital_qualification_eligible
    assert not governed.warnings
