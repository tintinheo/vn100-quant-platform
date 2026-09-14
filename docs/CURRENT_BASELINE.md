# VN100 Quant Platform — Current Baseline

**Stable file:** `CURRENT_BASELINE.md`  
**Current internal baseline:** **3.5 — SSI-Free DNSE-First Auto-Sync — 2026-09-13**

## Canonical documents

- `Agent.md` — Codex Cloud repository instructions; every task must explicitly read it first.
- `BRD-VN100-Quant-Platform.md` — canonical English business/trading requirements.
- `BRD-VN100-Quant-Platform-VI.md` — Vietnamese business companion.
- `SRD-VN100-Quant-Platform.md` — canonical software requirements.
- `PROVIDER-RESEARCH-REPORT.md` — provider evidence, gaps and decisions.

## Current architecture state

- SSI FastConnect: **OUT OF SCOPE / DISABLED**.
- Leading automated market-data candidate: **DNSE OpenAPI `[GUESS]`** — documented and adapter implemented, but **NOT ADMITTED / NOT LIVE VALIDATED**.
- Licensed secondary/alternative candidate: **Vietstock DataFeed `[GUESS]`** — generic contract-gated adapter implemented; live contract/access pending.
- CafeF: **reference / explicit opt-in validation**, not a silent production fallback or authoritative VN100-membership source.
- Referenced standalone artifact: `vn100_multisource_feed_v1` — **NOT PRESENT IN THIS REPOSITORY**; its documented package-local commands and historical 10/10 result are not reproducible. The maintained implementation is the integrated `src/vnquant/` code and `src/tests/`; its full suite passed 56 offline tests on 2026-09-14.
- Main trading/analytics app: stable provider implementations are now integrated under `src/vnquant/data/providers/` and registered as non-admitted by default; broader legacy v3.1 migration remains pending.
- Runtime integration: application startup and the actionable analytics pipeline now consume a persisted governed sync result; absent an admitted provider or accepted cache, candidate generation fails closed with `NO_ADMITTED_PROVIDER`.
- Real-data validation: **NOT YET PERFORMED**.

## Mandatory governance

After every material research, assessment or implementation discovery:

1. update `BRD-VN100-Quant-Platform.md`;
2. update `BRD-VN100-Quant-Platform-VI.md`;
3. update `SRD-VN100-Quant-Platform.md`;
4. append the change to each document's internal Change Log;
5. update this file if the active baseline/state changed;
6. update `PROVIDER-RESEARCH-REPORT.md` when provider evidence/decision changes;
7. keep unsourced/invented/inferred content labelled `[GUESS]`.

Do **not** create new versioned document filenames or `LATEST` aliases. Git history + internal Change Logs provide revision history.

## Change Log

| Internal baseline | Date | Change |
|---|---|---|
| 3.3 | 2026-09-10 | SSI removed from active architecture. |
| 3.4 | 2026-09-13 | Auto-refresh-on-run / sync-if-stale data ingestion. |
| **3.5** | **2026-09-13** | **DNSE-first provider research + standalone-scanner delivery claim later withdrawn by the 2026-09-14 artifact audit.** |
| **3.5 (integration update)** | **2026-09-13** | **Stable main-package providers registered in non-admitted states; no live-validation or admission status change.** |
| **3.5 (sync-gate update)** | **2026-09-13** | **Persisted source-sync gate integrated beneath startup and actionable analytics; offline regression tested, with no live-validation or admission status change.** |
| **3.5 (artifact audit)** | **2026-09-14** | **Recorded that `vn100_multisource_feed_v1` was never committed here, removed the unreproducible 10/10 claim, and identified `src/vnquant/` as the maintained implementation path. No live-validation or admission status change.** |
