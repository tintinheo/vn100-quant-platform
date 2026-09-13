import pandas as pd
from vnquant.backtest.engine import backtest_pullback_with_audit
from vnquant.backtest.execution import ExecutionMode
from vnquant.market.rules import BrokerCostProfile

def test_backtest_audits_rejected_gap_signal():
    dates=pd.bdate_range('2026-01-01',periods=8).date
    df=pd.DataFrame({
        'symbol':['AAA']*8,'trading_date':dates,'open':[100,105,105,105,105,105,105,105],
        'high':[101,106,106,106,106,106,106,106],'low':[99,104,104,104,104,104,104,104],
        'close':[100,105,105,105,105,105,105,105],'volume':[1000]*8,
        'signal_pullback':[True,False,False,False,False,False,False,False]
    })
    costs=BrokerCostProfile(commission_rate=0)
    tr,a=backtest_pullback_with_audit(df,costs,max_gap=0.02,mode=ExecutionMode.CONSERVATIVE)
    assert tr.empty
    assert len(a)==1 and a.iloc[0].reason=='gap_gate'
