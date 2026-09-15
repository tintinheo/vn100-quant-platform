from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Iterable

import pandas as pd

from vnquant.config import parameter_value, parameters_version


class PublicationState(str, Enum):
    SUPPRESSED = "SUPPRESSED"
    SHADOW_ONLY = "SHADOW_ONLY"
    ELIGIBLE_FOR_ACCEPTANCE_REVIEW = "ELIGIBLE_FOR_ACCEPTANCE_REVIEW"


@dataclass(frozen=True)
class PurgedFold:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    embargo_sessions: int


@dataclass(frozen=True)
class TrialLedger:
    """One identifier per model/parameter variant actually attempted."""

    tried_variants: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(set(self.tried_variants)) != len(self.tried_variants):
            raise ValueError("every tried model/parameter variant needs a unique identifier")

    @property
    def total_trials(self) -> int:
        return len(self.tried_variants)


@dataclass(frozen=True)
class FamilyValidation:
    strategy_family: str
    state: PublicationState
    failures: tuple[str, ...]
    samples: int
    signals_evaluated: int
    filled: int
    fill_rate: float | None
    unfilled_attempts: int
    total_cost: float
    turnover: float
    max_drawdown: float | None
    oos_mean_return: float | None
    fold_positive_rate: float | None
    auc: float | None
    brier_score: float | None
    expected_calibration_error: float | None
    placebo_advantage: float | None
    trials_accounted: int
    parameters_version: str

    def as_dict(self) -> dict:
        value = asdict(self)
        value["state"] = self.state.value
        return value


def purged_forward_folds(
    ordered_dates: Iterable[object], *, horizon: int, test_sessions: int,
    minimum_train_sessions: int, buffer_sessions: int | None = None,
) -> tuple[PurgedFold, ...]:
    """Create expanding forward folds; observations near a boundary are excluded.

    The BRD embargo is ``horizon + buffer``. Dates are de-duplicated so a market
    day, rather than a security row, is the unit of separation.
    """
    dates = tuple(sorted(set(ordered_dates)))
    buffer_sessions = int(buffer_sessions if buffer_sessions is not None else parameter_value("validation.embargo_buffer_sessions"))
    embargo = horizon + buffer_sessions
    if min(horizon, test_sessions, minimum_train_sessions) <= 0:
        raise ValueError("horizon, test_sessions and minimum_train_sessions must be positive")
    folds: list[PurgedFold] = []
    test_start = minimum_train_sessions + embargo
    while test_start + test_sessions <= len(dates):
        train_end = test_start - embargo
        folds.append(PurgedFold(tuple(range(train_end)), tuple(range(test_start, test_start + test_sessions)), embargo))
        test_start += test_sessions
    return tuple(folds)


def _max_drawdown(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    wealth = (1.0 + returns).cumprod()
    return float((wealth / wealth.cummax() - 1.0).min())


def _calibration(rows: pd.DataFrame) -> tuple[float | None, float | None]:
    valid = rows.dropna(subset=["probability", "outcome"]) if {"probability", "outcome"} <= set(rows) else pd.DataFrame()
    if valid.empty:
        return None, None
    p, y = valid.probability.astype(float), valid.outcome.astype(float)
    brier = float(((p - y) ** 2).mean())
    bins = pd.cut(p, bins=[0, .2, .4, .6, .8, 1], include_lowest=True)
    ece = 0.0
    for _, group in valid.assign(_bin=bins).groupby("_bin", observed=True):
        ece += len(group) / len(valid) * abs(float(group.probability.mean()) - float(group.outcome.mean()))
    return brier, float(ece)


def evaluate_strategy_family(
    strategy_family: str, rows: pd.DataFrame, ledger: TrialLedger, *,
    placebo_sharpes: Iterable[float], real_grouping_sharpe: float | None,
    stability_passed: bool, multiple_testing_passed: bool,
    calibration_passed: bool, auc: float | None = None,
) -> FamilyValidation:
    """Evaluate one family's OOS rows and fail closed on every required gate.

    Required columns are ``fold``, ``execution_mode``, ``attempt_status``,
    ``net_return``, ``cost`` and ``turnover``. Optional calibrated forecasts use
    ``probability`` and binary ``outcome``. Callers must pass evidence verdicts
    rather than letting this layer invent stability or testing thresholds.
    """
    required = {"fold", "execution_mode", "attempt_status", "net_return", "cost", "turnover"}
    missing = required - set(rows)
    if missing:
        raise ValueError(f"missing validation columns: {sorted(missing)}")
    signals = len(rows)
    filled_rows = rows[rows.attempt_status == "FILLED"]
    returns = filled_rows.net_return.dropna().astype(float)
    filled = len(filled_rows)
    fill_rate = filled / signals if signals else None
    fold_means = filled_rows.dropna(subset=["net_return"]).groupby("fold").net_return.mean()
    placebo = tuple(float(x) for x in placebo_sharpes)
    advantage = None if real_grouping_sharpe is None or not placebo else float(real_grouping_sharpe - sum(placebo) / len(placebo))
    brier, ece = _calibration(filled_rows)
    failures: list[str] = []
    if len(returns) < int(parameter_value("validation.minimum_samples")): failures.append("INSUFFICIENT_SAMPLE")
    if fill_rate is None or fill_rate < float(parameter_value("validation.minimum_fill_rate")): failures.append("EXECUTION_FILL_RATE")
    if not rows.execution_mode.eq("conservative").all(): failures.append("NON_CONSERVATIVE_EXECUTION")
    if not stability_passed or fold_means.empty: failures.append("STABILITY")
    if ledger.total_trials < 1 or not multiple_testing_passed: failures.append("MULTIPLE_TESTING")
    if advantage is None or advantage < float(parameter_value("validation.minimum_placebo_advantage")): failures.append("GROUPING_PLACEBO")
    forecast_present = auc is not None or brier is not None
    if forecast_present and (auc is None or auc < float(parameter_value("validation.minimum_auc"))): failures.append("FORECAST_AUC")
    if forecast_present and (not calibration_passed or brier is None or ece is None): failures.append("CALIBRATION")
    return FamilyValidation(
        strategy_family, PublicationState.SUPPRESSED if failures else PublicationState.SHADOW_ONLY,
        tuple(failures), len(returns), signals, filled, fill_rate, signals - filled,
        float(filled_rows.cost.fillna(0).sum()), float(filled_rows.turnover.fillna(0).sum()),
        _max_drawdown(returns), float(returns.mean()) if not returns.empty else None,
        float((fold_means > 0).mean()) if not fold_means.empty else None, auc, brier, ece,
        advantage, ledger.total_trials, parameters_version(),
    )


def complete_shadow_period(report: FamilyValidation, *, sessions_observed: int,
                           minimum_sessions: int, no_capital: bool) -> FamilyValidation:
    if report.state is not PublicationState.SHADOW_ONLY:
        raise ValueError("only a validation-passed strategy may enter/complete shadow operation")
    if not no_capital:
        raise ValueError("shadow operation must use no capital")
    if sessions_observed < minimum_sessions:
        return report
    return replace(report, state=PublicationState.ELIGIBLE_FOR_ACCEPTANCE_REVIEW)
