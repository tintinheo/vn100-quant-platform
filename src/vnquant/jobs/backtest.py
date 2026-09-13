from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd, yaml
from vnquant.data.storage import Warehouse
from vnquant.features.technical import add_baseline_features
from vnquant.market.rules import BrokerCostProfile
from vnquant.backtest.engine import backtest_pullback_with_audit
from vnquant.backtest.metrics import trade_metrics
from vnquant.backtest.execution import ExecutionMode

def load_costs(path):
    x=yaml.safe_load(Path(path).read_text(encoding="utf-8")); return BrokerCostProfile(**{k:x[k] for k in ["commission_rate","commission_includes_exchange_fee","exchange_fee_rate","sell_tax_rate","slippage_bps"]})
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",default="data"); ap.add_argument("--costs",default="config/broker_costs.example.yaml"); ap.add_argument("--mode",choices=[x.value for x in ExecutionMode],default="conservative"); ap.add_argument("--output",default="publish/backtest_current_universe_proxy.csv")
    a=ap.parse_args(); wh=Warehouse(a.data_dir); costs=load_costs(a.costs); rows=[]; audits=[]
    bar_dir=wh.parquet/"bars"
    for p in sorted(bar_dir.glob("*.parquet")):
        df=add_baseline_features(pd.read_parquet(p)); tr,audit=backtest_pullback_with_audit(df,costs,mode=ExecutionMode(a.mode));
        if not tr.empty: rows.append(tr)
        if not audit.empty: audits.append(audit)
    out=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(a.output,index=False)
    audit=pd.concat(audits,ignore_index=True) if audits else pd.DataFrame()
    audit_path=Path(a.output).with_name(Path(a.output).stem+"_execution_audit.csv")
    audit.to_csv(audit_path,index=False)
    summary={"universe_mode":"CURRENT_UNIVERSE_PROXY","warning":"NOT_TRUE_HISTORICAL_VN100 unless effective-dated membership snapshots were supplied"}
    summary.update(trade_metrics(out))
    if not audit.empty:
        summary["signals_evaluated"]=int(len(audit)); summary["fill_rate"]=float((audit.status=="FILLED").mean())
        summary["mean_overnight_gap"]=float(audit.overnight_gap.dropna().mean())
        summary["execution_rejections"]=audit[audit.status!="FILLED"].reason.value_counts().to_dict()
    print(json.dumps(summary,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
