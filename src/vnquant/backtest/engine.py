from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd
from .execution import simulate_buy_limit, simulate_urgent_sell, ExecutionMode
from vnquant.market.rules import BrokerCostProfile
from vnquant.market.settlement import regulatory_sellable_date, eod_policy_earliest_exit_fill_date
from vnquant.config import parameter_value

@dataclass
class Trade:
    symbol:str; signal_date:object; entry_date:object; entry_price:float
    regulatory_sellable_date:object; policy_earliest_exit_date:object
    exit_date:object|None=None; exit_price:float|None=None; net_return:float|None=None; exit_reason:str|None=None

@dataclass
class Attempt:
    symbol:str; signal_date:object; status:str; reason:str
    entry_date:object|None=None; entry_price:float|None=None; overnight_gap:float|None=None


def backtest_pullback_with_audit(df:pd.DataFrame, costs:BrokerCostProfile, *, hold_sessions:int|None=None,
                                 premium:float|None=None,max_gap:float|None=None,
                                 mode:ExecutionMode=ExecutionMode.CONSERVATIVE)->tuple[pd.DataFrame,pd.DataFrame]:
    hold_sessions = int(hold_sessions if hold_sessions is not None else parameter_value("backtest.hold_sessions"))
    premium = float(premium if premium is not None else parameter_value("backtest.entry_premium"))
    max_gap = float(max_gap if max_gap is not None else parameter_value("backtest.maximum_gap"))
    d=df.sort_values("trading_date").reset_index(drop=True).copy(); sessions=d.trading_date.tolist(); trades=[]; attempts=[]; i=0
    while i < len(d)-4:
        if not bool(d.loc[i].get("signal_pullback",False)): i+=1; continue
        n=d.loc[i+1]; gap=float(n.open)/float(d.loc[i].close)-1
        fill=simulate_buy_limit(float(d.loc[i].close),float(n.open),float(n.high),float(n.low),premium=premium,max_gap=max_gap,mode=mode)
        if not fill.filled:
            attempts.append(asdict(Attempt(str(d.loc[i].symbol),sessions[i],"REJECTED",fill.reason,overnight_gap=gap)))
            i+=1; continue
        entry_idx=i+1; entry_date=sessions[entry_idx]
        attempts.append(asdict(Attempt(str(d.loc[i].symbol),sessions[i],"FILLED",fill.reason,entry_date,float(fill.price),gap)))
        try:
            sellable=regulatory_sellable_date(entry_date,sessions); policy=eod_policy_earliest_exit_fill_date(entry_date,sessions)
        except (ValueError,IndexError): break
        t=Trade(str(d.loc[i].symbol),sessions[i],entry_date,float(fill.price),sellable,policy)
        exit_signal_idx=min(entry_idx+hold_sessions,len(d)-2)
        policy_idx=sessions.index(policy)
        exit_signal_idx=max(exit_signal_idx,policy_idx-1)
        j=min(exit_signal_idx+1,len(d)-1)
        sold=simulate_urgent_sell(float(d.loc[j-1].close),float(d.loc[j].open),float(d.loc[j].high),float(d.loc[j].low),mode=mode)
        while not sold.filled and j < len(d)-1:
            j+=1; sold=simulate_urgent_sell(float(d.loc[j-1].close),float(d.loc[j].open),float(d.loc[j].high),float(d.loc[j].low),mode=mode)
        if sold.filled:
            gross=float(sold.price)/t.entry_price-1
            t.exit_date=sessions[j]; t.exit_price=float(sold.price); t.exit_reason="time_stop"
            t.net_return=(1-costs.sell_cost_rate())*(1+gross)/(1+costs.buy_cost_rate())-1
        trades.append(t); i=max(i+1,j)
    return pd.DataFrame([asdict(t) for t in trades]), pd.DataFrame(attempts)


def backtest_pullback(df:pd.DataFrame, costs:BrokerCostProfile, **kwargs)->pd.DataFrame:
    trades,_=backtest_pullback_with_audit(df,costs,**kwargs)
    return trades
