from __future__ import annotations

from dataclasses import dataclass

from vnquant.data.sector_membership import SectorMode
from vnquant.data.universe import UniverseMode


@dataclass(frozen=True)
class BacktestGovernance:
    result_label: str
    universe_mode: UniverseMode
    sector_mode: SectorMode
    warnings: tuple[str, ...]
    capital_qualification_eligible: bool


def govern_backtest_result(result_label: str, universe_mode: UniverseMode,
                           sector_mode: SectorMode) -> BacktestGovernance:
    historical_claim = "HISTORICAL VN100" in result_label.upper().replace("_", " ")
    if historical_claim and universe_mode is not UniverseMode.STRICT_PIT:
        raise ValueError("historical VN100 backtest requires STRICT_PIT universe mode")
    warnings: list[str] = []
    if universe_mode is UniverseMode.CURRENT_UNIVERSE_PROXY:
        warnings.append("NOT_TRUE_HISTORICAL_VN100: CURRENT_UNIVERSE_PROXY")
    if sector_mode is SectorMode.CURRENT_ICB_PROXY:
        warnings.append("NOT_TRUE_HISTORICAL_SECTOR_CLASSIFICATION: current-sector proxy")
    eligible = universe_mode is UniverseMode.STRICT_PIT and sector_mode is SectorMode.STRICT_PIT
    if not eligible:
        warnings.append("NOT_ELIGIBLE_FOR_REAL_CAPITAL_STRATEGY_QUALIFICATION")
    return BacktestGovernance(result_label, universe_mode, sector_mode, tuple(warnings), eligible)
