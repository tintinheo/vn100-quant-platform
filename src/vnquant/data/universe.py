from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
import pandas as pd

class UniverseMode(str, Enum):
    STRICT_PIT = "STRICT_PIT"
    CURRENT_UNIVERSE_PROXY = "CURRENT_UNIVERSE_PROXY"

REQUIRED = {"index_code", "symbol", "effective_from", "effective_to", "source"}

@dataclass(frozen=True)
class UniverseResolution:
    as_of: date
    symbols: tuple[str, ...]
    mode: UniverseMode
    source: str
    warning: str | None = None

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
                                          ";".join(sorted(rows.source.unique())))
        if allow_proxy and current_members:
            return UniverseResolution(
                as_of, tuple(sorted({s.upper() for s in current_members})),
                UniverseMode.CURRENT_UNIVERSE_PROXY, "current-provider-membership",
                "NOT_TRUE_HISTORICAL_VN100: current membership used for a historical date",
            )
        raise LookupError(f"No point-in-time {index_code} snapshot covers {as_of}")

    def append_snapshot(self, symbols: list[str], effective_from: date, *,
                        index_code: str = "VN100", source: str,
                        effective_to: date | None = None) -> None:
        old = self._load()
        new = pd.DataFrame({
            "index_code": index_code,
            "symbol": sorted({s.upper().strip() for s in symbols}),
            "effective_from": effective_from.isoformat(),
            "effective_to": effective_to.isoformat() if effective_to else "",
            "source": source,
        })
        out = pd.concat([old, new], ignore_index=True) if not old.empty else new
        out["effective_from"] = out["effective_from"].astype(str)
        out["effective_to"] = out["effective_to"].astype(str).replace("NaT", "")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out.drop_duplicates(["index_code", "symbol", "effective_from", "source"]).to_csv(self.path, index=False)
