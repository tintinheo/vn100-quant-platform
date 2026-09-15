"""UI contract tests for each governed synchronization outcome."""
from vnquant.data.source_sync import SyncReport
from vnquant.ui_status import synchronization_status_view


def report(**overrides):
    values = dict(
        run_id="run", started_at="2026-09-15T00:00:00+00:00",
        finished_at="2026-09-15T00:00:01+00:00", required_capabilities=("daily_ohlcv",),
        provider_id=None, fresh_before=False, remote_fetch_performed=False,
        requested_range=None, canonical_rows_written=0, dq_status="NOT_RUN", dq_score=0,
        last_accepted_market_date=None, last_successful_sync=None, data_age_days=None,
        failure_reason=None, mode="FAILED", actionable=False,
    )
    values.update(overrides)
    return SyncReport(**values)


def test_ui_no_admitted_provider_is_not_a_dq_failure():
    view = synchronization_status_view(report(
        status="NO_ADMITTED_PROVIDER", failure_reason="NO_ADMITTED_PROVIDER",
        next_action="Configure and complete Source Admission for DNSE.",
    ))

    assert view.primary_message == (
        "NO_ADMITTED_PROVIDER — no provider is eligible for real-data synchronization."
    )
    assert "provider: none" in view.details
    assert "data as of: unavailable" in view.details
    assert "last sync: never" in view.details
    assert "DQ: NOT_RUN" in view.details
    assert "cache accepted: no" in view.details
    assert "actionable recommendations: blocked" in view.details
    assert view.next_action == "Configure and complete Source Admission for DNSE."


def test_ui_missing_credentials_reports_sync_not_dq_failure():
    view = synchronization_status_view(report(
        status="SYNC_FAILED", provider_id="dnse_openapi", remote_fetch_performed=True,
        failure_reason="ProviderConfigurationError: missing credentials",
        next_action="Configure DNSE market-data credentials, then retry synchronization.",
    ))
    assert view.state == "FAILED"
    assert "missing credentials" in view.primary_message
    assert "DQ: NOT_RUN" in view.details
    assert view.next_action.startswith("Configure DNSE")


def test_ui_provider_fetch_failure_reports_sync_not_dq_failure():
    view = synchronization_status_view(report(
        status="SYNC_FAILED", provider_id="dnse_openapi", remote_fetch_performed=True,
        failure_reason="RuntimeError: provider outage",
        next_action="Retry synchronization after resolving the provider failure.",
    ))
    assert view.state == "FAILED"
    assert "provider outage" in view.primary_message
    assert "DQ: NOT_RUN" in view.details


def test_ui_genuine_dq_failure_is_labelled_fail():
    view = synchronization_status_view(report(
        status="SYNC_FAILED", provider_id="dnse_openapi", remote_fetch_performed=True,
        failure_reason="RuntimeError: DQ failed for AAA", dq_status="FAIL",
        next_action="Review the blocking data-quality findings before retrying synchronization.",
    ))
    assert view.state == "FAILED"
    assert "DQ: FAIL" in view.details
    assert "data-quality" in view.next_action


def test_ui_stale_accepted_cache_preserves_prior_dq_result():
    view = synchronization_status_view(report(
        status="CACHE_STALE", mode="STALE", provider_id="dnse_openapi",
        data_as_of="2026-09-12", last_sync_at="2026-09-12T10:00:00+00:00",
        dq_status="PASS", dq_score=100, cache_accepted=True, degraded_mode=True,
        failure_reason="NO_ADMITTED_PROVIDER",
        next_action="Configure and complete Source Admission for DNSE.",
    ))
    assert view.state == "STALE"
    assert view.severity == "warning"
    assert "DQ: PASS" in view.details
    assert "cache accepted: yes" in view.details
    assert "actionable recommendations: blocked" in view.details


def test_ui_successful_synchronization_is_fresh_and_actionable():
    view = synchronization_status_view(report(
        status="READY", mode="LIVE", provider_id="dnse_openapi",
        data_as_of="2026-09-15", last_sync_at="2026-09-15T10:00:00+00:00",
        dq_status="PASS", dq_score=100, cache_accepted=True, actionable=True,
    ))
    assert view.state == "FRESH"
    assert view.severity == "success"
    assert "DQ: PASS" in view.details
    assert "actionable recommendations: allowed" in view.details
    assert view.next_action is None
