from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from vnquant.market.rules import round_down_hose, hose_floor

class ExecutionMode(str,Enum):
    OPTIMISTIC="optimistic"; BASE="base"; CONSERVATIVE="conservative"

@dataclass(frozen=True)
class FillResult:
    filled: bool
    price: float|None
    reason: str


def simulate_buy_limit(close_t:float,next_open:float,next_high:float,next_low:float,*,premium:float,max_gap:float,mode:ExecutionMode=ExecutionMode.CONSERVATIVE)->FillResult:
    gap=next_open/close_t-1
    if gap>max_gap: return FillResult(False,None,"gap_gate")
    limit=round_down_hose(close_t*(1+premium))
    if next_open<=limit: return FillResult(True,float(next_open),"open_better_than_limit")
    if next_low<limit: return FillResult(True,float(limit),"traded_through_limit")
    if next_low==limit and mode==ExecutionMode.OPTIMISTIC:
        return FillResult(True,float(limit),"touch_fill_optimistic")
    return FillResult(False,None,"limit_not_provably_filled")


def simulate_urgent_sell(prev_close:float,next_open:float,next_high:float,next_low:float,*,mode:ExecutionMode=ExecutionMode.CONSERVATIVE)->FillResult:
    floor_px=hose_floor(prev_close)
    # Daily OHLC cannot observe queue. If the whole day is pinned at/under model floor, treat as non-fill in base/conservative.
    pinned = next_open<=floor_px and next_high<=floor_px
    if pinned and mode!=ExecutionMode.OPTIMISTIC:
        return FillResult(False,None,"floor_lock_or_no_liquidity")
    return FillResult(True,float(next_open),"urgent_next_open")
