from pathlib import Path
from datetime import date
import json
import pandas as pd
import streamlit as st
from vnquant.data.source_sync import SourceSyncOrchestrator
from vnquant.data.provider_registry import default_provider_registry
from vnquant.data.storage import Warehouse
from vnquant.data.reconciliation_frame import evaluate_canonical_frame
from vnquant.config.provider_origins import verified_provider_origins
from vnquant.ui_status import synchronization_status_view


def run_startup_sync(data_dir="data", orchestrator=None, *, force=False):
    # Streamlit's managed secret store is the only UI-side alternative to
    # environment variables. Values remain lazy and never enter sync reports.
    registry = None if orchestrator else default_provider_registry(secret_store=st.secrets.get)
    return (orchestrator or SourceSyncOrchestrator(data_dir, registry=registry)).sync(
        {"daily_ohlcv"}, force=force
    )


def run_independent_validation(data_dir, sync):
    """Validate the accepted latest session across independently evidenced origins.

    Different provider labels are not treated as independent unless the
    versioned provider-origin registry contains explicit verified evidence.
    """
    try:
        bars = Warehouse(data_dir).read_table("canonical_bars")
        if bars.empty:
            raise ValueError("canonical bars are empty")
        timestamps = pd.to_datetime(bars["timestamp"], utc=True, errors="coerce")
        bars = bars.loc[timestamps.notna()].copy()
        bars["timestamp"] = timestamps[timestamps.notna()]
        expected = date.fromisoformat(sync.last_accepted_market_date) if sync.last_accepted_market_date else None
        if expected is not None:
            latest = bars[bars["timestamp"].dt.date == expected]
            if not latest.empty:
                bars = latest
        return evaluate_canonical_frame(
            bars,
            provider_origins=verified_provider_origins(),
            expected_latest_session=expected,
        )
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
        return evaluate_canonical_frame(
            pd.DataFrame(),
            provider_origins=verified_provider_origins(),
            expected_latest_session=(
                date.fromisoformat(sync.last_accepted_market_date)
                if sync.last_accepted_market_date else None
            ),
        )


def display_sync_state(report):
    """Render one unambiguous application data state."""
    view = synchronization_status_view(report)
    getattr(st, view.severity)(view.primary_message)
    st.caption(view.details)
    if view.next_action:
        st.info(f"Next action: {view.next_action}")
    return view.state


DATA_DIR = "data"
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

reconciliation = run_independent_validation(DATA_DIR, sync)
analysis_actionable = bool(sync.actionable and reconciliation.buy_sell_allowed)
st.caption(
    "Independent validation: "
    f"{reconciliation.validation_status.value} | sources: "
    f"{', '.join(reconciliation.source_names) or 'none'} | "
    f"verified origins: {len(reconciliation.independent_origins)} | "
    f"quality: {reconciliation.overall_quality_score}/100"
)
if reconciliation.validation_status.value in {"QUARANTINED", "UNAVAILABLE"}:
    st.error(
        "Independent data validation blocked actionable recommendations: "
        + ", ".join(reconciliation.issues)
    )
elif reconciliation.validation_status.value == "WARNING":
    st.warning(
        "Independent validation is incomplete: "
        + ", ".join(reconciliation.issues)
    )

pub=Path("publish")
market_file=pub/"market.json"
if analysis_actionable and market_file.exists():
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
    st.info("Market artifacts are unavailable until governed synchronization and independent-data validation are acceptable.")

tabs=st.tabs(["Candidates","Sector Rotation","Backtest","Data/Model Notes"])
with tabs[0]:
    p=pub/"candidates.csv"
    if analysis_actionable and p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No candidate artifact.")
with tabs[1]:
    p=pub/"sector_scores.csv"
    if analysis_actionable and p.exists():
        df=pd.read_csv(p); st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.caption("No sector-score artifact.")
with tabs[2]:
    p=pub/"backtest_current_universe_proxy.csv"
    if analysis_actionable and p.exists():
        df=pd.read_csv(p); st.metric("Filled trades",len(df)); st.dataframe(df.tail(200),use_container_width=True,hide_index=True)
        audit=pub/"backtest_current_universe_proxy_execution_audit.csv"
        if audit.exists():
            a=pd.read_csv(audit); st.metric("Signals evaluated",len(a)); st.dataframe(a.tail(200),use_container_width=True,hide_index=True)
    else: st.caption("No backtest artifact.")
with tabs[3]:
    st.markdown("""
- Strategy thresholds marked `[D]` are calibration hypotheses, not facts.
- Provider-name differences do not prove independent upstream data origin.
- `VERIFIED` independent validation requires explicit origin evidence plus overlapping, consistent OHLCV observations.
- `QUARANTINED` / `UNAVAILABLE` independent validation blocks actionable recommendations.
- No automated market-data provider is currently admitted; real-data commands fail closed.
- Corporate-action type comes from official disclosure; adjustment ratios are anomaly detectors only.
- Missing provider bars are not forward-filled into fake OHLC.
- Elliott Wave is not part of the production score in this build.
""")
