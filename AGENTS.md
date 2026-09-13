# Agent.md — VN100 Quant Platform Codex Instructions

**Stable filename:** `Agent.md`  
**Current internal revision:** **1.0 — 2026-09-13**

> **Important:** this project intentionally keeps the filename `Agent.md`. Do not rename it. Because Codex may not auto-discover this non-standard filename, every Codex Cloud task must explicitly begin with: **`Read Agent.md first and follow it as repository instructions.`**

## Change Log

| Revision | Date | Change |
|---|---|---|
| **1.0** | **2026-09-13** | **Aligned Codex instructions to stable-document naming and baseline 3.5 DNSE-first auto-sync architecture.** |

## 1. Mission

Build a personal Vietnam equity quantitative research and recommendation application focused on VN100 securities.

The product researches/ranks VN100 stocks, identifies market regime and sector rotation, generates setup/entry/invalidation/target recommendations, performs execution-aware backtests, and may estimate forward-return distributions or calibrated probabilities. It **does not** automatically place orders and **does not** provide an order-routing path.

Target environment: Python, Windows 11, Streamlit, GitHub and Codex Cloud.

## 2. Required reading

Before changing code, read in this order:

1. `Agent.md`
2. `CURRENT_BASELINE.md`
3. `BRD-VN100-Quant-Platform.md`
4. `SRD-VN100-Quant-Platform.md`
5. `PROVIDER-RESEARCH-REPORT.md`

Product-owner companion: `BRD-VN100-Quant-Platform-VI.md`.

Authority order: `CURRENT_BASELINE → BRD → SRD → provider research/ADRs → implementation → tests`.

The BRD is the source of truth for business/trading rules, thresholds and validation policy. The SRD defines how to implement them. Do not invent trading thresholds in source code.

## 3. Stable document policy

Do not create document filenames containing version numbers and do not create `LATEST` aliases. Maintain version/date/change history inside the existing files and in Git history.

For any material research/assessment/implementation change, update BRD English + BRD Vietnamese + SRD in the same PR/work cycle, append their internal Change Logs, update `CURRENT_BASELINE.md` when baseline/state changes, and update the provider report when provider evidence changes.

Any invented, inferred, unsourced or not-yet-verified statement must be marked `[GUESS]`.

## 4. Current baseline

Current internal baseline: **3.5 — SSI-Free DNSE-First Auto-Sync**.

SSI FastConnect is **OUT OF SCOPE / DISABLED**. Do not add `ssi-sdk`, SSI credentials, SSI bootstrap/doctor, or use SSI as primary/fallback/validator.

## 5. Provider policy

### DNSE
DNSE OpenAPI is the leading automated market-data provider candidate `[GUESS]`. A read-only adapter exists in `vn100_multisource_feed_v1`. Allowed work is documented read-only market data. Do not add order placement, trading tokens, OTP/2FA trading flows or brokerage trading functions.

Implementation does not equal admission. Provider state must progress explicitly: `CANDIDATE → DOCTOR_PASSED → CROSS_VALIDATED → ADMITTED`. Do not claim `ADMITTED` or `REAL_DATA_VALIDATED` without live evidence. Keep unverified VN100 index literals, resolution strings, live schema/units, history depth and rate-limit behavior marked `[GUESS]` until verified.

### Vietstock
Vietstock DataFeed is a licensed secondary/alternative candidate `[GUESS]`. Do not reverse-engineer `finance.vietstock.vn` browser/XHR endpoints as production API. Production calls require an authorized contract specifying base URL, auth, endpoint semantics, schema, pagination, units, adjusted/raw semantics, revision policy, rate limits and usage rights. Until then, fail closed.

### CafeF
CafeF is reference / explicit cross-validation by default. It must not silently replace DNSE. Public-page parsing must be opt-in, preserve provenance and fail clearly if layout changes. Do not depend on undocumented private APIs.

## 6. Failover policy

There is **no silent provider fallback**. On provider failure: record it, evaluate accepted cached data, expose `DEGRADED`/`STALE`, and block actionable recommendations when DQ policy requires it. Provider changes must remain visible in lineage. Never average conflicting provider prices just to hide disagreement.

## 7. Auto-sync runtime

Normal use must not require CSV/XLSX import.

`APP START → sync check → expected latest session → local cache → missing/stale window → provider fetch → raw snapshot → normalization → DQ → persistent cache/warehouse → analytics → recommendations`

Auto-refresh does **not** mean full-history download on every Streamlit rerun. Use freshness checks, incremental refresh, cache and locking. CSV/XLSX is secondary only for bootstrap, recovery, debugging, tests, provider comparison or one-off authorized evidence.

## 8. Current implemented subsystem

`vn100_multisource_feed_v1` currently includes provider abstraction, DNSE read-only adapter, Vietstock contract gate, CafeF reference parser, SQLite cache, incremental scanner, DQ checks, disagreement handling and DNSE doctor. Current offline evidence: **10/10 tests passed**. Do not interpret offline tests as live market-data validation.

