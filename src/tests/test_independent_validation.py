from datetime import date, datetime, timezone
from decimal import Decimal

from vnquant.data.models import CanonicalBar
from vnquant.data.reconciliation import IndependentDataValidator, ReconciliationStatus


def test_two_independent_matching_sources_are_verified():
    result = IndependentDataValidator().evaluate(
        [_bar("primary", "p1"), _bar("validator", "v1")],
        provider_origins={"primary": "origin-a", "validator": "origin-b"},
        expected_latest_session=date(2026, 9, 14),
    )
    assert result.validation_status is ReconciliationStatus.VERIFIED
    assert result.source_names == ("primary", "validator")
    assert result.independent_origins == ("origin-a", "origin-b")
    assert result.price_disagreement == 0
    assert result.volume_disagreement == 0
    assert result.buy_sell_allowed


def test_two_provider_labels_with_same_origin_are_quarantined():
    result = IndependentDataValidator().evaluate(
        [_bar("wrapper-a", "a1"), _bar("wrapper-b", "b1")],
        provider_origins={"wrapper-a": "shared-feed", "wrapper-b": "shared-feed"},
    )
    assert result.validation_status is ReconciliationStatus.QUARANTINED
    assert "INDEPENDENCE_UNPROVEN" in result.issues
    assert not result.buy_sell_allowed


def test_material_cross_source_price_or_volume_mismatch_is_quarantined():
    result = IndependentDataValidator(price_tolerance=0.005, volume_tolerance=0.10).evaluate(
        [
            _bar("primary", "p1"),
            _bar("validator", "v1", close="101", volume=130),
        ],
        provider_origins={"primary": "origin-a", "validator": "origin-b"},
    )
    assert result.validation_status is ReconciliationStatus.QUARANTINED
    assert "DATA_SOURCE_PRICE_MISMATCH" in result.issues
    assert "DATA_SOURCE_VOLUME_MISMATCH" in result.issues
    assert result.price_disagreement > 0.005
    assert result.volume_disagreement > 0.10
    assert not result.buy_sell_allowed


def test_single_source_is_warning_not_verified():
    result = IndependentDataValidator().evaluate(
        [_bar("primary", "p1")],
        provider_origins={"primary": "origin-a"},
    )
    assert result.validation_status is ReconciliationStatus.WARNING
    assert "SINGLE_SOURCE_ONLY" in result.issues
    assert result.overall_quality_score < 100
    assert result.buy_sell_allowed


def test_no_trustworthy_data_is_unavailable_and_blocks_buy_sell():
    result = IndependentDataValidator().evaluate([], provider_origins={})
    assert result.validation_status is ReconciliationStatus.UNAVAILABLE
    assert result.freshness == "UNAVAILABLE"
    assert result.overall_quality_score == 0
    assert result.issues == ("DATA_UNAVAILABLE",)
    assert not result.buy_sell_allowed


def test_stale_independent_data_is_quarantined():
    result = IndependentDataValidator().evaluate(
        [_bar("primary", "p1"), _bar("validator", "v1")],
        provider_origins={"primary": "origin-a", "validator": "origin-b"},
        expected_latest_session=date(2026, 9, 15),
    )
    assert result.validation_status is ReconciliationStatus.QUARANTINED
    assert result.freshness == "STALE"
    assert "DATA_STALE" in result.issues
    assert not result.buy_sell_allowed


def _bar(provider: str, snapshot: str, *, close="100", volume=100) -> CanonicalBar:
    return CanonicalBar(
        timestamp=datetime(2026, 9, 14, tzinfo=timezone.utc),
        symbol="AAA",
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal(close),
        volume=volume,
        turnover=Decimal("10000"),
        adj_close=Decimal(close),
        provider=provider,
        ingested_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
        quality_flags=(),
        raw_snapshot_id=snapshot,
        trust_tier="T1",
        raw_price_unit="VND",
        price_semantics="raw",
        source_reference=f"test://{provider}",
        payload_sha256="a" * 64,
    )
