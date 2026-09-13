from __future__ import annotations

from datetime import date

import pytest

from vnquant.data.provider_registry import (
    NoAdmittedProvider,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderState,
    default_provider_registry,
)
from vnquant.data.providers import (
    CafeFReferenceProvider,
    DNSEProvider,
    VietstockDataFeedContract,
    VietstockDataFeedProvider,
)
from vnquant.data.providers.common import ProviderConfigurationError


class SuccessfulDNSEClient:
    def get_instruments(self, **kwargs):
        return {"data": [{"symbol": "VNM"}]}

    def get_ohlc(self, **kwargs):
        return {
            "data": [
                {
                    "time": 1_788_825_600,
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 1_000,
                }
            ]
        }


def test_default_implementations_are_registered_but_not_admitted():
    registry = default_provider_registry()

    assert registry.registration("dnse_openapi").state is ProviderState.CANDIDATE
    assert registry.registration("vietstock_datafeed").state is ProviderState.CANDIDATE
    assert registry.registration("cafef_reference").state is ProviderState.RESEARCH_ONLY
    assert registry.admitted_provider_ids("daily_ohlcv") == ()
    with pytest.raises(NoAdmittedProvider):
        registry.select(provider_id="dnse_openapi", capability="daily_ohlcv")


def test_dnse_http_success_does_not_promote_admission():
    provider = DNSEProvider(client=SuccessfulDNSEClient())
    registry = default_provider_registry()

    assert provider.current_index_members() == ["VNM"]
    assert not provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9)).empty
    assert registry.registration("dnse_openapi").state is ProviderState.CANDIDATE
    assert registry.admitted_provider_ids("daily_ohlcv") == ()

    with pytest.raises(ProviderNotAllowed, match="requires doctor"):
        ProviderRegistry().register(
            provider,
            state=ProviderState.ADMITTED,
            documented_access=True,
        )


def test_dnse_surface_has_no_brokerage_execution_methods():
    forbidden = {"order", "place_order", "otp", "trading_token", "execute_trade"}
    assert forbidden.isdisjoint(dir(DNSEProvider))


def test_vietstock_incomplete_contract_fails_before_transport():
    transport_called = False

    def transport(**kwargs):
        nonlocal transport_called
        transport_called = True
        return []

    provider = VietstockDataFeedProvider(transport=transport)
    with pytest.raises(ProviderConfigurationError, match="incomplete authorized"):
        provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9))
    assert transport_called is False


def test_authorized_vietstock_http_success_still_does_not_admit_provider():
    contract = VietstockDataFeedContract(
        authorized=True,
        base_url="https://licensed.example",
        authentication={"Authorization": "fake-test-value"},
        paths={"current_index_members": "/members", "daily_history": "/history"},
        parameters={"index_code": "index", "symbol": "ticker", "start": "from", "end": "to"},
        response_record_paths={
            "current_index_members": ("result", "rows"),
            "daily_history": ("result", "rows"),
        },
        schema_mapping={
            "symbol": "ticker", "trading_date": "date", "open": "o", "high": "h",
            "low": "l", "close": "c", "volume": "v",
        },
        units={"price_multiplier": 1, "volume_multiplier": 1, "value_multiplier": 1},
        revision_policy="vendor contract revision clause",
        rate_limits="vendor contract quota",
        usage_rights="authorized for internal research",
    )
    def transport(**kwargs):
        if kwargs["path"] == "/members":
            rows = [{"ticker": "VNM"}]
        else:
            rows = [
                {
                    "date": "2026-09-09",
                    "o": 10,
                    "h": 11,
                    "l": 9,
                    "c": 10.5,
                    "v": 1_000,
                }
            ]
        return {"result": {"rows": rows}}

    provider = VietstockDataFeedProvider(contract, transport=transport)
    registry = default_provider_registry()

    assert provider.current_index_members() == ["VNM"]
    history = provider.daily_history("VNM", date(2026, 9, 9), date(2026, 9, 9))
    assert history.iloc[0]["symbol"] == "VNM"
    assert history.iloc[0]["close"] == 10.5
    assert registry.registration("vietstock_datafeed").state is ProviderState.CANDIDATE
    assert registry.admitted_provider_ids("current_index_members") == ()


def test_cafef_is_disabled_and_reference_only():
    provider = CafeFReferenceProvider(page_fetcher=lambda url: "<html></html>")
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9))
    assert provider.reference_only is True
    assert "daily_ohlcv" not in provider.capabilities


def test_cafef_opt_in_parses_public_html_as_reference_data():
    html = """
    <table><thead><tr>
      <th>Ngày</th><th>Mở cửa</th><th>Cao nhất</th><th>Thấp nhất</th>
      <th>Đóng cửa</th><th>KL khớp lệnh</th>
    </tr></thead><tbody><tr>
      <td>09/09/2026</td><td>10</td><td>11</td><td>9</td><td>10.5</td><td>1000</td>
    </tr></tbody></table>
    """
    provider = CafeFReferenceProvider(
        allow_reference_source=True,
        page_fetcher=lambda url: html,
    )

    frame = provider.daily_history("VNM", date(2026, 9, 9), date(2026, 9, 9))

    assert frame.iloc[0]["close"] == 10_500
    assert frame.iloc[0]["provider"] == "cafef_reference"
