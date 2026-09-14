from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hashlib
import json

import pandas as pd

from vnquant.data.base import DataMode
from vnquant.data.models import CanonicalBar, RawSnapshot
from vnquant.data.provider_registry import (
    ProviderRegistry,
    ProviderRegistryError,
    default_provider_registry,
)
from vnquant.data.quality import validate_bars
from vnquant.data.storage import Warehouse


def run(
    *,
    provider_id: str | None,
    start: date,
    end: date,
    data_dir: str,
    registry: ProviderRegistry | None = None,
) -> int:
    """Ingest real data only from the explicitly selected admitted provider."""
    active_registry = registry or default_provider_registry()
    provider = active_registry.select(
        provider_id=provider_id,
        capability="daily_ohlcv",
        mode=DataMode.REAL,
    )
    if "current_index_members" not in provider.capabilities:
        raise ProviderRegistryError("selected provider cannot resolve current index members")

    wh = Warehouse(data_dir)
    universe_fetch = provider.fetch_current_index_members("VN100")
    universe_snapshot = _snapshot(universe_fetch)
    wh.store_raw_snapshot(universe_snapshot)
    members = provider.normalize_index_members(universe_fetch)
    security_master = pd.DataFrame(
        {"symbol": members, "index_code": "VN100", "provider": provider.provider_id}
    )
    wh.write_table(security_master, "security_master")
    wh.write_table(
        security_master.assign(snapshot_date=end.isoformat()), "universe_current"
    )
    print(
        f"Current VN100 members: {len(members)}. Historical use is "
        "CURRENT_UNIVERSE_PROXY unless PIT snapshots are supplied."
    )
    for position, symbol in enumerate(members, 1):
        fetched = provider.fetch_daily_history(symbol, start, end)
        snapshot = _snapshot(fetched)
        # This ordering is a hard lineage boundary: parsing and canonical writes
        # are forbidden until immutable raw evidence exists.
        wh.store_raw_snapshot(snapshot)
        frame = provider.normalize_daily_history(fetched)
        issues = validate_bars(frame)
        if any(issue.severity == "ERROR" for issue in issues):
            print(
                f"[{position}/{len(members)}] {symbol}: BLOCKED "
                f"{[(issue.code, issue.message) for issue in issues]}"
            )
            continue
        bars = [_canonical_bar(row, fetched, snapshot) for _, row in frame.iterrows()]
        output = wh.append_canonical_bars(bars)
        print(f"[{position}/{len(members)}] {symbol}: {len(frame)} rows -> {output}")
    provider.close()
    wh.build_duckdb_views()
    return 0


def _snapshot(fetched) -> RawSnapshot:
    digest = hashlib.sha256(fetched.payload).hexdigest()
    identity = json.dumps({"retrieved_at": fetched.retrieved_at.isoformat(),
        "request_parameters": fetched.request_parameters, "adapter_version": fetched.adapter_version,
        "source_reference": fetched.source_reference}, sort_keys=True).encode()
    snapshot_id = f"{fetched.provider}-{hashlib.sha256(identity).hexdigest()[:24]}"
    return RawSnapshot(snapshot_id, fetched.provider, fetched.retrieved_at, fetched.payload,
        digest, fetched.source_reference, dict(fetched.request_parameters),
        fetched.adapter_version, fetched.trust_tier, fetched.raw_price_unit,
        fetched.price_semantics)


def _decimal(value):
    return None if pd.isna(value) else Decimal(str(value))


def _canonical_bar(row, fetched, snapshot: RawSnapshot) -> CanonicalBar:
    timestamp = datetime.combine(row.trading_date, time.min, tzinfo=timezone.utc)
    return CanonicalBar(
        timestamp=timestamp, symbol=str(row.symbol), open=_decimal(row.open),
        high=_decimal(row.high), low=_decimal(row.low), close=_decimal(row.close),
        volume=int(row.volume), turnover=_decimal(row.get("value")),
        adj_close=_decimal(row.get("adj_close")), provider=fetched.provider,
        ingested_at=fetched.retrieved_at, quality_flags=(),
        raw_snapshot_id=snapshot.snapshot_id, trust_tier=fetched.trust_tier,
        raw_price_unit=fetched.raw_price_unit, price_semantics=fetched.price_semantics,
        request_parameters=json.dumps(fetched.request_parameters, sort_keys=True),
        adapter_version=fetched.adapter_version, source_reference=fetched.source_reference,
        payload_sha256=snapshot.payload_sha256,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default=str(date.today()))
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()
    try:
        return run(
            provider_id=args.provider,
            start=date.fromisoformat(args.start),
            end=date.fromisoformat(args.end),
            data_dir=args.data_dir,
        )
    except ProviderRegistryError as error:
        print(error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
