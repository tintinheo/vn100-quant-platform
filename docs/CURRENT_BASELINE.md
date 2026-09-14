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
- Referenced standalone artifact: `vn100_multisource_feed_v1` — **NOT PRESENT IN THIS REPOSITORY**; its documented package-local commands and historical 10/10 result are not reproducible. The maintained implementation is the integrated `src/vnquant/` code and `src/tests/`; its full suite passed 99 offline tests on 2026-09-14.
- Main trading/analytics app: stable provider implementations are now integrated under `src/vnquant/data/providers/` and registered as non-admitted by default; broader legacy v3.1 migration remains pending.
- Provider governance: structured evidence and the enforced `CANDIDATE → DOCTOR_PASSED → CROSS_VALIDATED → ADMITTED` lifecycle now replace the prior boolean access flag; no provider advanced from its prior state.
- Runtime integration: application startup and the actionable analytics pipeline now consume a persisted governed sync result; absent an admitted provider or accepted cache, candidate generation fails closed with `NO_ADMITTED_PROVIDER`.
- Data quality: one canonical service now evaluates ingestion/storage observations, persists revision-linked results and synchronization history, and applies the BRD's `[D]` confidence cap (70) and actionable block threshold (50).
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
| **3.5 (provider hardening)** | **2026-09-14** | **Completed fail-closed provider guardrails for the maintained adapters, including the full authorized Vietstock contract gate and a non-promotable CafeF reference role. All providers remain NOT ADMITTED / NOT LIVE VALIDATED.** |
| **3.5 (admission evidence)** | **2026-09-14** | **Replaced the registry's boolean access flag with structured evidence and enforced lifecycle transitions. Offline suite: 60 passed; no live-validation or provider-admission change.** |
| **3.5 (sync-result enforcement)** | **2026-09-14** | **Made the governed synchronization result mandatory for startup/direct pipeline execution, with explicit `NO_ADMITTED_PROVIDER`, cache/degraded metadata, and stale actionable-artifact suppression. No live-validation or provider-admission change.** |
| **3.5 (sync orchestration completion)** | **2026-09-14** | **Added capability freshness policies, provider/capability watermarks, expected-session resolution, deterministic freshness keys, cross-rerun locking, incremental raw snapshots/canonical merges, force refresh, and persisted per-capability results. Offline tested only; no live-validation or provider-admission change.** |
| **3.5 (raw-evidence contract)** | **2026-09-14** | **Provider/file fetches now retain raw payload and request context before normalization, and canonical writes require persisted raw evidence. Offline tested only; no live-validation or provider-admission change.** |
| **3.5 (canonical DQ service)** | **2026-09-14** | **Unified DQ checks and revision/sync-report persistence and enforced confidence/actionability gates. Offline tested only; no live-validation or provider-admission change.** |
| **3.5 (historical isolation)** | **2026-09-14** | **Quarantined the v3.1 SSI archive/report from imports, builds, dependencies and test discovery; retained negative retirement tests. No provider/admission/live-validation change.** |
| **3.5 (acceptance suite)** | **2026-09-14** | **Implemented BRD §28.7 and SRD §§25.2/26.8 offline acceptance coverage with deterministic, non-network provider fixtures and temporary storage. Full suite: 99 passed; no provider/admission/live-validation change.** |
| **3.5 (status reconciliation)** | **2026-09-14** | **Compared all canonical implementation-status statements with tracked contents and reconciled the five documents: standalone `vn100_multisource_feed_v1` is absent; maintained `src/vnquant/` is implemented and tested offline (99 passed). No live-validation/admission change.** |

## Historical-artifact isolation (2026-09-14)

The v3.1 archive, its embedded SSI adapter and SSI-specific doctor/bootstrap,
and its implementation report are historical/disabled evidence under
`legacy/`; they are not active implementation or validation evidence. Active
package discovery is restricted to `src/vnquant`, build artifacts and
dependencies exclude legacy/SSI inputs, pytest discovery is restricted to
`src/tests`, and checkout imports of `legacy` fail closed. Negative SSI
retirement tests remain required. Provider admission and real-data status are
unchanged.
