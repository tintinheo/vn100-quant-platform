from vnquant.market.rules import BrokerCostProfile, round_down_hose

def test_no_exchange_double_count_when_included():
    c=BrokerCostProfile(0.0015,True,0.00027,0.001,0)
    assert abs(c.buy_cost_rate()-0.0015)<1e-12
    assert abs(c.sell_cost_rate()-0.0025)<1e-12

def test_exchange_fee_added_when_not_included():
    c=BrokerCostProfile(0.0015,False,0.00027,0.001,0)
    assert abs(c.buy_cost_rate()-0.00177)<1e-12

def test_round_down_never_bids_above_intent():
    for p in [9999,10001,49999,50001,123456]: assert round_down_hose(p)<=p
