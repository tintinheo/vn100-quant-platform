# VNQuant v3.1 — Agentic Implementation Report

## Scope implemented in this iteration

1. Effective-dated VN100 universe store with strict/proxy modes.
2. SSI current-index security master including ICB metadata.
3. Current-ICB-vs-point-in-time sector classification boundary.
4. Expanded technical feature baseline: SMA/EMA, Wilder ATR, RSI, ATR%, volume/turnover z-score, displacement/ATR, pullback and conservative reversal proxies.
5. Three-way relative strength: stock/market, stock/sector, sector/market for 20 and 126 sessions plus daily cross-sectional ranks.
6. Equal-weight market breadth, A/D line and turnover confirmation.
7. Regime engine with the v3.1 correction: missing turnover can never confirm Strong/Concentrated Bull.
8. Sector rotation score.
9. Three strategy-family routing skeleton: Trend Pullback, Momentum Continuation, Structural Reversal.
10. Conservative pullback backtest execution audit: signals evaluated, fill/reject reasons and overnight gaps.
11. Streamlit diagnostics for market, candidates, sectors, backtest and proxy warnings.
12. Tests expanded from 9 to 18.

## Important limitations

- Real SSI network calls cannot be executed in this build environment because user credentials are unavailable.
- `pyarrow` and `duckdb` cannot be installed in this sandbox because outbound package download is blocked, so the Parquet/DuckDB end-to-end check must run on the Windows environment after `pip install -r requirements-local.txt`.
- The current pipeline labels VN100 history `CURRENT_UNIVERSE_PROXY` until official effective-dated snapshots are supplied.
- Current SSI ICB is also a historical proxy unless a point-in-time sector file is supplied.
- Official cap-weighted index history is not yet ingested; the current regime pipeline labels its cap-index leg as a proxy rather than silently pretending it is VNINDEX/VN100.
- No ML promotion was performed; simple explainable baselines remain the reference.
