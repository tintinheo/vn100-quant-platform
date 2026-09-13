from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from vnquant.data.base import DataMode, MarketDataProvider
from vnquant.data.provider_registry import (
    AdmissionEvidence,
    NO_ADMITTED_PROVIDER,
    NoAdmittedProvider,
    ProviderNotAllowed,
    ProviderRegistry,
    ProviderSelectionRequired,
    ProviderState,
)
from vnquant.jobs.bootstrap import run as run_bootstrap
from vnquant.jobs.doctor import run as run_doctor


ADMISSION_EVIDENCE = AdmissionEvidence(
    doctor_passed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    cross_validated_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
    approval_reference="test-review-only",
)


class StubProvider(MarketDataProvider):
    capabilities = frozenset({"daily_ohlcv", "current_index_members"})

    def __init__(self, provider_id: str, data_mode: DataMode = DataMode.REAL):
        self.provider_id = provider_id
        self.data_mode = data_mode

    def current_index_members(self, index_code: str = "VN100") -> list[str]:
        return ["VNM"]

    def daily_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        raise AssertionError("test selection must not fetch data")


@pytest.mark.parametrize("provider_id", ["ssi", "ssi_fastconnect", "ssi_fastconnect_v3"])
def test_ssi_cannot_become_active_accidentally(provider_id):
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotAllowed, match="retired provider"):
        registry.register(
            StubProvider(provider_id),
            state=ProviderState.ADMITTED,
            documented_access=True,
            admission_evidence=ADMISSION_EVIDENCE,
        )


def test_application_starts_without_ssi_credentials(monkeypatch, capsys):
    for name in ("SSI_CLIENT_ID", "SSI_API_KEY", "SSI_API_SECRET"):
        monkeypatch.delenv(name, raising=False)

    assert run_doctor() == 2
    assert NO_ADMITTED_PROVIDER in capsys.readouterr().out


def test_real_data_ingestion_fails_safely_without_admitted_provider(tmp_path):
    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        run_bootstrap(
            provider_id=None,
            start=date(2026, 1, 1),
            end=date(2026, 1, 2),
            data_dir=str(tmp_path),
        )

    assert list(tmp_path.iterdir()) == []


def test_synthetic_provider_cannot_masquerade_as_real_data():
    registry = ProviderRegistry()
    provider = StubProvider("fixture_generator", DataMode.SYNTHETIC)
    registry.register(
        provider,
        state=ProviderState.ADMITTED,
        documented_access=True,
        admission_evidence=ADMISSION_EVIDENCE,
    )

    with pytest.raises(NoAdmittedProvider, match=NO_ADMITTED_PROVIDER):
        registry.select(
            provider_id="fixture_generator",
            capability="daily_ohlcv",
            mode=DataMode.REAL,
        )
    assert registry.select(
        provider_id="fixture_generator",
        capability="daily_ohlcv",
        mode=DataMode.SYNTHETIC,
    ) is provider


def test_provider_selection_is_explicit():
    registry = ProviderRegistry()
    provider = StubProvider("licensed_feed")
    registry.register(
        provider,
        state=ProviderState.ADMITTED,
        documented_access=True,
        admission_evidence=ADMISSION_EVIDENCE,
    )

    with pytest.raises(ProviderSelectionRequired, match="explicitly"):
        registry.select(provider_id=None, capability="daily_ohlcv")
    assert registry.select(
        provider_id="licensed_feed", capability="daily_ohlcv"
    ) is provider


def test_no_ssi_runtime_dependency_or_module():
    source_root = Path(__file__).parents[1]

    assert "ssi-sdk" not in (source_root / "requirements-local.txt").read_text().lower()
    assert not (source_root / "vnquant" / "data" / "ssi.py").exists()
