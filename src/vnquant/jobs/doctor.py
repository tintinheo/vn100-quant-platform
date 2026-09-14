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
from vnquant.config import parameter_value, parameters_version


def run(
    provider_id: str | None = None,
    symbol: str | None = None,
    days: int | None = None,
    index: str | None = None,
    registry: ProviderRegistry | None = None,
) -> int:
    """Run a provider-neutral preflight against an admitted real-data source."""
    symbol = symbol or str(parameter_value("doctor.symbol"))
    days = int(days if days is not None else parameter_value("doctor.lookback_days"))
    index = index or str(parameter_value("doctor.index"))
    calendar_multiplier = int(parameter_value("doctor.calendar_day_multiplier"))
    sample_size = int(parameter_value("doctor.member_sample_size"))
    print(f"VNQuant Doctor v3.5 — admitted-provider preflight ({parameters_version()})")
    try:
        provider = (registry or default_provider_registry()).select(
            provider_id=provider_id,
            capability="daily_ohlcv",
            mode=DataMode.REAL,
        )
        members = provider.current_index_members(index)
        print(f"[1/3] INDEX {index}: {len(members)} members; sample={members[:sample_size]}")
        end = date.today()
        frame = provider.daily_history(symbol, end - timedelta(days=days * calendar_multiplier), end)
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
    parser.add_argument("--symbol")
    parser.add_argument("--days", type=int)
    parser.add_argument("--index")
    args = parser.parse_args()
    raise SystemExit(run(args.provider, args.symbol, args.days, args.index))
