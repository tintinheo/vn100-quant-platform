import pandas as pd
from vnquant.data.sector_membership import apply_sector_mapping, SectorMode

def test_current_icb_is_explicit_proxy():
    panel=pd.DataFrame([{"symbol":"AAA","trading_date":"2020-01-01","close":1}])
    master=pd.DataFrame([{"symbol":"AAA","icb_name":"Banks"}])
    r=apply_sector_mapping(panel,current_master=master)
    assert r.mode is SectorMode.CURRENT_ICB_PROXY
    assert r.panel.iloc[0].sector=="Banks"
    assert "NOT_TRUE_HISTORICAL" in r.warning
