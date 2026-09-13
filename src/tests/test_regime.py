from vnquant.market.regime import compute_regime, Regime

def test_missing_turnover_cannot_confirm_bull():
    ix={"close":120,"ma50":110,"ma200":100}
    breadth={"pct_ma50":0.80,"ad_slope_10":10,"turnover_ratio":None}
    r=compute_regime(ix,ix,breadth)
    assert r.regime == Regime.RANGE

def test_strong_bull_requires_turnover():
    ix={"close":120,"ma50":110,"ma200":100}
    breadth={"pct_ma50":0.80,"ad_slope_10":10,"turnover_ratio":1.2}
    assert compute_regime(ix,ix,breadth).regime == Regime.STRONG_BULL