## 9. Canonical data and lineage

Normalize provider data before analytics and preserve at least: `symbol, trading_date, open, high, low, close, volume, value, adj_close, provider, trust_tier, raw_price_unit, ingested_at`.

Preserve raw provider representation/snapshots where practical. Do not silently mix adjusted/raw prices. Do not infer corporate-action type solely from an adjustment factor.

## 10. Data quality

Validate before features/signals: duplicate `(symbol, trading_date)`, invalid dates, OHLC invariants, negative prices/volume, suspicious gaps, stale data, missing expected sessions, provider disagreement and unresolved corporate actions. Do not silently forward-fill missing prices as if a trade occurred. DQ degradation must propagate to confidence or block actionable recommendations per BRD.

## 11. Point-in-time discipline

Prevent look-ahead, survivorship bias, future VN100 membership leakage, future sector leakage, future corporate-action leakage and future financial-statement leakage. Historical VN100 membership must be effective-dated. Current membership used historically must be labelled as proxy. For fundamentals, `published_at` governs availability, not only `period_end`.

## 12. Quant architecture

Decision hierarchy: `MARKET → REGIME → SECTOR → ARCHETYPE → STRATEGY FAMILY → SETUP → ENTRY TRIGGER → INVALIDATION → EXPECTED VALUE → EXECUTION FEASIBILITY → RECOMMENDATION`.

Core families: Trend Pullback, Momentum Continuation, Structural Reversal / Mean Reversion. Indicators are evidence, not standalone rules. Wyckoff/SMC concepts must be measurable/testable; Elliott is hypothesis support, not deterministic trade logic.

## 13. Forecast policy

Prefer forward return, excess return, probability of outperforming and return distributions over exact point-price claims. Use time-series validation; never random-split financial time series. Prevent label leakage. Suppress models that fail validation; `FORECAST_UNAVAILABLE` is valid.

## 14. Parameter governance

`[S]` structural/regulatory; `[M]` measured; `[A]` academic evidence; `[D]` default requiring calibration; `[GUESS]` invented/inferred/unsourced/unverified.

Any new threshold, heuristic, provider assumption, weight, lookback or cutoff without authoritative evidence must carry `[GUESS]`. Unit tests validate implementation, not alpha.

## 15. Backtest rules

Backtests must be execution-aware. No same-close fill for a signal generated from that close. Do not assume every limit order fills. Model price bands, suspensions, costs, corporate actions and PIT universe. Keep rejected/unfilled attempts auditable. Separate signal date, attempt date, fill date, regulatory sellability and policy earliest exit. `SELL` means reduce/exit long, not naked short.

## 16. Security

Never commit API keys, secrets, tokens, OTPs, signing keys or brokerage passwords. Use environment variables or approved secret store. Never log full secrets. Tests use fake credentials/mocks.

## 17. Forbidden functionality/dependencies

Without explicit product-owner approval, do not introduce `vnstock`, SSI FastConnect, broker order-routing, automatic execution, hidden scraping dependencies, synthetic fallback masquerading as real data, or current-universe historical backtests without proxy warning.

## 18. Development workflow

For every Codex task:

1. read `Agent.md` first;
2. read current baseline + applicable BRD/SRD sections;
3. inspect existing code before editing;
4. state the requirement being implemented;
5. make the smallest coherent change;
6. add unit/regression tests;
7. run relevant tests and broader suite when feasible;
8. review leakage/provider-policy risks;
9. report changed files, assumptions, `[GUESS]` additions and unresolved issues;
10. state real-data validation status honestly;
11. evaluate documentation impact and update stable docs in the same PR when material.

Never claim success solely because code compiles.

## 19. Validation commands

For `vn100_multisource_feed_v1`, run at minimum:

```bash
python -m compileall -q vn100_feed
python -m pytest -q
```

When package installation is part of the task:

```bash
pip install -e . --no-deps --no-build-isolation
```

When approved DNSE credentials are available, run the read-only doctor before promoting provider status. If network/credentials/dependencies are unavailable, report the limitation; never fabricate success.

## 20. Pull-request contract

Every PR must state: Purpose; current baseline; BRD/SRD requirements; changed files; tests/results; data status (`SYNTHETIC_ONLY`, `OFFLINE_TESTED`, `DOCTOR_PASSED`, `CROSS_VALIDATED`, `REAL_DATA_VALIDATED`); all new `[GUESS]`; known limitations; documentation impact. Prefer small reviewable PRs.

## 21. Completion criteria

A task is complete only when requested behavior exists, important tests exist and were run where possible, secrets are absent, provider lineage is preserved, prohibited dependencies are absent, leakage risks were checked, documentation impact was evaluated, and real-data status is stated accurately. Fail-closed behavior is preferable to invented data, silent fallback or false validation.