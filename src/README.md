# VNQuant v3.3 — SSI-Free Runtime

This is a personal research and decision-support platform. It does not
auto-trade or route orders.

## Provider state

- SSI FastConnect is retired and cannot be registered.
- No automated market-data provider is currently admitted.
- Real-data commands require an explicitly selected, admitted provider.
- Without one, doctor and bootstrap stop with `NO_ADMITTED_PROVIDER`.
- Synthetic and test providers are mode-bound and cannot satisfy real mode.
- There is no Yahoo, vnstock, undocumented scraping, or synthetic fallback.

The generic commands are ready for a provider that passes Source Admission:

```powershell
python -m vnquant.jobs.doctor --provider <admitted_provider>
python -m vnquant.jobs.bootstrap --provider <admitted_provider> `
  --start 2015-01-01 --data-dir data
```

At the current admission state both commands fail closed. This is expected
and must not be bypassed by treating fixtures or manual validation sources as
an automated real-data feed.

## Local setup and tests

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-local.txt
python -m pytest -q
```

No SSI credentials are used or required.

## Existing offline workflow

Backtest and pipeline commands consume already validated warehouse artifacts:

```powershell
python -m vnquant.jobs.backtest --data-dir data `
  --costs config/my_broker.yaml --mode conservative
python -m vnquant.jobs.pipeline --data-dir data --publish-dir publish
streamlit run app.py
```

Historical current-membership runs remain explicitly labelled
`CURRENT_UNIVERSE_PROXY`; they are not true point-in-time VN100 backtests.
Existing measured strategy results are synthetic, not real-data validation.

## Historical v3.1 material

The retired v3.1 SSI implementation and report are documented under
`../legacy/README.md`. They are intentionally outside this active source tree
and cannot be imported or packaged. Keep the negative SSI retirement tests;
they enforce this product-policy boundary.
