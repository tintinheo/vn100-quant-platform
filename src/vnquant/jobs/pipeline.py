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
from vnquant.data.source_sync import SourceSyncOrchestrator
from vnquant.data.quality import apply_dq_policy
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
    # VN-Index is the BRD cap-weighted input; VN100 is accepted only when VN-Index is absent.
    available = set(indexes.index_code.astype(str).str.upper())
    code = "VNINDEX" if "VNINDEX" in available else ("VN100" if "VN100" in available else None)
    if code is None:
        return unavailable, "DEGRADED_PROXY_UNAVAILABLE", "VNINDEX/VN100 official series absent"
    series = indexes[indexes.index_code.astype(str).str.upper() == code].sort_values("trading_date")
    if series.trading_date.max() < latest_date:
        return unavailable, "DEGRADED_PROXY_STALE", f"official {code} series stale"
    for window in parameter_value("features.ma_windows"):
        series[f"ma{int(window)}"] = series.close.astype(float).rolling(int(window), min_periods=int(window)).mean()
    turnover_window = int(parameter_value("market.turnover_window"))
    turnover_min = int(parameter_value("market.turnover_min_periods"))
    turnover = pd.to_numeric(series.turnover, errors="coerce")
    series["turnover_ratio"] = turnover / turnover.rolling(turnover_window, min_periods=turnover_min).mean()
    row = series[series.trading_date == latest_date]
    if row.empty:
        return unavailable, "DEGRADED_PROXY_STALE", f"official {code} latest session missing"
    return row.iloc[-1], f"OFFICIAL_{code}", None


def _publish_blocked_result(sync, publish_dir: str) -> dict:
    """Publish the gate outcome and remove analytics from an older run."""
    result={"status":sync.status,"sync_mode":sync.mode,
            "provider_id":sync.provider_id,"data_age_days":sync.data_age_days,
            "last_sync_at":sync.last_successful_sync,"dq_status":sync.dq_status,
            "degraded_mode":sync.degraded_mode,"cache_accepted":sync.cache_accepted,
            "candidate_count":0,"actionable":False}
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
    for p in sorted((wh.parquet/"bars").glob("*.parquet")):
        d=add_baseline_features(pd.read_parquet(p))
        frames.append(d)
    if not frames: raise RuntimeError("No bars in warehouse. Run bootstrap first.")
    panel=pd.concat(frames,ignore_index=True)
    mapped=apply_sector_mapping(panel,pit_path=sector_pit_path,current_master=sec)
    return mapped.panel, mapped.mode.value, mapped.warning


def run(data_dir="data", publish_dir="publish", sector_pit_path: str | None = None,
        sync_orchestrator: SourceSyncOrchestrator | None = None,
        portfolio_context: PortfolioContext | None = None) -> dict:
    sync=(sync_orchestrator or SourceSyncOrchestrator(data_dir)).sync({"daily_ohlcv"})
    if not sync.actionable:
        return _publish_blocked_result(sync,publish_dir)
    wh=Warehouse(data_dir); panel, sector_mode, sector_warning=_load_panel(wh,sector_pit_path)
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
    (out/"market.json").write_text(json.dumps(market,ensure_ascii=False,indent=2),encoding="utf-8")
    return market

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",default="data"); ap.add_argument("--publish-dir",default="publish"); ap.add_argument("--sector-pit",default=None)
    a=ap.parse_args(); print(json.dumps(run(a.data_dir,a.publish_dir,a.sector_pit),indent=2,ensure_ascii=False))
