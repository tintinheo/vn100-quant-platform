import pandas as pd
import pytest

from vnquant.backtest.validation import (
    PublicationState, TrialLedger, complete_shadow_period,
    evaluate_strategy_family, purged_forward_folds,
)


def _rows(n=30, *, filled=24):
    return pd.DataFrame({
        "fold": [i // 10 for i in range(n)],
        "execution_mode": ["conservative"] * n,
        "attempt_status": ["FILLED"] * filled + ["UNFILLED"] * (n - filled),
        "net_return": [.01] * filled + [None] * (n - filled),
        "cost": [100.0] * n,
        "turnover": [10000.0] * n,
        "probability": [.6] * n,
        "outcome": [1] * n,
    })


def test_purged_forward_folds_use_horizon_plus_specified_embargo():
    folds = purged_forward_folds(range(100), horizon=5, test_sessions=10, minimum_train_sessions=30)
    assert folds[0].embargo_sessions == 26
    assert max(folds[0].train_indices) == 29
    assert min(folds[0].test_indices) == 56


def test_family_report_accounts_attempts_costs_trials_and_suppresses_thin_sample():
    report = evaluate_strategy_family(
        "TREND_PULLBACK", _rows(), TrialLedger(tuple(f"variant-{i}" for i in range(6))),
        placebo_sharpes=[.1, .2], real_grouping_sharpe=.5,
        stability_passed=True, multiple_testing_passed=True,
        calibration_passed=True, auc=.6,
    )
    assert report.state is PublicationState.SUPPRESSED
    assert report.samples == 24 and report.unfilled_attempts == 6
    assert report.fill_rate == .8 and report.total_cost == 2400
    assert report.trials_accounted == 6
    assert "INSUFFICIENT_SAMPLE" in report.failures


def test_each_family_must_pass_before_no_capital_shadow_and_review():
    report = evaluate_strategy_family(
        "MOMENTUM_CONTINUATION", _rows(40, filled=32), TrialLedger(("logit:declared",)),
        placebo_sharpes=[.1, .15], real_grouping_sharpe=.5,
        stability_passed=True, multiple_testing_passed=True,
        calibration_passed=True, auc=.6,
    )
    assert report.state is PublicationState.SHADOW_ONLY
    assert complete_shadow_period(report, sessions_observed=19, minimum_sessions=20, no_capital=True).state is PublicationState.SHADOW_ONLY
    assert complete_shadow_period(report, sessions_observed=20, minimum_sessions=20, no_capital=True).state is PublicationState.ELIGIBLE_FOR_ACCEPTANCE_REVIEW
    with pytest.raises(ValueError, match="no capital"):
        complete_shadow_period(report, sessions_observed=20, minimum_sessions=20, no_capital=False)
