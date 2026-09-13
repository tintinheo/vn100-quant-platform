# VNQuant v3.1 — Real-Data Ready Phase 1

This bundle implements the corrected Phase-1 foundation for a VN100 research/recommendation platform. It **does not auto-trade** and intentionally requests only SSI market-data authentication (no OTP/private trading key).

## What is real vs not yet proven

- **Real provider contract:** SSI FastConnect v3 via the official `ssi-sdk` Python package.
- **Real-data code path:** current VN100 discovery + historical daily OHLCV + canonical validation + Parquet/DuckDB warehouse.
- **Not executed in this build environment:** SSI network calls, because no user credentials/network access were available here.
- **Backtest supplied:** conservative EOD pullback baseline; when run on the current-membership universe it is explicitly labelled `CURRENT_UNIVERSE_PROXY`, not a true historical VN100 backtest.

## 1. Windows 11 setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-local.txt
```

Copy `.env.example` values into your Windows environment or a local secret file that is not committed:

```powershell
$env:SSI_CLIENT_ID="..."
$env:SSI_API_KEY="..."
$env:SSI_API_SECRET="..."
```

Do **not** configure OTP or trading private keys for this application.

## 2. Doctor first

```powershell
python -m vnquant.jobs.doctor --symbol SSI --index VN100
```

This validates authentication, VN100 discovery, daily OHLCV shape, and basic data quality. It is a connectivity/schema smoke test, not a proof that every security and corporate action is correct.

## 3. Bootstrap current VN100 real OHLCV

```powershell
python -m vnquant.jobs.bootstrap --start 2015-01-01 --data-dir data
```

The current-membership list is suitable for current scanning. Historical results using it are **survivorship-biased** unless you populate effective-dated official VN100 snapshots under `config/universe/`.

## 4. Configure your actual broker costs

Copy `config/broker_costs.example.yaml` and set the tariff from your broker. The key `commission_includes_exchange_fee` prevents double-counting the 0.027% exchange trading-service fee when the broker's quoted commission already includes it.

## 5. Run the conservative baseline backtest

```powershell
python -m vnquant.jobs.backtest --data-dir data --costs config/my_broker.yaml --mode conservative
```

Execution semantics:
- signal after close T;
- buy can fill only on next-session OHLC;
- exact low-touch is **not** assumed filled in conservative mode;
- regulatory sellability is recorded at entry trade date + 2 trading sessions (13:00 T+2);
- because this is an EOD strategy, its conservative policy evaluates after that settlement day's close and executes from the next session;
- urgent exits can remain unfilled on a modeled floor-lock day.

## 6. Streamlit

```powershell
streamlit run app.py
```

Community Cloud should remain a read-only viewer of sanitized artifacts. Do not put SSI credentials, capital figures, or the local warehouse in the hosted app.

## Corporate actions

Adjustment-factor jumps are **anomaly detectors only**. They never classify a cash dividend/stock dividend/rights issue. `action_type` must come from official VSDC/HOSE/issuer disclosures; the adjusted/raw factor is used as a validation cross-check.

## Strict historical VN100 mode

Before calling a result a historical VN100 backtest, add effective-dated official membership snapshots. Until then every backtest is labelled `CURRENT_UNIVERSE_PROXY / NOT_TRUE_HISTORICAL_VN100`.

## Tests

```powershell
pytest -q
```

## 7. Compute market/sector context and candidates

After bootstrap:

```powershell
python -m vnquant.jobs.pipeline --data-dir data --publish-dir publish
```

If you have a verified effective-dated sector file:

```powershell
python -m vnquant.jobs.pipeline --data-dir data --publish-dir publish `
  --sector-pit config/sector/sector_membership.csv
```

Without it, the output is explicitly tagged `CURRENT_ICB_PROXY`.

The pipeline currently produces:

- `publish/market.json`
- `publish/sector_scores.csv`
- `publish/candidates.csv`

The current cap-index leg remains labelled a proxy until official cap-weighted index history is ingested. It is not silently presented as VNINDEX/VN100 history.

## 8. Backtest execution audit

The baseline backtest now writes both filled trades and an execution audit:

```text
publish/backtest_current_universe_proxy.csv
publish/backtest_current_universe_proxy_execution_audit.csv
```

The audit records signals evaluated, fill/reject status, rejection reason and overnight gap. Use this to reject strategies with unrealistic fill rates even when their filled-trade equity curve looks attractive.

## 9. Tests

Use the module form so the repository root is always importable:

```powershell
python -m pytest -q
```

Current implementation build: **18 tests passing** in the build environment.
