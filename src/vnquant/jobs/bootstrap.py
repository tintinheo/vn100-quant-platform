from __future__ import annotations
import argparse
from datetime import date
from vnquant.data.ssi import SSIFastConnectV3Provider
from vnquant.data.quality import validate_bars
from vnquant.data.storage import Warehouse

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--start",default="2015-01-01"); ap.add_argument("--end",default=str(date.today())); ap.add_argument("--data-dir",default="data")
    a=ap.parse_args(); wh=Warehouse(a.data_dir); start=date.fromisoformat(a.start); end=date.fromisoformat(a.end)
    with SSIFastConnectV3Provider() as p:
        security_master=p.current_index_securities("VN100")
        members=security_master.symbol.tolist()
        wh.write_table(security_master,"security_master")
        wh.write_table(security_master[["symbol","index_code","provider"]].assign(snapshot_date=end.isoformat()),"universe_current")
        print(f"Current VN100 members: {len(members)}. Historical use is CURRENT_UNIVERSE_PROXY unless PIT snapshots are supplied.")
        for k,s in enumerate(members,1):
            df=p.daily_history(s,start,end); issues=validate_bars(df)
            if any(x.severity=="ERROR" for x in issues):
                print(f"[{k}/{len(members)}] {s}: BLOCKED {[(x.code,x.message) for x in issues]}"); continue
            out=wh.write_bars(df,s); print(f"[{k}/{len(members)}] {s}: {len(df)} rows -> {out}")
    wh.build_duckdb_views()
if __name__=="__main__": main()
