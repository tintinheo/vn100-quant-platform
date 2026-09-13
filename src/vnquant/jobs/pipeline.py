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


def run(data_dir="data", publish_dir="publish", sector_pit_path: str | None = None) -> dict:
    wh=Warehouse(data_dir); panel, sector_mode, sector_warning=_load_panel(wh,sector_pit_path)
    panel=add_cross_sectional_rs(panel,horizons=(20,126))
    breadth=compute_breadth(panel); ew=build_equal_weight_index(panel)

    # Cap-index proxy in offline mode: current-universe equal-weight series.
    # A real official VNINDEX/VN100 index series should replace this when ingested.
    cap=ew.copy()
    latest_date=panel.trading_date.max()
    br=breadth[breadth.trading_date==latest_date].iloc[-1]
    ewr=ew[ew.trading_date==latest_date].iloc[-1]
    capr=cap[cap.trading_date==latest_date].iloc[-1]
    rr=compute_regime(capr,ewr,br)
    sectors=compute_sector_scores(panel,latest_date)
    latest=panel[panel.trading_date==latest_date].copy()
    candidates=detect_candidates(latest,rr.regime,sectors)

    wh.write_table(sectors,"sector_scores")
    wh.write_table(candidates,"candidates")
    wh.write_table(pd.DataFrame([{
        "as_of":latest_date,"regime":rr.regime.name,"cap_score":rr.cap_score,"ew_score":rr.ew_score,
        "breadth_pct_ma50":rr.breadth_pct_ma50,"turnover_ratio":rr.turnover_ratio,"reason":rr.reason,
    }]),"market_regimes")
    wh.build_duckdb_views()

    out=Path(publish_dir); out.mkdir(parents=True,exist_ok=True)
    sectors.to_csv(out/"sector_scores.csv",index=False)
    candidates.to_csv(out/"candidates.csv",index=False)
    market={"as_of":str(latest_date),"regime":rr.regime.name,"reason":rr.reason,
            "candidate_count":int(len(candidates)),"universe_mode":"CURRENT_UNIVERSE_PROXY",
            "sector_mode":sector_mode,"sector_warning":sector_warning,
            "cap_index_mode":"EQUAL_WEIGHT_PROXY_UNTIL_OFFICIAL_INDEX_SERIES_INGESTED"}
    (out/"market.json").write_text(json.dumps(market,ensure_ascii=False,indent=2),encoding="utf-8")
    return market

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",default="data"); ap.add_argument("--publish-dir",default="publish"); ap.add_argument("--sector-pit",default=None)
    a=ap.parse_args(); print(json.dumps(run(a.data_dir,a.publish_dir,a.sector_pit),indent=2,ensure_ascii=False))
