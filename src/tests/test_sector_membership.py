import pandas as pd
from vnquant.data.sector_membership import apply_sector_mapping, SectorMode

def test_current_icb_is_explicit_proxy():
    panel=pd.DataFrame([{"symbol":"AAA","trading_date":"2020-01-01","close":1}])
    master=pd.DataFrame([{"symbol":"AAA","icb_name":"Banks"}])
    r=apply_sector_mapping(panel,current_master=master)
    assert r.mode is SectorMode.CURRENT_ICB_PROXY
    assert r.panel.iloc[0].sector=="Banks"
    assert "NOT_TRUE_HISTORICAL" in r.warning

def test_pit_taxonomy_propagates_lineage(tmp_path):
    path=tmp_path/"sectors.csv"
    pd.DataFrame([{"symbol":"AAA","sector_code":"10","sector_name":"Banks",
        "taxonomy_version":"ICB-2020","effective_from":"2020-01-01","effective_to":"",
        "source":"official","source_snapshot_id":"snap-1"}]).to_csv(path,index=False)
    panel=pd.DataFrame([{"symbol":"AAA","trading_date":"2020-02-01","close":1}])
    r=apply_sector_mapping(panel,pit_path=path)
    assert r.mode is SectorMode.STRICT_PIT
    assert r.panel.iloc[0].sector_source_snapshot_id == "snap-1"
