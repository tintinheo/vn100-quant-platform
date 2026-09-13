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
- Executable data subsystem: `vn100_multisource_feed_v1` — **IMPLEMENTED + TESTED_OFFLINE, 10/10 PASS**.
- Main trading/analytics app: legacy v3.1 remains to be migrated/integrated with the new module.
- Real-data validation: **NOT YET PERFORMED**.
- Provider admission registry: **3.5.1 lifecycle/evidence gates implemented and offline-tested**; no provider has thereby been admitted or real-data validated.

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
| **3.5** | **2026-09-13** | **DNSE-first provider research + implemented/offline-tested multi-source scanner.** |
| **3.5.1** | **2026-09-13** | **Persisted provider-admission evidence and mandatory doctor/cross-validation lifecycle gates implemented.** |
