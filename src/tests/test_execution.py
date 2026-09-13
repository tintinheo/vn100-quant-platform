import inspect
from vnquant.backtest.execution import simulate_buy_limit,ExecutionMode

def test_entry_signature_cannot_accept_same_session_entry_price():
    p=set(inspect.signature(simulate_buy_limit).parameters)
    assert {"next_open","next_high","next_low"}<=p
    assert "entry_price" not in p

def test_exact_touch_is_not_proven_fill_conservative():
    r=simulate_buy_limit(10000,10100,10200,10050,premium=.005,max_gap=.02,mode=ExecutionMode.CONSERVATIVE)
    assert not r.filled

def test_trade_through_fills():
    r=simulate_buy_limit(10000,10100,10200,10040,premium=.005,max_gap=.02,mode=ExecutionMode.CONSERVATIVE)
    assert r.filled
