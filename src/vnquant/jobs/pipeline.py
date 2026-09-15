from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from vnquant.data.storage import Warehouse
from vnquant.features.technical import add_baseline_features
from vnquant.features.relative_strength import add_cross_sectional_rs
from vnquant.market.breadth import build_equal_weight_index, compute_breadth
from vnquant.market.regime import compute_regime
from vnquant.market.sector_rotation import compute_sector_scores
from vnquant.recommendations.engine import detect_candidates
from vnquant.data.sector_membership import apply_sector_mapping
from vnquant.data.source_sync import SourceSyncOrchestrator, SyncReport, SyncStatus
from vnquant.data.quality import ACTIONABLE_BLOCK_THRESHOLD, apply_dq_policy
from vnquant.config import parameter_value
from vnquant.portfolio import PortfolioContext, PortfolioRiskService


def _official_cap_index(wh: Warehouse, latest_date) -> tuple[pd.Series, str, str | None]:
    """Return a fresh official cap-index row, or an explicitly unavailable proxy state."""
    unavailable = pd.Series({"close": pd.NA, "ma50": pd.NA, "ma200": pd.NA})
    try:
        indexes = wh.read_table("index_bars")
    except (FileNotFoundError, OSError):
        return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "official index data absent"
    if indexes.empty:
        return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "official index data absent"
    indexes = indexes.copy()
    indexes["trading_date"] = pd.to_datetime(indexes["timestamp"], utc=True).dt.date
    required_lineage = {"provider", "raw_snapshot_id", "payload_sha256", "source_reference"}
    if not required_lineage.issubset(indexes.columns):
        return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "official index lineage incomplete"
    accepted = []
    for row in indexes.itertuples(index=False):
        try:
            metadata = wh._raw_snapshot_metadata(str(row.provider), str(row.raw_snapshot_id))
        except (FileNotFoundError, OSError, ValueError, KeyError):
            continue
        if (metadata.get("payload_sha256") == row.payload_sha256 and
                metadata.get("source_reference") == row.source_reference):
            accepted.append(row)
    indexes = pd.DataFrame(accepted, columns=indexes.columns)
    if indexes.empty:
        return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "no raw-lineaged official index observations"

    # VN-Index is the BRD cap-weighted input. A fresh, accepted VN100 series is
    # used only when VN-Index cannot supply the current expected session.
    indexes["index_code"] = indexes.index_code.astype(str).str.upper()
    code = next((candidate for candidate in ("VNINDEX", "VN100")
                 if not indexes[(indexes.index_code == candidate) &
                                (indexes.trading_date == latest_date)].empty), None)
    if code is None:
        available = set(indexes.index_code)
        if not available.intersection({"VNINDEX", "VN100"}):
            return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "VNINDEX/VN100 official series absent"
        present = "VNINDEX" if "VNINDEX" in available else "VN100"
        return unavailable, "DEGRADED_PROXY_STALE", f"official {present} latest session missing"
    series = indexes[indexes.index_code == code].sort_values("trading_date")
    for window in parameter_value("features.ma_windows"):
        series[f"ma{int(window)}"] = series.close.astype(float).rolling(int(window), min_periods=int(window)).mean()
    turnover_window = int(parameter_value("market.turnover_window"))
    turnover_min = int(parameter_value("market.turnover_min_periods"))
    turnover = pd.to_numeric(series.turnover, errors="coerce")
    series["turnover_ratio"] = turnover / turnover.rolling(turnover_window, min_periods=turnover_min).mean()
    row = series[series.trading_date == latest_date]
    return row.iloc[-1], f"OFFICIAL_{code}", None


def _sync_metadata(sync: SyncReport, **overrides) -> dict:
    values = {
        "provider_id": sync.provider_id, "providers": dict(sync.providers),
        "provider_status": "ADMITTED" if sync.status == SyncStatus.READY.value else "NOT_ACCEPTED",
        "sync_run_id": sync.run_id, "sync_status": sync.status, "sync_mode": sync.mode,
        "data_age_days": sync.data_age_days, "last_sync_at": sync.last_successful_sync,
        "expected_session_status": sync.expected_session_status,
        "canonical_revision": sync.canonical_revision, "lineage_status": sync.lineage_status,
        "dq_status": sync.dq_status, "dq_score": sync.dq_score,
        "universe_status": sync.universe_status, "sector_status": sync.sector_status,
        "corporate_action_status": sync.corporate_action_status,
        "reconciliation_status": sync.reconciliation_status,
        "degraded_mode": sync.degraded_mode, "cache_accepted": sync.cache_accepted,
    }
    values.update(overrides)
    return values


