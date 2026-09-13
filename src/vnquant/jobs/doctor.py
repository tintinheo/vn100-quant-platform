from __future__ import annotations

import argparse
from datetime import date, timedelta

from vnquant.data.base import DataMode
from vnquant.data.provider_registry import (
    ProviderRegistry,
    ProviderRegistryError,
    default_provider_registry,
)
from vnquant.data.quality import quality_score, validate_bars


def run(
    provider_id: str | None = None,
    symbol: str = "VNM",
    days: int = 90,
    index: str = "VN100",
    registry: ProviderRegistry | None = None,
) -> int:
    """Run a provider-neutral preflight against an admitted real-data source."""
    print("VNQuant Doctor v3.3 — admitted-provider preflight")
    try:
        provider = (registry or default_provider_registry()).select(
            provider_id=provider_id,
            capability="daily_ohlcv",
            mode=DataMode.REAL,
        )
        members = provider.current_index_members(index)
        print(f"[1/3] INDEX {index}: {len(members)} members; sample={members[:8]}")
        end = date.today()
        frame = provider.daily_history(symbol, end - timedelta(days=days * 2), end)
        print(
            f"[2/3] OHLC {symbol}: {len(frame)} rows "
            f"{frame.trading_date.min()}..{frame.trading_date.max()}"
        )
        issues = validate_bars(frame)
        print(f"[3/3] QUALITY: score={quality_score(issues)} issues={[(x.severity, x.code) for x in issues]}")
        provider.close()
        return 1 if any(issue.severity == "ERROR" for issue in issues) else 0
    except ProviderRegistryError as error:
        print(error)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider")
    parser.add_argument("--symbol", default="VNM")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--index", default="VN100")
    args = parser.parse_args()
    raise SystemExit(run(args.provider, args.symbol, args.days, args.index))
