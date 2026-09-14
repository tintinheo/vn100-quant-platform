from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .models import RawSnapshot
from .storage import Warehouse
from .universe import UniverseStore


@dataclass(frozen=True)
class OfficialReviewImport:
    snapshot_id: str
    member_count: int
    evidence_path: Path


def ingest_vn100_review(
    evidence: bytes,
    *,
    source_reference: str,
    effective_from: date,
    universe_store: UniverseStore,
    warehouse: Warehouse,
    effective_to: date | None = None,
) -> OfficialReviewImport:
    """Ingest a controlled CSV transcription of official HOSE review evidence.

    Required CSV columns are ``symbol`` and ``index_code``. The original bytes
    are stored before any effective-dated records are written.
    """
    if not source_reference.strip():
        raise ValueError("source_reference is required")
    digest = hashlib.sha256(evidence).hexdigest()
    snapshot = RawSnapshot(
        f"hose-vn100-{digest[:16]}", "HOSE_OFFICIAL", datetime.now(timezone.utc),
        evidence, digest, source_reference, {"evidence_type": "VN100_REVIEW"},
        "official-review-csv-v1", "T0_OFFICIAL", "not_applicable", "not_applicable",
    )
    evidence_path = warehouse.store_raw_snapshot(snapshot)
    try:
        rows = list(csv.DictReader(evidence.decode("utf-8-sig").splitlines()))
    except UnicodeDecodeError as exc:
        raise ValueError("official review transcription must be UTF-8 CSV") from exc
    if not rows or not {"symbol", "index_code"}.issubset(rows[0]):
        raise ValueError("official review CSV requires symbol,index_code")
    members = [r["symbol"] for r in rows if r["index_code"].strip().upper() == "VN100"]
    universe_store.append_snapshot(
        members, effective_from, effective_to=effective_to, index_code="VN100",
        source=source_reference, source_snapshot_id=snapshot.snapshot_id,
    )
    return OfficialReviewImport(snapshot.snapshot_id, len(set(members)), evidence_path)
