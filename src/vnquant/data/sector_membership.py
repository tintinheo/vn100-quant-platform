from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import pandas as pd

class SectorMode(str, Enum):
    STRICT_PIT = "STRICT_PIT"
    CURRENT_ICB_PROXY = "CURRENT_ICB_PROXY"

@dataclass(frozen=True)
class SectorMappingResult:
    panel: pd.DataFrame
    mode: SectorMode
    warning: str | None


def apply_sector_mapping(panel: pd.DataFrame, *, pit_path: str | Path | None = None,
                         current_master: pd.DataFrame | None = None) -> SectorMappingResult:
    d=panel.copy()
    if pit_path is not None and Path(pit_path).exists():
        m=pd.read_csv(pit_path)
        req={"symbol","sector","effective_from","effective_to"}
        missing=req-set(m.columns)
        if missing: raise ValueError(f"Sector PIT file missing columns: {sorted(missing)}")
        m["symbol"]=m.symbol.astype(str).str.upper()
        m["effective_from"]=pd.to_datetime(m.effective_from,errors="raise")
        m["effective_to"]=pd.to_datetime(m.effective_to,errors="coerce")
        d["_td"]=pd.to_datetime(d.trading_date)
        d["sector"]="UNKNOWN"
        # Deterministic and auditable; VN100 scale makes this acceptable.
        for row in m.itertuples(index=False):
            mask=(d.symbol.astype(str).str.upper()==row.symbol)&(d._td>=row.effective_from)&(pd.isna(row.effective_to)|(d._td<=row.effective_to))
            d.loc[mask,"sector"]=row.sector
        d=d.drop(columns="_td")
        return SectorMappingResult(d,SectorMode.STRICT_PIT,None)
    if current_master is not None and not current_master.empty:
        cmap=dict(zip(current_master.symbol.astype(str).str.upper(),current_master.icb_name.fillna("UNKNOWN").astype(str)))
        d["sector"]=d.symbol.astype(str).str.upper().map(cmap).fillna("UNKNOWN")
        return SectorMappingResult(d,SectorMode.CURRENT_ICB_PROXY,
            "NOT_TRUE_HISTORICAL_SECTOR_CLASSIFICATION: current provider sector mapping applied historically")
    d["sector"]="UNKNOWN"
    return SectorMappingResult(d,SectorMode.CURRENT_ICB_PROXY,"No sector metadata available")
