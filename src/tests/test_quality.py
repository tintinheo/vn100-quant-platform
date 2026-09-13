import pandas as pd
from datetime import date
from vnquant.data.quality import validate_bars

def test_bad_ohlc_is_blocked():
    df=pd.DataFrame([{"symbol":"X","trading_date":date(2026,1,1),"open":10,"high":9,"low":8,"close":10,"volume":1,"provider":"x"}])
    assert any(x.code=="OHLC_LOGIC" and x.severity=="ERROR" for x in validate_bars(df))