def _publish_blocked_result(sync: SyncReport, publish_dir: str, reason: str | None = None,
                            **statuses) -> dict:
    """Publish the gate outcome and remove analytics from an older run."""
    result = _sync_metadata(sync, **statuses)
    result.update({"status": sync.status, "block_reason": reason or sync.failure_reason,
                   "candidate_count": 0, "actionable": False})
    out=Path(publish_dir); out.mkdir(parents=True,exist_ok=True)
    for name in ("candidates.csv", "sector_scores.csv", "portfolio_risk_decisions.csv"):
        (out/name).unlink(missing_ok=True)
    (out/"market.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def _load_panel(wh: Warehouse, sector_pit_path: str | None = None):
    frames=[]
    sec=None
    try: sec=wh.read_table("security_master")
    except Exception: pass
    canonical_path = wh.parquet / "canonical_bars.parquet"
    if canonical_path.exists():
        canonical = pd.read_parquet(canonical_path)
        canonical["trading_date"] = pd.to_datetime(canonical.timestamp).dt.date
        canonical["value"] = canonical.turnover
        for _, frame in canonical.groupby("symbol", sort=True):
            frames.append(frame.copy())
    if not frames: raise RuntimeError("No canonical bars in warehouse. Run bootstrap first.")
    panel=pd.concat(frames,ignore_index=True)
    mapped=apply_sector_mapping(panel,pit_path=sector_pit_path,current_master=sec)
    return mapped.panel, mapped.mode.value, mapped.warning


def _validate_sync_for_analytics(sync: SyncReport, orchestrator: SourceSyncOrchestrator,
                                 wh: Warehouse) -> tuple[bool, str | None, dict]:
    """Re-check the persisted synchronization contract at the consumer boundary."""
    if not isinstance(sync, SyncReport):
        return False, "SYNC_REPORT_REQUIRED", {}
    expected = orchestrator.expected_session(orchestrator.today()).isoformat()
    admitted = set(orchestrator.registry.admitted_provider_ids("daily_ohlcv"))
    provider_ok = bool(sync.provider_id and sync.provider_id in admitted)
    session_ok = sync.last_accepted_market_date == expected and (sync.data_age_days or 0) == 0
    revision_ok = bool(sync.canonical_revision)
    lineage_ok = bool(sync.raw_snapshot_ids or not sync.remote_fetch_performed)
    corporate_action_status = "CLEAR"
    reconciliation_status = "CLEAR"
    try:
        bars = wh.read_table("canonical_bars")
        revision_ok = revision_ok and "canonical_revision" in bars and sync.canonical_revision in set(
            bars.canonical_revision.dropna().astype(str))
        required = {"raw_snapshot_id", "payload_sha256", "source_reference"}
        lineage_ok = lineage_ok and required.issubset(bars.columns) and not bars[list(required)].isna().any().any()
        if lineage_ok:
            for row in bars[["provider", "raw_snapshot_id", "payload_sha256",
                             "source_reference"]].drop_duplicates().itertuples(index=False):
                metadata = wh._raw_snapshot_metadata(str(row.provider), str(row.raw_snapshot_id))
                lineage_ok = (metadata.get("payload_sha256") == row.payload_sha256 and
                              metadata.get("source_reference") == row.source_reference)
                if not lineage_ok:
                    break
        try:
            issues = wh.read_table("data_quality_results")
            revision_issues = issues[issues.canonical_revision.astype(str) == sync.canonical_revision]
            if "PROVIDER_DISAGREEMENT" in set(revision_issues.code.astype(str)):
                reconciliation_status = "DISAGREEMENT"
        except (FileNotFoundError, OSError, KeyError):
            pass
        try:
            anomalies = wh.read_table("adjustment_anomalies")
            unresolved = anomalies[~anomalies.resolution_status.astype(str).str.upper().isin(
                {"RESOLVED", "VERIFIED", "CLEAR"})]
            if not unresolved.empty:
                corporate_action_status = "UNRESOLVED"
        except (FileNotFoundError, OSError, KeyError):
            pass
    except (FileNotFoundError, OSError, ValueError, KeyError):
        revision_ok = lineage_ok = False
    statuses = {
        "provider_status": "ADMITTED" if provider_ok else "NOT_ADMITTED",
        "expected_session_status": "COMPLETE" if session_ok else "INCOMPLETE_OR_STALE",
        "lineage_status": "COMPLETE" if lineage_ok else "MISSING",
        "canonical_revision_status": "ACCEPTED" if revision_ok else "MISSING_OR_MISMATCHED",
        "corporate_action_status": corporate_action_status,
        "reconciliation_status": reconciliation_status,
    }
    capabilities_ok = {"daily_ohlcv", "current_index_members"}.issubset(sync.required_capabilities)
    state_ok = (sync.dq_status in {"PASS", "WARN"} and
                sync.universe_status not in {"UNKNOWN", "MISSING", "FAILED"} and
                corporate_action_status == "CLEAR" and
                reconciliation_status in {"CLEAR", "DISAGREEMENT"})
    acceptable = (sync.actionable and sync.cache_accepted and provider_ok and session_ok and
                  revision_ok and lineage_ok and capabilities_ok and state_ok and
                  sync.dq_score >= ACTIONABLE_BLOCK_THRESHOLD)
    return acceptable, None if acceptable else "SYNC_REPORT_NOT_ACCEPTABLE", statuses


def run(data_dir="data", publish_dir="publish", sector_pit_path: str | None = None,
        sync_orchestrator: SourceSyncOrchestrator | None = None,
        portfolio_context: PortfolioContext | None = None) -> dict:
    orchestrator = sync_orchestrator or SourceSyncOrchestrator(data_dir)
    sync=orchestrator.sync({"daily_ohlcv"})
    wh=Warehouse(data_dir)
    acceptable, reason, gate_statuses = _validate_sync_for_analytics(sync, orchestrator, wh)
    if not acceptable:
        return _publish_blocked_result(sync,publish_dir,reason,**gate_statuses)
    panel, sector_mode, sector_warning=_load_panel(wh,sector_pit_path)
    # No feature calculation occurs before the accepted sync/revision gate above.
    panel = pd.concat((add_baseline_features(frame.copy())
                       for _, frame in panel.groupby("symbol", sort=True)), ignore_index=True)
    panel=add_cross_sectional_rs(panel)
    breadth=compute_breadth(panel); ew=build_equal_weight_index(panel)

    latest_date=panel.trading_date.max()
    br=breadth[breadth.trading_date==latest_date].iloc[-1]
    ewr=ew[ew.trading_date==latest_date].iloc[-1]
    capr, cap_mode, cap_warning=_official_cap_index(wh,latest_date)
    # Official index turnover confirms liquidity. Missing official turnover is
    # neutral and therefore cannot manufacture a bull classification.
    regime_breadth=br.copy()
    regime_breadth["turnover_ratio"] = capr.get("turnover_ratio")
    rr=compute_regime(capr,ewr,regime_breadth)
    sectors=compute_sector_scores(panel,latest_date)
    latest=panel[panel.trading_date==latest_date].copy()
    dq_score=int(sync.dq_score)
    _, dq_actionable = apply_dq_policy(0.0, dq_score)
    candidates=detect_candidates(latest,rr.regime,sectors,dq_score=dq_score,
                                 dq_actionable=sync.actionable)
    if not dq_actionable:
        candidates=candidates.iloc[0:0]

    # Risk approval is deliberately after recommendation construction and before
    # either warehouse/publication output. Missing account state fails closed.
    context = portfolio_context or PortfolioContext(0.0, 0.0, 0.0)
    decisions = PortfolioRiskService().evaluate(candidates, context, rr.regime.name)
    if not decisions.empty:
        wh.persist_portfolio_risk_decisions(decisions)
        approved = decisions[decisions.status.isin(["ACCEPTED", "RESIZED"])]
        candidates = candidates.merge(
            approved[["decision_id", "symbol", "status", "quantity", "estimated_loss",
                      "notional", "binding_constraint", "configuration_version"]],
            on="symbol", how="inner")
    else:
        candidates = candidates.iloc[0:0]

    publication_status = _sync_metadata(sync, **gate_statuses,
        universe_status=sync.universe_status, sector_status=sector_mode,
        confidence_cap=(dq_score if sync.degraded_mode else None))
    for key, value in publication_status.items():
        candidates[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value

    wh.write_table(sectors,"sector_scores")
    wh.write_table(candidates,"candidates")
    wh.write_table(pd.DataFrame([{
        "as_of":latest_date,"regime":rr.regime.name,"cap_score":rr.cap_score,"ew_score":rr.ew_score,
        "breadth_pct_ma50":rr.breadth_pct_ma50,"turnover_ratio":rr.turnover_ratio,"reason":rr.reason,
        "cap_index_mode":cap_mode,"cap_index_warning":cap_warning,
    }]),"market_regimes")
    wh.build_duckdb_views()

    out=Path(publish_dir); out.mkdir(parents=True,exist_ok=True)
    sectors.to_csv(out/"sector_scores.csv",index=False)
    candidates.to_csv(out/"candidates.csv",index=False)
    decisions.to_csv(out/"portfolio_risk_decisions.csv", index=False)
    market={"as_of":str(latest_date),"regime":rr.regime.name,"reason":rr.reason,
            "candidate_count":int(len(candidates)),"universe_mode":"CURRENT_UNIVERSE_PROXY",
            "sector_mode":sector_mode,"sector_warning":sector_warning,
            "cap_index_mode":cap_mode,"cap_index_warning":cap_warning,
            "sync_mode":sync.mode,"provider_id":sync.provider_id,"data_age_days":sync.data_age_days,
            "last_sync_at":sync.last_successful_sync,"dq_status":sync.dq_status,
            "degraded_mode":bool(sync.degraded_mode or cap_mode.startswith("DEGRADED_PROXY")),
            "cache_accepted":sync.cache_accepted,
            "status":sync.status,"dq_score":dq_score,
            "actionable":bool(sync.actionable and dq_actionable)}
    market.update(publication_status)
    (out/"market.json").write_text(json.dumps(market,ensure_ascii=False,indent=2),encoding="utf-8")
    return market

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",default="data"); ap.add_argument("--publish-dir",default="publish"); ap.add_argument("--sector-pit",default=None)
    a=ap.parse_args(); print(json.dumps(run(a.data_dir,a.publish_dir,a.sector_pit),indent=2,ensure_ascii=False))
