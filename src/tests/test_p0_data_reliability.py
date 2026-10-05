from __future__ import annotations

from datetime import date

import pytest

from vnquant.data.provider_registry import (
    AdmissionEvidence,
    ProviderRegistry,
    ProviderState,
    ValidationResult,
)
from vnquant.data.providers.dnse import DNSEProvider
from vnquant.data.providers.common import DataProviderErrorCode, ProviderResponseError
from vnquant.data.source_sync import SourceSyncOrchestrator, SyncMode, SyncStatus
from vnquant.ui_status import synchronization_status_view


class HttpResponse:
    def __init__(self, body: str, *, status_code: int = 200, content_type: str = "application/json"):
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.text = body
        self.content = body.encode("utf-8")

    def json(self):
        raise AssertionError("provider code must validate the body before calling response.json()")


class ResponseClient:
    def __init__(self, response):
        self.response = response

    def get_instruments(self, **kwargs):
        return self.response

    def get_ohlc(self, **kwargs):
        return self.response


class ValidClient:
    def get_instruments(self, **kwargs):
        return HttpResponse('{"data":[{"symbol":"FPT"}]}')

    def get_ohlc(self, **kwargs):
        return HttpResponse(
            '{"data":[{"time":1788825600,"open":100,"high":110,'
            '"low":90,"close":105,"volume":1000}]}'
        )


def admitted_registry(provider: DNSEProvider) -> ProviderRegistry:
    evidence = AdmissionEvidence(
        access_basis="test agreement",
        licence_reference="TEST-LICENCE",
        capability_definitions={
            "daily_ohlcv": "test daily bars",
            "current_index_members": "test current members",
            "index_daily_ohlct": "test index bars",
        },
        schema_and_units="fixture schema and units",
        timezone_date_semantics="fixture exchange date",
        raw_adjusted_policy="raw",
        revision_behavior="fixture immutable snapshots",
        quotas="fixture quota",
        lineage_method="fixture payload hash",
        owner="test owner",
        history_depth="fixture history",
        universe_semantics="fixture VN100 membership",
        reviewed_at=date(2026, 10, 5),
        next_review_at=date(2027, 10, 5),
        validation_results=(
            ValidationResult("doctor", True, "fixture-doctor", date(2026, 10, 5)),
            ValidationResult("cross_validation", True, "fixture-cross", date(2026, 10, 5)),
        ),
    )
    registry = ProviderRegistry()
    registry.register(provider, evidence=evidence)
    registry.transition(provider.provider_id, ProviderState.DOCTOR_PASSED)
    registry.transition(provider.provider_id, ProviderState.CROSS_VALIDATED)
    registry.transition(provider.provider_id, ProviderState.ADMITTED)
    return registry


def assert_provider_code(response, expected: DataProviderErrorCode):
    provider = DNSEProvider(client=ResponseClient(response))
    with pytest.raises(ProviderResponseError) as caught:
        provider.fetch_daily_history("FPT", date(2026, 10, 1), date(2026, 10, 5))
    assert caught.value.code is expected
    assert expected.value in str(caught.value)
    return caught.value


def test_data_01_valid_provider_json_is_decoded_without_blind_json_call():
    provider = DNSEProvider(client=ValidClient())

    assert provider.current_index_members() == ["FPT"]
    frame = provider.daily_history("FPT", date(2026, 10, 1), date(2026, 10, 5))

    assert len(frame) == 1
    assert frame.iloc[0].symbol == "FPT"
    assert frame.iloc[0].close == 105


def test_data_02_fpt_html_response_is_typed_and_never_json_parsed():
    error = assert_provider_code(
        HttpResponse("<!DOCTYPE html><html><head><title>Challenge</title></head></html>", content_type="text/html"),
        DataProviderErrorCode.HTML_RESPONSE,
    )
    assert error.status_code == 200


@pytest.mark.parametrize("status", [403, 404, 429, 500])
def test_data_03_to_05_http_errors_are_classified_before_body_parsing(status):
    error = assert_provider_code(
        HttpResponse("<!DOCTYPE html><html>upstream error</html>", status_code=status, content_type="text/html"),
        DataProviderErrorCode.HTTP_ERROR,
    )
    assert error.status_code == status


def test_data_06_malformed_json_is_distinct_from_html():
    assert_provider_code(
        HttpResponse('{"data": [', content_type="application/json"),
        DataProviderErrorCode.INVALID_JSON,
    )


def test_data_07_missing_ohlcv_is_schema_error():
    provider = DNSEProvider(client=ResponseClient(HttpResponse('{"data":[{"time":1788825600,"close":105}]}')))
    fetched = provider.fetch_daily_history("FPT", date(2026, 10, 1), date(2026, 10, 5))

    with pytest.raises(ProviderResponseError) as caught:
        provider.normalize_daily_history(fetched)

    assert caught.value.code is DataProviderErrorCode.SCHEMA_ERROR
    assert "DATA_PROVIDER_SCHEMA_ERROR" in str(caught.value)


def test_ui_01_and_04_html_provider_failure_fails_closed_without_crashing_ui(tmp_path):
    response = HttpResponse(
        "<!DOCTYPE html><html><body>Cloudflare challenge</body></html>",
        content_type="text/html; charset=utf-8",
    )
    provider = DNSEProvider(client=ResponseClient(response))
    report = SourceSyncOrchestrator(
        tmp_path,
        registry=admitted_registry(provider),
        today=lambda: date(2026, 10, 5),
    ).sync(force=True)

    assert report.status == SyncStatus.SYNC_FAILED.value
    assert report.mode == SyncMode.FAILED.value
    assert report.dq_status == "NOT_RUN"
    assert not report.cache_accepted
    assert not report.actionable
    assert "DATA_PROVIDER_HTML_RESPONSE" in report.failure_reason

    view = synchronization_status_view(report)
    assert view.state == "FAILED"
    assert view.severity == "error"
    assert "DATA_PROVIDER_HTML_RESPONSE" in view.primary_message
    assert "blocked" in view.details
