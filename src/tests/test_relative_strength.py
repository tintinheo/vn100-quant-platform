import pandas as pd
from vnquant.features.relative_strength import add_cross_sectional_rs

def test_three_way_relative_strength_columns_exist():
    rows=[]
    for i in range(130):
        for sym,sector,g in [("AAA","BANK",1.002),("BBB","BANK",1.001),("CCC","TECH",1.003)]:
            rows.append({"symbol":sym,"sector":sector,"trading_date":pd.Timestamp("2025-01-01")+pd.Timedelta(days=i),"close":100*(g**i)})
    out=add_cross_sectional_rs(pd.DataFrame(rows),(20,126))
    for c in ["rs_stock_market_20","rs_stock_sector_20","rs_sector_market_20","rs_stock_market_rank_126"]:
        assert c in out
