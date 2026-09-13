from __future__ import annotations
from datetime import date

def add_trading_sessions(entry_date:date, sessions:list[date], n:int)->date:
    ordered=sorted(sessions); i=ordered.index(entry_date); return ordered[i+n]

def regulatory_sellable_date(entry_date:date, sessions:list[date])->date:
    """Equities allocated by 13:00 on trade date T+2; sellable in that afternoon.
    With daily bars, the engine records the date but cannot model 13:00 microstructure.
    """
    return add_trading_sessions(entry_date,sessions,2)

def eod_policy_earliest_exit_fill_date(entry_date:date,sessions:list[date])->date:
    """Conservative EOD policy: evaluate after close of settlement day, execute next session."""
    return add_trading_sessions(entry_date,sessions,3)
