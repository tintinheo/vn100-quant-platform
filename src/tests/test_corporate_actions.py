import pandas as pd
from vnquant.data.corporate_actions import detect_adjustment_factor_jumps

def test_adjustment_jump_does_not_infer_action_type():
    raw=pd.Series([100,100,100]); adj=pd.Series([100,90,90]); dates=pd.Series(pd.to_datetime(["2026-01-01","2026-01-02","2026-01-03"]))
    x=detect_adjustment_factor_jumps("X",raw,adj,dates)
    assert len(x)==1 and "UNKNOWN" in x[0].note
