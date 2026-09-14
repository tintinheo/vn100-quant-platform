from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from .models import SectorMembership


REQUIRED_COLUMNS = {
    "symbol", "sector_code", "sector_name", "taxonomy_version",
    "effective_from", "effective_to", "source", "source_snapshot_id",
}


class SectorTaxonomyStore:
    """Effective-dated, source-linked sector classifications."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=sorted(REQUIRED_COLUMNS))
        frame = pd.read_csv(self.path, dtype=str, keep_default_na=False)
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Sector taxonomy missing columns: {sorted(missing)}")
        frame["effective_from"] = pd.to_datetime(frame.effective_from, errors="raise")
        frame["effective_to"] = pd.to_datetime(frame.effective_to.replace("", pd.NA), errors="coerce")
        return frame

    def append(self, records: list[SectorMembership]) -> None:
        if not records:
            raise ValueError("sector taxonomy records cannot be empty")
        incoming = pd.DataFrame([
            {**asdict(record), "taxonomy_version": record.taxonomy}
            for record in records
        ]).drop(columns="taxonomy")
        old = self.load()
        combined = pd.concat([old, incoming], ignore_index=True)
        combined = combined.drop_duplicates([
            "symbol", "taxonomy_version", "effective_from", "effective_to",
            "source_snapshot_id",
        ])
        combined["symbol"] = combined.symbol.str.upper().str.strip()
        if (combined.symbol == "").any():
            raise ValueError("sector taxonomy symbol cannot be empty")
        combined["effective_from"] = pd.to_datetime(combined.effective_from, errors="raise")
        combined["effective_to"] = pd.to_datetime(combined.effective_to, errors="coerce")
        for (_, taxonomy), group in combined.sort_values("effective_from").groupby(["symbol", "taxonomy_version"]):
            previous_end = None
            seen = False
            for row in group.itertuples():
                if seen and previous_end is None:
                    raise ValueError(f"open-ended sector interval overlaps a later interval: {row.symbol}")
                if previous_end is not None and row.effective_from <= previous_end:
                    raise ValueError(f"overlapping sector intervals: {row.symbol}")
                previous_end = row.effective_to if pd.notna(row.effective_to) else None
                seen = True
        combined["effective_from"] = combined.effective_from.dt.date.astype(str)
        combined["effective_to"] = combined.effective_to.dt.date.astype(str).replace("NaT", "")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(self.path, index=False)

    def resolve(self, symbol: str, as_of: date, taxonomy_version: str | None = None) -> SectorMembership:
        frame = self.load()
        ts = pd.Timestamp(as_of)
        rows = frame[(frame.symbol.str.upper() == symbol.upper()) &
                     (frame.effective_from <= ts) &
                     (frame.effective_to.isna() | (frame.effective_to >= ts))]
        if taxonomy_version is not None:
            rows = rows[rows.taxonomy_version == taxonomy_version]
        if len(rows) != 1:
            raise LookupError(f"expected exactly one sector classification for {symbol} at {as_of}")
        row = rows.iloc[0]
        return SectorMembership(row.symbol, row.sector_code, row.sector_name,
                                row.taxonomy_version, row.effective_from.date(),
                                row.effective_to.date() if pd.notna(row.effective_to) else None,
                                row.source, row.source_snapshot_id)
