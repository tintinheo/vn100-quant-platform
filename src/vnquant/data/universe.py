from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
import pandas as pd

class UniverseMode(str, Enum):
    STRICT_PIT = "STRICT_PIT"
    CURRENT_UNIVERSE_PROXY = "CURRENT_UNIVERSE_PROXY"

REQUIRED = {"index_code", "symbol", "effective_from", "effective_to", "source", "source_snapshot_id"}

@dataclass(frozen=True)
class UniverseResolution:
    as_of: date
    symbols: tuple[str, ...]
    mode: UniverseMode
    source: str
    warning: str | None = None
    source_snapshot_ids: tuple[str, ...] = ()

class UniverseStore:
    """Effective-dated universe snapshots.

    STRICT_PIT never fabricates historical membership. If no effective-dated
    snapshot covers the requested date it raises rather than silently using
    today's VN100.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=sorted(REQUIRED))
        df = pd.read_csv(self.path, dtype={"index_code": str, "symbol": str, "source": str})
        missing = REQUIRED - set(df.columns)
        if missing:
            raise ValueError(f"Universe snapshot missing columns: {sorted(missing)}")
        df["effective_from"] = pd.to_datetime(df["effective_from"], errors="raise")
        df["effective_to"] = pd.to_datetime(df["effective_to"], errors="coerce")
        df["symbol"] = df["symbol"].str.upper().str.strip()
        return df

    def resolve(self, as_of: date, index_code: str = "VN100", *,
                current_members: list[str] | None = None,
                allow_proxy: bool = False) -> UniverseResolution:
        df = self._load()
        if not df.empty:
            ts = pd.Timestamp(as_of)
            rows = df[(df.index_code == index_code) & (df.effective_from <= ts) &
                      (df.effective_to.isna() | (df.effective_to >= ts))]
            symbols = tuple(sorted(rows.symbol.unique()))
            if symbols:
                return UniverseResolution(as_of, symbols, UniverseMode.STRICT_PIT,
                                          ";".join(sorted(rows.source.unique())), None,
                                          tuple(sorted(rows.source_snapshot_id.unique())))
        if allow_proxy and current_members:
            return UniverseResolution(
                as_of, tuple(sorted({s.upper() for s in current_members})),
                UniverseMode.CURRENT_UNIVERSE_PROXY, "current-provider-membership",
                "NOT_TRUE_HISTORICAL_VN100: current membership used for a historical date",
            )
        raise LookupError(f"No point-in-time {index_code} snapshot covers {as_of}")

    def append_snapshot(self, symbols: list[str], effective_from: date, *,
                        index_code: str = "VN100", source: str,
                        source_snapshot_id: str,
                        effective_to: date | None = None) -> None:
        """Append membership transcribed from one immutable official snapshot."""
        if not source.strip() or not source_snapshot_id.strip():
            raise ValueError("source and source_snapshot_id are required")
        if effective_to is not None and effective_to < effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        normalized = sorted({s.upper().strip() for s in symbols if s.strip()})
        if not normalized:
            raise ValueError("official membership snapshot cannot be empty")
        old = self._load()
        new = pd.DataFrame({
            "index_code": index_code,
            "symbol": normalized,
            "effective_from": effective_from.isoformat(),
            "effective_to": effective_to.isoformat() if effective_to else "",
            "source": source,
            "source_snapshot_id": source_snapshot_id,
        })
        out = pd.concat([old, new], ignore_index=True) if not old.empty else new
        out["effective_from"] = out["effective_from"].astype(str)
        out["effective_to"] = out["effective_to"].astype(str).replace("NaT", "")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.drop_duplicates(["index_code", "symbol", "effective_from", "source_snapshot_id"]).to_csv(self.path, index=False)
