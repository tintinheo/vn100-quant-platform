import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd

from vnquant.data.models import CanonicalBar, QualityStatus, RawSnapshot
from vnquant.data.quality import DataQualityService, apply_dq_policy, validate_bars
from vnquant.data.storage import Warehouse

def test_bad_ohlc_is_blocked():
    df=pd.DataFrame([{"symbol":"X","trading_date":date(2026,1,1),"open":10,"high":9,"low":8,"close":10,"volume":1,"provider":"x"}])
    assert any(x.code=="OHLC_LOGIC" and x.severity=="ERROR" for x in validate_bars(df))


def test_invalid_date_is_blocked():
    frame = _frame(); frame.loc[0, "trading_date"] = "not-a-date"
    assert _has_frame(frame, "INVALID_DATE", "ERROR")


def test_expected_session_and_stale_data_are_blocking():
    bar = _bar()
    tomorrow = bar.timestamp + timedelta(days=1)
    evaluation = DataQualityService().evaluate([bar], expected_sessions={bar.timestamp, tomorrow},
                                                expected_latest_session=tomorrow)
    assert {"MISSING_SESSION", "STALE_DATA"} <= {result.code for result in evaluation.results}
    assert not evaluation.actionable


def test_venue_price_band_breach_is_blocking():
    evaluation = DataQualityService().evaluate([_bar(high="108")], venues={"AAA": "HOSE"},
        venue_bands={"HOSE": Decimal("0.07")}, reference_prices={("AAA", date(2026, 9, 14)): Decimal("100")})
    assert _has(evaluation, "PRICE_BAND_BREACH", QualityStatus.FAIL)


def test_non_trading_status_is_blocking():
    evaluation = DataQualityService().evaluate([_bar()], trading_statuses={("AAA", date(2026, 9, 14)): "SUSPENDED"})
    assert _has(evaluation, "TRADING_STATUS_BLOCKED", QualityStatus.FAIL)


def test_unknown_unit_and_raw_adjusted_semantics_are_blocking():
    evaluation = DataQualityService().evaluate([_bar(raw_price_unit="unknown", price_semantics="unknown")])
    assert {"UNIT_UNKNOWN", "RAW_ADJUSTED_AMBIGUOUS"} <= {result.code for result in evaluation.results}
    assert not evaluation.actionable


def test_missing_lineage_and_non_admitted_provider_are_blocking():
    evaluation = DataQualityService().evaluate([_bar(payload_sha256="unknown", source_reference="unknown")],
                                                admitted_providers={"other"})
    assert {"LINEAGE_MISSING", "PROVIDER_NOT_ADMITTED"} <= {result.code for result in evaluation.results}


def test_provider_disagreement_warns_and_never_averages():
    first, second = _bar(provider="p1", snapshot="s1"), _bar(provider="p2", snapshot="s2", close="101")
    evaluation = DataQualityService().evaluate([first, second])
    assert _has(evaluation, "PROVIDER_DISAGREEMENT", QualityStatus.WARN)
    assert first.close == Decimal("100") and second.close == Decimal("101")


def test_unresolved_corporate_action_is_blocking():
    evaluation = DataQualityService().evaluate([_bar()], unresolved_corporate_actions={("AAA", date(2026, 9, 14))})
    assert _has(evaluation, "UNRESOLVED_CORPORATE_ACTION", QualityStatus.FAIL)


def test_dq_confidence_cap_and_actionable_thresholds():
    assert apply_dq_policy(88, 69) == (69.0, True)
    assert apply_dq_policy(88, 49) == (49.0, False)
    assert apply_dq_policy(88, 70) == (88, True)


def test_dq_results_and_canonical_revision_are_persisted(tmp_path):
    wh = Warehouse(tmp_path)
    evaluation = DataQualityService().evaluate([_bar(raw_price_unit="unknown")])
    wh.persist_dq_evaluation(evaluation, sync_run_id="run-1")
    summaries = wh.read_table("dq_evaluations")
    results = wh.read_table("data_quality_results")
    assert summaries.loc[0, "canonical_revision"] == evaluation.canonical_revision
    assert results.loc[0, "sync_run_id"] == "run-1"


def _frame():
    return pd.DataFrame([{"symbol":"AAA", "trading_date":date(2026,9,14), "open":100,
        "high":101, "low":99, "close":100, "volume":1, "provider":"p1"}])


def _has_frame(frame, code, severity):
    return any(issue.code == code and issue.severity == severity for issue in validate_bars(frame))


def _has(evaluation, code, status):
    return any(result.code == code and result.status == status for result in evaluation.results)


def _bar(*, provider="p1", snapshot="s1", **changes):
    values = dict(timestamp=datetime(2026,9,14,tzinfo=timezone.utc), symbol="AAA",
        open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"),
        volume=100, turnover=Decimal("10000"), adj_close=Decimal("100"), provider=provider,
        ingested_at=datetime(2026,9,14,tzinfo=timezone.utc), quality_flags=(),
        raw_snapshot_id=snapshot, trust_tier="T1", raw_price_unit="VND", price_semantics="raw",
        source_reference="test://bars", payload_sha256="a" * 64)
    for key, value in changes.items():
        values[key] = Decimal(value) if key in {"open","high","low","close","adj_close"} else value
    return CanonicalBar(**values)
