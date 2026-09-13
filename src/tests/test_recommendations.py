import pandas as pd
from vnquant.market.regime import Regime
from vnquant.recommendations.engine import detect_candidates

def test_panic_bear_emits_no_candidates():
    latest=pd.DataFrame([{"symbol":"AAA","trading_date":"2026-01-01","sector":"BANK","rs_stock_market_rank_126":99,"rs_stock_market_rank_20":1,"signal_pullback":True}])
    sectors=pd.DataFrame([{"sector":"BANK","leadership_score":90}])
    assert detect_candidates(latest,Regime.PANIC_BEAR,sectors).empty

def test_pullback_family_can_fire():
    latest=pd.DataFrame([{"symbol":"AAA","trading_date":"2026-01-01","sector":"BANK","rs_stock_market_rank_126":80,"rs_stock_market_rank_20":20,"signal_pullback":True,"setup_quality":0.8,"volume_confirmation":0.4}])
    sectors=pd.DataFrame([{"sector":"BANK","leadership_score":80}])
    out=detect_candidates(latest,Regime.RANGE,sectors)
    assert len(out)==1 and out.iloc[0].family=="TREND_PULLBACK"
