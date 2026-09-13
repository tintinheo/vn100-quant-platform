from __future__ import annotations

from datetime import date

import pytest

from vnquant.data.provider_registry import (
    NoAdmittedProvider,
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
        schema_mapping={
            "symbol": "ticker", "trading_date": "date", "open": "o", "high": "h",
            "low": "l", "close": "c", "volume": "v",
        },
        units={"price_multiplier": 1},
        revision_policy="vendor contract revision clause",
        rate_limits="vendor contract quota",
        usage_rights="authorized for internal research",
    )
    provider = VietstockDataFeedProvider(contract, transport=lambda **kwargs: [{"ticker": "VNM"}])
    registry = default_provider_registry()

    assert provider.current_index_members() == ["VNM"]
    assert registry.registration("vietstock_datafeed").state is ProviderState.CANDIDATE
    assert registry.admitted_provider_ids("current_index_members") == ()


def test_cafef_is_disabled_and_reference_only():
    provider = CafeFReferenceProvider(page_fetcher=lambda url: "<html></html>")
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        provider.daily_history("VNM", date(2026, 9, 8), date(2026, 9, 9))
    assert provider.reference_only is True
    assert "daily_ohlcv" not in provider.capabilities
