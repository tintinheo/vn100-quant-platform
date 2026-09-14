from pathlib import Path
import json
import pandas as pd
import streamlit as st
from vnquant.data.source_sync import SourceSyncOrchestrator

def run_startup_sync(data_dir="data", orchestrator=None):
    return (orchestrator or SourceSyncOrchestrator(data_dir)).sync({"daily_ohlcv"})

st.set_page_config(page_title="VNQuant v3.3",layout="wide")
st.title("VNQuant v3.3 — SSI-Free Viewer")
st.caption("Decision support only. Startup performs a governed source sync check; it never places orders.")
sync=run_startup_sync()
st.caption(f"Source: {sync.provider_id or 'none'} | mode: {sync.mode} | age: {sync.data_age_days if sync.data_age_days is not None else 'unknown'} days | last sync: {sync.last_successful_sync or 'never'} | DQ: {sync.dq_status}")
if not sync.actionable:
    st.error(sync.failure_reason or sync.mode)
pub=Path("publish")
market_file=pub/"market.json"
if sync.actionable and market_file.exists():
    market=json.loads(market_file.read_text(encoding="utf-8"))
    c1,c2,c3=st.columns(3)
    c1.metric("Market regime",market.get("regime","UNKNOWN"))
    c2.metric("Candidates",market.get("candidate_count",0))
    c3.metric("As of",market.get("as_of",""))
    if market.get("universe_mode")!="STRICT_PIT": st.warning("CURRENT_UNIVERSE_PROXY — historical results are not a true point-in-time VN100 backtest.")
    if market.get("sector_mode")!="STRICT_PIT": st.warning(market.get("sector_warning") or "Current sector mapping is being used as a historical proxy.")
    if "PROXY" in market.get("cap_index_mode",""): st.info("Market regime currently uses an equal-weight proxy until an official cap-index series is ingested.")
else:
    st.info("No market artifact yet. Run the local bootstrap and pipeline first.")

tabs=st.tabs(["Candidates","Sector Rotation","Backtest","Data/Model Notes"])
with tabs[0]:
    p=pub/"candidates.csv"
    if sync.actionable and p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No candidate artifact.")
with tabs[1]:
    p=pub/"sector_scores.csv"
    if p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No sector-score artifact.")
with tabs[2]:
    p=pub/"backtest_current_universe_proxy.csv"
    if p.exists():
        df=pd.read_csv(p); st.metric("Filled trades",len(df)); st.dataframe(df.tail(200),use_container_width=True,hide_index=True)
        audit=pub/"backtest_current_universe_proxy_execution_audit.csv"
        if audit.exists():
            a=pd.read_csv(audit); st.metric("Signals evaluated",len(a)); st.dataframe(a.tail(200),use_container_width=True,hide_index=True)
    else: st.caption("No backtest artifact.")
with tabs[3]:
    st.markdown("""
- Strategy thresholds marked `[D]` are calibration hypotheses, not facts.
- No automated market-data provider is currently admitted; real-data commands fail closed.
- Corporate-action type comes from official disclosure; adjustment ratios are anomaly detectors only.
- Missing provider bars are not forward-filled into fake OHLC.
- Elliott Wave is not part of the production score in this build.
""")
