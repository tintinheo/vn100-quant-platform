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

def test_concentrated_large_cap_leadership_is_not_misread_as_broad_bull():
    cap={"close":130,"ma50":115,"ma200":100}
    equal_weight={"close":101,"ma50":100,"ma200":102}
    breadth={"pct_ma50":0.50,"ad_slope_10":-2,"turnover_ratio":1.1}
    result=compute_regime(cap,equal_weight,breadth)
    assert result.cap_score == 3
    assert result.ew_score == 1
    assert result.regime == Regime.RANGE

def test_broad_market_participation_can_confirm_strong_bull():
    cap={"close":130,"ma50":115,"ma200":100}
    equal_weight={"close":125,"ma50":112,"ma200":101}
    breadth={"pct_ma50":0.75,"ad_slope_10":8,"turnover_ratio":1.1}
    result=compute_regime(cap,equal_weight,breadth)
    assert result.cap_score == result.ew_score == 3
    assert result.regime == Regime.STRONG_BULL
