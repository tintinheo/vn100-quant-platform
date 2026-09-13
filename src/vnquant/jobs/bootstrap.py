from __future__ import annotations

import argparse
from datetime import date

import pandas as pd

from vnquant.data.base import DataMode
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
    members = provider.current_index_members("VN100")
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
        frame = provider.daily_history(symbol, start, end)
        issues = validate_bars(frame)
        if any(issue.severity == "ERROR" for issue in issues):
            print(
                f"[{position}/{len(members)}] {symbol}: BLOCKED "
                f"{[(issue.code, issue.message) for issue in issues]}"
            )
            continue
        output = wh.write_bars(frame, symbol)
        print(f"[{position}/{len(members)}] {symbol}: {len(frame)} rows -> {output}")
    provider.close()
    wh.build_duckdb_views()
    return 0


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
