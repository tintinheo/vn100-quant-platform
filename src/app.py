from pathlib import Path
import json
import pandas as pd
import streamlit as st
from vnquant.data.source_sync import SourceSyncOrchestrator

def run_startup_sync(data_dir="data", orchestrator=None, *, force=False):
    return (orchestrator or SourceSyncOrchestrator(data_dir)).sync({"daily_ohlcv"}, force=force)

def display_sync_state(report):
    """Render one unambiguous application data state."""
    if report.status == "NO_ADMITTED_PROVIDER":
        state = "NO_ADMITTED_PROVIDER"
    elif report.mode == "DEGRADED_CACHED_DATA":
        state = "DEGRADED_CACHED_DATA"
    elif report.mode == "STALE" or report.status == "CACHE_STALE":
        state = "STALE"
    elif report.mode == "FAILED" or report.status == "SYNC_FAILED":
        state = "FAILED"
    else:
        state = "FRESH"
    message = (f"{state} — provider: {report.provider_id or 'none'}; "
               f"data as of: {report.data_as_of or 'unavailable'}; "
               f"last sync: {report.last_sync_at or 'never'}; DQ: {report.dq_status}")
    if state == "FRESH":
        st.success(message)
    elif state == "DEGRADED_CACHED_DATA":
        st.warning(message)
    elif state == "STALE":
        st.warning(message)
    else:
        st.error(message)
    return state

st.set_page_config(page_title="VNQuant v3.3",layout="wide")
st.title("VNQuant v3.3 — SSI-Free Viewer")
st.caption("Decision support only. Startup performs a governed source sync check; it never places orders.")
force_refresh=st.sidebar.button("Refresh now", help="Force a governed provider recheck")
sync_indicator = st.empty()
sync_indicator.info("SYNCING — checking admitted providers and accepted cache…")
sync=run_startup_sync(force=force_refresh)
sync_indicator.empty()
display_sync_state(sync)
# Defensive fallback for future orchestrator statuses not yet mapped above.
if sync.status not in {"READY", "CACHE_STALE", "SYNC_FAILED", "NO_ADMITTED_PROVIDER"}:
    st.error(sync.status)
st.caption(f"Source: {sync.provider_id or 'none'} | mode: {sync.mode} | degraded: {'yes' if sync.degraded_mode else 'no'} | cache accepted: {'yes' if sync.cache_accepted else 'no'} | age: {sync.data_age_days if sync.data_age_days is not None else 'unknown'} days | last sync: {sync.last_successful_sync or 'never'} | DQ: {sync.dq_status}")
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
    if "PROXY" in market.get("cap_index_mode", ""):
        # The equal-weight series is an independent breadth/regime leg; it must
        # never be presented as a substitute for the required official index.
        st.warning(
            f"Official cap-index input unavailable: "
            f"{market.get('cap_index_warning') or market.get('cap_index_mode')}. "
            "Bull regime classification is disabled."
        )
else:
    st.info("Market artifacts are unavailable until governed synchronization produces accepted canonical data.")

tabs=st.tabs(["Candidates","Sector Rotation","Backtest","Data/Model Notes"])
with tabs[0]:
    p=pub/"candidates.csv"
    if sync.actionable and p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No candidate artifact.")
with tabs[1]:
    p=pub/"sector_scores.csv"
    if sync.actionable and p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No sector-score artifact.")
with tabs[2]:
    p=pub/"backtest_current_universe_proxy.csv"
    if sync.actionable and p.exists():
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
