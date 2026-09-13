from __future__ import annotations
import argparse, os, sys
from datetime import date, timedelta
from vnquant.data.ssi import SSIFastConnectV3Provider, SSIConfigurationError
from vnquant.data.quality import validate_bars, quality_score

def run(symbol="SSI",days=90,index="VN100") -> int:
    print("VNQuant Doctor v3.1 — real-data preflight")
    try:
        with SSIFastConnectV3Provider() as p:
            print("[1/5] AUTH/NETWORK: OK (market-data token, no OTP)")
            sec=p.current_index_securities(index); members=sec.symbol.tolist(); print(f"[2/5] INDEX {index}: {len(members)} members; sample={members[:8]}; ICB populated={(sec.icb_name != "UNKNOWN").mean():.1%}")
            end=date.today(); start=end-timedelta(days=days*2)
            df=p.daily_history(symbol,start,end); print(f"[3/5] OHLC {symbol}: {len(df)} rows {df.trading_date.min()}..{df.trading_date.max()}")
            issues=validate_bars(df); print(f"[4/5] QUALITY: score={quality_score(issues)} issues={[(x.severity,x.code) for x in issues]}")
            if any(x.severity=="ERROR" for x in issues): return 1
            print("[5/5] RESULT: PASS. This proves connectivity/schema plausibility, NOT full VN100 correctness.")
            return 0
    except SSIConfigurationError as e:
        print("CONFIGURATION:",e); return 2
    except Exception as e:
        print("FAILED:",type(e).__name__,e); return 1

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--symbol",default="SSI"); ap.add_argument("--days",type=int,default=90); ap.add_argument("--index",default="VN100")
    a=ap.parse_args(); raise SystemExit(run(a.symbol,a.days,a.index))
