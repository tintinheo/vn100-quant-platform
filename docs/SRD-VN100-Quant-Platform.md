# SRD — VN100 Quant Research & Recommendation Platform

**Software Requirements Document · Stable filename · Current internal version 3.5**

| | |
|---|---|
| File | `SRD-VN100-Quant-Platform.md` |
| Current internal version | **3.5 — SSI-FREE DNSE-FIRST AUTO-SYNC — 2026-09-13** |
| Companion | `BRD-VN100-Quant-Platform.md` — read that first |
| Basis | Current BRD + source-governance research + implemented/offline-tested multi-source feed module |
| Reality check | **The main app and actionable pipeline now invoke a persisted source-sync gate. Providers remain offline-tested only; none is production-admitted or live-data validated.** |

## Document Control & Change Log

**Filename policy:** this document keeps a stable filename. Versions are recorded **inside the document**; future updates must modify this same file instead of creating versioned filenames or `LATEST` aliases.

| Internal version | Date | Material change |
|---|---|---|
| 3.0 | 2026-09-09 | Consolidated BRD/SRD and hierarchical quant architecture. |
| 3.1 | 2026-09-10 | Real-data-ready corrections: execution/settlement/cost realism, PIT discipline, provider boundary and validation honesty. |
| 3.2 | 2026-09-10 | Multi-source data governance, provider trust tiers, source-admission/reconciliation rules. |
| 3.3 | 2026-09-10 | SSI FastConnect removed from active architecture; SSI-Free baseline. |
| 3.4 | 2026-09-13 | Auto-refresh-on-run requirement: sync-if-stale, cache, fail-safe; CSV/XLSX demoted to fallback/debug. |
| **3.5** | **2026-09-13** | **DNSE-first auto-sync research and implementation: read-only DNSE adapter, CafeF reference validator, Vietstock contract gate, SQLite incremental scanner, with an offline-test claim later withdrawn by the 2026-09-14 artifact audit. No live-data validation claim.** |
| **3.5.1** | **2026-09-13** | **Integrated DNSE, contract-gated Vietstock, and disabled/reference-only CafeF under `src/vnquant/data/providers/`; default registry is non-admitted and admission is not derived from HTTP success.** |
| **3.5.2** | **2026-09-13** | **Implemented persisted source-sync orchestration for startup and actionable pipeline execution, explicit stale/degraded cache metadata, and fail-closed candidate gating.** |
| **3.5.3** | **2026-09-14** | **Repository audit found that `vn100_multisource_feed_v1` was never committed; removed its unreproducible offline result and made `src/vnquant/` the documented implementation path. No live-validation/admission change.** |
| **3.5.4** | **2026-09-14** | **Completed the provider contract guardrails: DNSE is explicitly read-only with all unverified live assumptions tagged `[GUESS]`; Vietstock validates endpoint semantics and retention rights before I/O; CafeF is ineligible for admission.** |
| **3.5.5** | **2026-09-14** | **Implemented structured admission evidence, evidence-gated lifecycle transitions, suspension/revalidation, and regression coverage for incomplete or ineligible sources.** |
| **3.5.6** | **2026-09-14** | **Required the persisted synchronization result at both runtime entry points, added explicit cache-acceptance/degraded fields, and made blocked pipeline publication invalidate stale candidate/sector artifacts. Offline tested only.** |
| **3.5.7** | **2026-09-14** | **Implemented the complete application sync-service mechanics: capability/provider resolution, independent persisted watermarks and policies, expected-session calculation, deterministic freshness keys, cross-rerun locking, incremental/recheck fetch, immutable raw snapshots, idempotent canonical merges, force refresh, and persisted per-capability results. Offline tested only.** |
| **3.5.8** | **2026-09-14** | **Implemented raw-first provider fetch results, evidence-before-normalization/canonical-write ordering, full canonical lineage fields, and exact-byte hashing/snapshotting for authorized price and universe files. Offline tested only.** |
| **3.5.9** | **2026-09-14** | **Made `DataQualityService` the canonical DQ implementation; added date/session/staleness/band/status/unit/semantics/lineage/admission/disagreement/corporate-action checks, append-only revision-linked DQ and sync reports, and pipeline/recommendation DQ gates. Offline tested only.** |
| **3.5.10** | **2026-09-14** | **Quarantined the historical v3.1 SSI archive/report behind package, built-distribution, dependency, import, and pytest-discovery checks while retaining negative SSI retirement coverage.** |
| **3.5.11** | **2026-09-14** | **Implemented the §§25.2/26.8 offline acceptance harness with deterministic injectable clocks, fake DNSE SDK calls, an injected Vietstock contract fixture, local CafeF HTML, temporary warehouses, raw-order/lineage assertions, idempotence, and concurrent-rerun coverage. Full suite: 99 passed; admission/live-validation status is unchanged.** |

**Governance:** after every material research/assessment/implementation discovery, update BRD + BRD-VI + SRD in the same work cycle, append one row to each document's Change Log, and update `CURRENT_BASELINE.md`. Unsourced/inferred statements must be marked `[GUESS]`.

---

## 0. SCOPE AND RELATIONSHIP TO THE BRD

The BRD is the **single source of truth for every trading rule and
threshold**. This document specifies how to build the system that implements
them. It must never derive a threshold of its own — where a number appears
here, it references the BRD section that defines it.

Tags follow the BRD: `[S]` structural, `[M]` measured, `[A]` academic, `[D]`
default requiring calibration (equivalent to `[GUESS]` in the v2 SAD).

### 0.1. What changed from the v2 SAD, and why

| Change | Reason |
|---|---|
| Dependency stack reduced to nine packages | At VN100 scale (~375,000 rows) every engine is sub-second; the performance case for a heavier stack does not exist |
| Column identity **detected**, not assumed | "Verify the layout on first run" is a hope, not a design. A silent mis-parse is the worst available failure mode |
| A diagnostic command added as the first entry point | Makes a layout surprise a five-minute fix rather than an afternoon |
| Weight fitting restricted to regime level | The `regime × sector × archetype` grid yields ~9 signals per cell — see BRD §5.2 |
| Dual-stop system retained but reinterpreted | Sizing stop is a tail-stress device; T+2 sellability and EOD policy dates are modelled separately |
| Deflated Sharpe and placebo test added to validation | The hierarchical design's trial count is in the hundreds |

---

## TABLE OF CONTENTS

| § | Section |
|---|---|
| [1](#1-deployment-reality) | Deployment reality |
| [2](#2-architecture) | Architecture |
| [3](#3-repository-layout) | Repository layout |
| [4](#4-dependencies) | Dependencies |
| [5](#5-environment) | Environment |
| [6](#6-data-layer) | Data layer |
| [7](#7-storage-schema) | Storage schema |
| [8](#8-feature-engine) | Feature engine |
| [9](#9-classification-engine) | Classification engine |
| [10](#10-regime-and-sector-engines) | Regime and sector engines |
| [11](#11-strategy-registry-and-weight-policy) | Strategy registry and weight policy |
| [12](#12-signal-engine) | Signal engine |
| [13](#13-execution-simulation-and-backtest) | Execution simulation and backtest |
| [14](#14-calibration-loop) | Calibration loop |
| [15](#15-forecast-engine) | Forecast engine |
| [16](#16-validation-harness) | Validation harness |
| [17](#17-user-interface) | User interface |
| [18](#18-scheduling-and-operations) | Scheduling and operations |
| [19](#19-testing) | Testing |
| [20](#20-runbook) | Runbook |
| [21](#21-migration-plan) | Migration plan |
| [22](#22-known-limitations) | Known limitations |
| [23](#23-v33-specification-status-implementation-evidence-and-verification-sources) | v3.3 status & verification sources |
| [24](#24-research--assessment--brdsrd-synchronization-contract-guess) | Research/assessment → BRD/SRD synchronization contract |
| [25](#25-ssi-free-runtime-migration-contract-guess) | SSI-free runtime migration contract |

---

# 1. DEPLOYMENT REALITY

## 1.1. Platform constraints

| Constraint | Value | Consequence |
|---|---|---|
| Memory (hosted free tier) | ~1 GB | Cannot compute a universe of features; load pre-computed data only |
| Filesystem (hosted) | **Ephemeral** | Cannot be the datastore; runtime writes are lost |
| Sleep (hosted) | ~12 quiet hours | No reliable in-process scheduler |
| Cron (hosted) | Unavailable | Scheduling must be external |
| System packages (hosted) | Unreliable | Nothing requiring C compilation |

**The hosted front end is a viewer, not a compute environment.** This is the
correct division of labour, not a limitation to route around.

## 1.2. Compute plane: local workstation

| Property | Local | Cloud CI | Hosted UI |
|---|---|---|---|
| Fixed local-time schedule | ✅ Task Scheduler | ⚠️ UTC cron, drift | ❌ |
| Durable storage | ✅ Unlimited | ⚠️ repo limits | ❌ ephemeral |
| Job duration | Unbounded | 6h cap | seconds |
| Capital figures stay private | ✅ Never leave the machine | ⚠️ repo secrets | ⚠️ cloud secrets |
| Disabled after inactivity | Never | After 60 days | n/a |
| Machine must be powered on | ⚠️ ~15:10–16:00 local | No | n/a |

The single tradeoff is mitigated by `catch_up()` (§18.3): gaps are detected
and rebuilt from the full-history archive, so a week offline costs nothing.

## 1.3. Deployment tiers

| Tier | Setup | When |
|:---:|---|---|
| **0** | Local only. No cloud account. | Build and validate here first |
| **1** | Local compute + publish + hosted read-only view | To check signals on a phone |
| **2** | Tier 1 + cloud fallback pipeline | Only if the machine is often off |

---

# 2. ARCHITECTURE

## 2.1. Two planes, one codebase

```
╔═══════════════════════════════════════════════════════════════════╗
║  COMPUTE PLANE — local workstation, scheduled, durable storage    ║
╠═══════════════════════════════════════════════════════════════════╣
║  15:15 local, weekdays                                            ║
║   1  download EOD archives                                        ║
║   2  DETECT column layout → parse → validate            (§6.2)    ║
║   3  derive corporate actions from adjusted/raw ratio   (§6.4)    ║
║   4  compute features + equal-weight index + breadth    (§8)      ║
║   5  profile securities, fit archetypes                 (§9)      ║
║   6  regime (dual index + turnover confirmation)        (§10.1)   ║
║   7  sector leadership + three-benchmark RS             (§10.2)   ║
║   8  resolve weight policy by regime                    (§11)     ║
║   9  seven-gate signal engine → order tickets           (§12)     ║
║  10  exit engine → alerts, locked-breach warnings                 ║
║  11  forecast engine for the most liquid names          (§15)     ║
║  12  write privacy-scrubbed artifacts → publish → notify          ║
║                                                                    ║
║  08:45 gap-check reminder · Sat weekly · quarterly full rebuild   ║
╚═══════════════════════════════╤═══════════════════════════════════╝
                                │  ~15 MB, no capital figures
                                ▼
╔═══════════════════════════════════════════════════════════════════╗
║  STORAGE — versioned artifact branch                              ║
╚═══════════════════════════════╤═══════════════════════════════════╝
                                │  HTTPS, cached
                                ▼
╔═══════════════════════════════════════════════════════════════════╗
║  VIEW PLANE — hosted, read-only, renders and nothing else         ║
╚═══════════════════════════════════════════════════════════════════╝

   Same codebase in local mode: reads the warehouse directly,
   writes the journal, can trigger the pipeline.
```

## 2.2. Logical layering — hierarchical engine

```
┌───────────────────────────────────────────────────────────┐
│  UI: Market · Sector · Screener · Ticker · Backtest · DQ  │
└───────────────────────────┬───────────────────────────────┘
┌───────────────────────────▼───────────────────────────────┐
│  Use cases: scan · recommend · explain · compare · test   │
└──────────┬──────────────────────────────────┬─────────────┘
    ┌──────▼───────┐                   ┌──────▼───────────┐
    │ Regime engine│                   │ Risk / execution │
    │ breadth      │                   │ limits, slippage │
    │ concentration│                   │ T+1 fill, T+2    │
    └──────┬───────┘                   └──────┬───────────┘
    ┌──────▼──────────────────────────────────▼───────────┐
    │  Sector / archetype ROUTING and WEIGHT POLICY       │
    │  routing: full hierarchy · fitting: regime only     │
    └──────┬──────────────────────────────────────────────┘
   ┌───────▼─────────────┐        ┌──────────────────────┐
   │ Universal feature   │        │ Valuation strategy   │
   │ engine (normalised) │        │ registry by industry │
   └───────┬─────────────┘        └──────────┬───────────┘
           └───────────────┬──────────────────┘
                ┌──────────▼──────────┐
                │ Recommendation eng. │
                └──────────┬──────────┘
                ┌──────────▼──────────┐
                │ DQ / liquidity gates│
                └──────────┬──────────┘
                     Decision support
```

## 2.3. Architecture Decision Records

**ADR-1 — Modular monolith, not microservices.** For a single-user research
tool: simpler deployment, easier debugging, clear internal boundaries for
later extraction. *Accepted.*

**ADR-2 — No single weight vector across VN100.** Production routes by
regime, sector and archetype. The fixed-weight engine remains as
`model_version = mvp_fixed_v1`, a benchmark only. New code must never branch
on `if symbol == "..."`. *Accepted; parameters remain `[D]`.*

**ADR-3 — Weight fitting confined to regime level.** The full hierarchy is
used for routing and gating, which costs no data. Fitting requires ≥30
signals per cell; only the regime partition satisfies that (BRD §5.2).
*Accepted.*

**ADR-4 — Column identity detected, not assumed.** Three independent
identification methods cross-checked; below 95% confidence the parse raises
with a diagnosis. *Accepted.*

**ADR-5 — Fill simulation accepts only next-session OHLC.** Makes
same-session entry structurally impossible rather than merely discouraged.
*Accepted.*

## 2.4. Hard rules

- **A.** In hosted mode the app never downloads, computes, fits or writes.
- **B.** The publish folder is the only thing that leaves the machine. The
  journal and all capital figures stay local.
- **C.** Both modes render identical page code; the difference lives entirely
  in the data-access layer.
- **D.** Mode defaults to **hosted/read-only** when unset, so a misconfigured
  deployment can never attempt to open a local warehouse.

---

# 3. REPOSITORY LAYOUT

```
vnquant/
├─ app.py                        hosted entry point
├─ requirements.txt              hosted dependencies, minimal
├─ requirements-local.txt        local superset
├─ .gitattributes                binary markers — commit before first push
│
├─ config/
│  ├─ universe_pit.csv           point-in-time index membership
│  ├─ sector_taxonomy.yaml       effective-dated
│  ├─ security_profiles.yaml     effective-dated master data
│  └─ model_profiles.yaml        regime weight policy
│
├─ vnquant/
│  ├─ constants.py               ⭐ the ONLY place numeric parameters live
│  ├─ market_rules.py            bands, ticks, lots, calendar, costs
│  ├─ mode.py                    resolves mode; defaults to hosted
│  │
│  ├─ domain/                    models.py · enums.py
│  │
│  ├─ data/
│  │  ├─ schema.py               ⭐ column identity detection
│  │  ├─ providers.py            provider interface + adapters
│  │  ├─ corporate_actions.py    derived from adjusted/raw ratio
│  │  ├─ quality.py              DQ score + ingestion gate
│  │  ├─ synthetic.py            demo generator, realistic character
│  │  └─ storage.py
│  │
│  ├─ features/
│  │  ├─ technical.py            pure NumPy/SciPy, no TA-Lib
│  │  ├─ relative_strength.py    three benchmarks
│  │  ├─ structure.py            confirmed pivots, BOS, sweeps, FVG
│  │  ├─ wyckoff.py              range, spring, upthrust, SOS
│  │  ├─ volume_profile.py       EOD proxy, labelled
│  │  ├─ order_flow.py           imbalance, order-to-trade, size stability
│  │  └─ normalization.py        z-scores, ATR-normalised, percentiles
│  │
│  ├─ market/
│  │  ├─ regime.py               dual index + turnover confirmation
│  │  ├─ breadth.py
│  │  ├─ concentration.py
│  │  └─ sector_rotation.py
│  │
│  ├─ profiles/
│  │  ├─ metrics.py              14 measured statistics
│  │  ├─ classifier.py           explicit decision tree
│  │  ├─ registry.py
│  │  └─ weight_policy.py        regime-level fitting + shrinkage
│  │
│  ├─ fundamentals/
│  │  ├─ repository.py           point-in-time
│  │  ├─ registry.py
│  │  └─ strategies/             banking · real_estate · cyclicals · generic
│  │
│  ├─ recommendations/
│  │  ├─ scoring.py              volume sign-flip by logic
│  │  ├─ setups.py
│  │  ├─ pricing.py              dual stops
│  │  ├─ sizing.py
│  │  ├─ gates.py                seven gates
│  │  ├─ exits.py                seven rules, urgency separated
│  │  └─ explain.py
│  │
│  ├─ forecast/
│  │  ├─ volatility.py           GARCH(1,1) MLE + EWMA
│  │  ├─ direction.py            purged CV, calibration, AUC gate
│  │  ├─ distribution.py         filtered bootstrap + analogues
│  │  ├─ regime.py               Markov trend states
│  │  └─ engine.py
│  │
│  ├─ backtest/
│  │  ├─ execution.py            ⭐ T+1 fill, costs, quality metrics
│  │  ├─ engine.py               event-driven, T+2 regulatory sellability + policy delay
│  │  ├─ walk_forward.py         purge + embargo
│  │  ├─ metrics.py              Deflated Sharpe, bootstrap CIs, power
│  │  └─ calibrate.py            hit rates, refusing thin samples
│  │
│  └─ ui.py                      cached read-only loaders
│
├─ jobs/
│  ├─ doctor.py                  ⭐ run FIRST on real data
│  ├─ pipeline.py                --demo | --bootstrap | daily
│  ├─ backtest.py                --n-trials N
│  └─ validate.py                the three validations
│
├─ pages/                        Market · Sector · Screener · Ticker ·
│                                Rejections · Backtest · Diagnostics
├─ scripts/                      scheduled-task entry points, registration
└─ tests/
```

## 3.1. Import discipline, enforced by test

```
UI pages may import ONLY: constants · market_rules · mode · ui
Never: data.providers · backtest · jobs
```

---

# 4. DEPENDENCIES

## 4.1. Hosted viewer

```text
streamlit · pandas · numpy · plotly · PyYAML
```

The hosted viewer never authenticates to any market-data provider, backtests, or owns the warehouse.

## 4.2. Local compute plane

```text
duckdb · pyarrow · pytest
+ hosted-viewer dependencies
+ provider-specific client/SDK only after that provider passes Source Admission `[GUESS]`
```

The **v3.3 target dependency set excludes `ssi-sdk`**. `duckdb + parquet` remain the local research warehouse baseline because point-in-time joins, lineage, ad-hoc validation and reproducible SQL are more valuable than minimizing one small dependency at VN100 scale. A provider-specific dependency is added only after access rights, contract/schema semantics and validation evidence are accepted. `[GUESS]`

No `vnstock`, no TA-Lib, no auto-trading dependency.

# 5. ENVIRONMENT

## 5.1. Text encoding is mandatory, not optional

Vietnamese company names carry diacritics, and the default file encoding on
the target OS is the locale code page rather than UTF-8. The result is silent
corruption or a decode error deep in the pipeline.

```python
# 1 — every file operation names its encoding
open(path, encoding="utf-8")
json.dump(obj, fh, ensure_ascii=False)

# 2 — every entry script sets UTF-8 mode before invoking Python
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
chcp 65001

# 3 — a startup assertion that fails loudly rather than corrupting data
if sys.flags.utf8_mode != 1:
    raise RuntimeError("UTF-8 mode is off; Vietnamese text will corrupt")
```

## 5.2. Filesystem and process

- Install at a short root path, **not** under a cloud-synced folder. Sync can
  corrupt a database file mid-write; deep paths risk path-length limits.
- Use the standard Python installer, not a sandboxed store build.
- Exclude the data directory and the Python executable from real-time
  antivirus scanning; otherwise columnar writes take roughly three times as
  long.
- A single-writer datastore must be opened **read-only** by the UI, and the
  scheduled job must retry on a lock rather than dying silently.

## 5.3. Version control

Commit a `.gitattributes` marking columnar, database and archive files as
binary **before** the first data push, or line-ending normalisation will
corrupt them.

For automated pushes from a non-interactive scheduled task, use a
fine-grained token scoped to one repository, cached once in the OS credential
store. Never in the repository, never in a script.

## 5.4. Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-local.txt
```

---

# 6. DATA LAYER

## 6.1. Provider hierarchy — v3.5 contract `[GUESS where tier/role is project design]`

| Trust tier | Source | v3.5 role | Current implementation |
|---|---|---|---|
| **T0 official truth** | HOSE / HNX / VSDC / SSC / issuer disclosures | Rules, index review evidence, corporate actions, listing/trading status, issuer filings | Reference/manual ingestion as applicable |
| **T1 documented machine feed** | **DNSE OpenAPI** | Leading automated market-data candidate after live Source Admission `[GUESS]` | **Read-only adapter IMPLEMENTED + TESTED_OFFLINE; NOT ADMITTED / NOT LIVE-VALIDATED** |
| **T1L licensed professional feed** | **Vietstock DataFeed** | Licensed secondary/alternative market/fundamental feed candidate after contract + schema + rights admission `[GUESS]` | **Generic contract-gated adapter IMPLEMENTED + TESTED_OFFLINE; NOT ADMITTED** |
| **T2 export/reference** | **CafeF historical pages / authorized exports** | Opt-in spot validation and research evidence; not primary production feed | **HTML reference adapter IMPLEMENTED + TESTED_OFFLINE; rights/live automation still unverified** |
| **TQ quarantine** | Undocumented/reverse-engineered endpoints | Research only | Must never write canonical data until admitted |

**SSI FastConnect is explicitly OUT OF SCOPE / DISABLED.** The product owner cannot obtain access, so v3.5 must not use it as primary, secondary, fallback, bootstrap dependency or validation prerequisite. The legacy adapter may remain in old source history for provenance but must not be reachable in the v3.5 runtime path.

DNSE official material documents a market-data API and official Python SDK; it is the leading automated candidate `[GUESS]` but still needs live Source Admission. Vietstock publicly describes DataFeed as financial data delivered through **API or Sync Data** for professional integration. CafeF publicly exposes historical data and Excel export with a reference-use disclaimer; research did not verify an equivalent official public API contract for CafeF. **[GUESS] Project policy:** a technically callable undocumented endpoint is not treated as an admitted API.

### Security boundary

```text
Allowed: data-provider credentials only for an ADMITTED provider, stored outside the repository
Forbidden: broker trading OTP/token/order endpoints/private trading-signature keys
Forbidden: SSI-specific runtime credentials/configuration in the v3.3 target build
```

No trading client is instantiated anywhere in this application.

### Provider interface

```python
class MarketDataProvider(ABC):
    provider_id: str
    trust_tier: str
    capabilities: set[str]

    def current_index_members(self, index_code: str = "VN100") -> list[str]: ...
    def daily_history(self, symbol: str, start: date, end: date) -> DataFrame: ...

# [GUESS] v3.3 source-governance objects
class SourceRegistry(Protocol):
    def admission(self, provider_id: str) -> "SourceAdmission": ...

class CrossProviderReconciler(Protocol):
    def reconcile(self, observations: list["ProviderObservation"]) -> "CanonicalDecision": ...
```

Canonical bar schema:

```text
symbol · trading_date · open · high · low · close · volume · value · provider
```

Current VN100 membership is valid for **current scanning**. For historical backtests, the engine must select one of two explicit modes:

```text
STRICT_PIT            verified effective-dated official membership snapshots
CURRENT_UNIVERSE_PROXY current VN100 applied historically; output MUST say NOT_TRUE_HISTORICAL_VN100
```


## 6.1A. Source admission and rights gate `[GUESS]`

A provider can exist in code without being admitted to production. `config/providers.yaml` must version at least:

```yaml
providers:
  vietstock_datafeed:
    trust_tier: T1L
    state: VALIDATION
    access_basis: contract_required
    capabilities: [TBD_AFTER_SCHEMA_REVIEW]

  cafef_export:
    trust_tier: T2
    state: RESEARCH_ONLY
    access_basis: user_visible_or_authorized_export
    capabilities: [manual_price_crosscheck, manual_flow_crosscheck]

  # No active SSI provider entry in v3.3.
```

The exact Vietstock schema/capabilities are `TBD` until commercial documentation or an authorized sample is reviewed. Do not infer field coverage from marketing copy.

Production admission requires evidence for access rights, schema semantics, timezone/trading-date rules, units, raw/adjusted treatment, revision behaviour, lineage capture and an independent validation plan. Failure of any gate is a **hard stop for canonical writes**, not an invitation to scrape another site silently.

The maintained registry implements immutable `AdmissionEvidence` and
`ValidationResult` records covering access basis, licence reference, every
declared capability, schema/units, timezone/date semantics, raw-versus-adjusted
policy, revision behavior, quotas, lineage, validation results, owner, and
ordered review dates. Legal transitions are `CANDIDATE -> DOCTOR_PASSED ->
CROSS_VALIDATED -> ADMITTED`, active-state transitions to
`SUSPENDED`/`RETIRED`, `SUSPENDED -> CANDIDATE|RETIRED`, and `RESEARCH_ONLY ->
RETIRED`; all others fail closed. Contract completeness and real-data/provider
role eligibility are checked before promotion.

## 6.1B. Provider fallback is explicit, never silent `[GUESS]`

```text
primary unavailable
  -> mark provider health failure
  -> evaluate an already-ADMITTED alternate provider
  -> if no admitted alternate: NO_ACTIONABLE_RECOMMENDATION
  -> never switch to CafeF/undocumented endpoint/synthetic data invisibly
```

A fallback must persist `source_policy_version`, `primary_provider`, `actual_provider`, `fallback_reason`, and `reconciliation_status` with the signal.


## 6.2. Column identity detection ⭐

Trusting column **position** is the riskiest assumption available for a free
feed whose header labels have changed over time: if the layout shifts, volume
silently becomes close, every indicator is computed on nonsense, and
**nothing raises an error**.

Three independent identification methods, cross-checked:

```
1  HEADER NAMES     matched against known aliases, accent- and
                    case-insensitively

2  VALUE SHAPE      dates match (19|20)\d{6} or parse as dates
                    tickers match [A-Za-z]{3}[A-Za-z0-9]?
                    prices fall in a plausible VND range and vary smoothly
                    volumes are non-negative integers, often exceeding
                      any plausible price

3  INTERNAL LOGIC   high ≥ max(open, close) and low ≤ min(open, close)
                    must hold for nearly every row
```

High and low are identified by which column is most often the row maximum and
minimum. Open and close are separated by **continuity**: whichever remaining
column sits closer to the previous session's close is the open.

A mapping is accepted only at **≥95% combined confidence**. Below that the
parse raises with the columns found, sample rows, every attempted mapping
with its confidence, and the specific fix.

### Verified behaviour

| Case | Result |
|---|---|
| Canonical AmiBroker headers | identified by name, 100% confidence |
| **Columns fully shuffled, names meaningless** | **recovered by value shape, 100% confidence** |
| Unrecognisable numeric noise | **raises with a diagnosis**, does not guess |

## 6.3. Three data traps

**Trap 1 — dated daily files are pruned** after a few days; only full-history
archives persist. A missed run recovers from the full archive.

**Trap 2 — provider history may be revised.** Never assume even “raw” vendor history can never change. Persist **immutable ingestion snapshots** with provider, fetch time and hash; canonical history may then be re-derived from the newest accepted revision.

```text
provider payload snapshot  → immutable evidence
canonical raw bars          → versioned accepted view
adjusted bars               → derived from official actions + validation checks
```

**Trap 3 — no free-feed assumption creates an SLA.** A missing/partial response blocks that day's recommendation until the DQ gate clears.

## 6.4. Corporate actions — official type, ratio only as validation

The v3.0 rule that classified action type from `adj_close/raw_close` magnitude is **removed**. Adjustment factors are not uniquely invertible to a legal corporate-action type, especially for rights, bonus shares, mixed events and vendor-specific anchoring.

Production flow:

```text
VSDC / HOSE / issuer disclosure
        ↓
CorporateAction(symbol, ex_date, action_type, ratio, cash_amount, announced_at, source)
        ↓
Adjustment engine
        ↓
Compare against provider-adjusted series / factor jumps
        ↓
DQ anomaly if disagreement remains unresolved
```

The adjusted/raw ratio is retained only to detect a **potential missing adjustment event**:

```text
factor(t) = adj_close(t) / raw_close(t)
large jump in factor => anomaly candidate
ACTION TYPE => UNKNOWN until official disclosure is matched
```

Rebuild the affected symbol's adjusted history immediately when a verified action arrives. A quarterly full rebuild remains an audit, not the first correction point.

## 6.5. Ingestion quality gate

Runs before any signal is generated; aborts and notifies on any failure.

```
latest stored date == latest expected trading session
row count ≥ 90% of the previous session
no |return| > band × 1.05 without a corporate action that date
low ≤ min(open, close) and high ≥ max(open, close) on every row
volume ≥ 0 · no duplicate (symbol, date)
classification metadata refreshed within 100 days
```

## 6.6. Data quality score (BRD §17)

```
DQ = 100 − stale − missing_bar − suspicious_gap
         − provider_disagreement − unresolved_corporate_action

DQ < 70 → cap confidence         DQ < 50 → block actionable recommendation
```

## 6.7. Universe refresh

```
exchange review release → parse candidate file → diff old/new
→ MANUAL VERIFICATION GATE → write effective-dated snapshot
→ invalidate caches
```

Never let an unattended scraper change the production universe without
validation. Snapshot the official basket at **every** review — that asset
cannot be reconstructed afterwards.

## 6.8. Network etiquette applies only after source admission

```
[GUESS] Descriptive User-Agent where the provider permits it
[GUESS] Respect documented rate limits; if none are documented, use a conservative client-side throttle for an admitted source
Exponential backoff on 429/5xx; do not bypass access controls
Cache/snapshot responses according to licence and lineage policy
```

---

# 6A. REAL-DATA INGESTION CONTRACT — SSI-FREE BASELINE

## 6A.1. Provider-agnostic admission state

There is currently **no admitted automated market-data provider**. Real-data automation must therefore fail closed with `NO_ADMITTED_PROVIDER` rather than invoke a legacy SSI path or silently substitute a scraped/synthetic feed. `[GUESS]`

The target runtime contract is:

```python
provider = registry.get_admitted_provider(capability="daily_ohlcv")
if provider is None:
    raise NoAdmittedProvider("Real-data ingestion is blocked until Source Admission passes")
```

The legacy `SSIFastConnectV3Provider` may remain in source history for provenance, but it is **RETIRED / DISABLED** in v3.3 and cannot write canonical data.

## 6A.2. Raw evidence and lineage

Every admitted-provider response or authorized/manual auxiliary import is snapshotted before normalization:

```text
provider · requested_at/imported_at · request/import parameters · payload/file hash · adapter/importer version
```

Revisions are additive. Canonical data points to the accepted revision rather than destroying earlier evidence.

## 6A.3. Generic source doctor `[GUESS]`

After a provider passes Source Admission, the target command is provider-agnostic:

```text
python -m vnquant.jobs.source_doctor --provider <admitted_provider>
```

This command is **SPECIFIED/TARGET, NOT YET IMPLEMENTED**. Checks include access/auth where applicable, sample coverage, OHLC invariants, duplicates/non-positive prices, units/timezone/date semantics, revision metadata and a Data Quality verdict. Passing the doctor proves connectivity/schema plausibility, **not** full historical correctness.

For manual/authorized CSV/Excel auxiliary imports, the importer must validate the same canonical invariants and persist the file hash and provenance. This path is fallback/debug/recovery/bootstrap only, not the normal startup workflow. `[GUESS]`

## 6A.4. Current-proxy versus strict historical backtest

A current VN100 snapshot may be imported for current scanning. Any retrospective backtest from that set is labelled `CURRENT_UNIVERSE_PROXY`. A result may be called “historical VN100” only in `STRICT_PIT` mode with effective-dated official membership snapshots.

## 6A.5. Provider/adaptor status

| Adapter/source | Status 2026-09-10 | Canonical writes allowed? |
|---|---|---|
| Official HOSE/HNX/VSDC/SSC/issuer evidence | **T0 authority; ingestion may be manual/structured by field** | Yes for fields whose provenance/effective date is captured |
| `VietstockDataFeedProvider` | **SPECIFIED / VALIDATION CANDIDATE** | No until authorized access, schema, rights and reconciliation evidence pass Source Admission |
| `CafeFManualValidationProvider` `[GUESS]` | **SPECIFIED ONLY** | Only controlled/manual validation/import where data-use basis is acceptable; not an automated production feed by default |
| Undocumented CafeF/Vietstock HTTP endpoints | **NOT ADMITTED** | No |
| Legacy `SSIFastConnectV3Provider` | **RETIRED / DISABLED by product-owner decision** | **No** |

## 6A.6. Reconciliation data model `[GUESS]`

```text
ProviderObservation(
  provider_id, provider_revision, symbol, trading_date, field,
  raw_value, normalized_value, unit, semantics_id,
  retrieved_at, payload_hash, source_uri_or_document
)

CanonicalDecision(
  symbol, trading_date, field, accepted_value,
  accepted_provider, compared_providers,
  reconciliation_status, reason, policy_version
)
```

Reconciliation first checks semantics, then values. It must retain all compared observations so a later provider revision can be audited without reconstructing history from memory.


---

# 7. STORAGE SCHEMA

```sql
-- Market data ------------------------------------------------------
provider_snapshots(snapshot_id, provider, requested_at, request_json,
                   payload_sha256, adapter_version, storage_path);

source_admission(provider_id, trust_tier, state, access_basis,
                 licence_ref, capabilities_json, schema_units,
                 timezone_date_semantics, raw_adjusted_policy,
                 revision_behavior, quotas, lineage_method,
                 validation_results_json, owner,
                 reviewed_at, next_review_at, policy_version);

provider_observations(provider_id, provider_revision, symbol, ts, field,
                      raw_value, normalized_value, unit, semantics_id,
                      retrieved_at, payload_sha256, source_ref);

canonical_decisions(symbol, ts, field, accepted_value, accepted_provider,
                    compared_providers_json, reconciliation_status,
                    reason, source_policy_version);

bars(symbol, ts, interval, open, high, low, close, volume, value,
     provider, provider_revision, ingested_at, quality_flags,
     trading_status, bar_present);

order_flow(symbol, ts, bid_volume, ask_volume, bid_orders, ask_orders,
           matched_volume, foreign_buy, foreign_sell);

index_series(index_code, ts, open, high, low, close, volume);
    -- includes the SELF-COMPUTED equal-weight index

-- Point-in-time metadata -------------------------------------------
universe(index_code, symbol, effective_from, effective_to,
         weight, source_document);

sector_membership(symbol, sector_code, industry_code,
                  effective_from, effective_to, taxonomy_version);

security_profiles(symbol, effective_from, effective_to,
                  sector, industry, archetypes_json,
                  beta_bucket, liquidity_bucket,
                  fundamental_model, technical_profile, source, version);

corporate_actions(symbol, ex_date, announced_at, action_type,
                  ratio, cash_amount, source, source_document, verified_at);

adjustment_anomalies(symbol, ts, factor_ratio, provider,
                     matched_action_id, resolution_status, note);

fundamentals(symbol, period_end, published_at, statement_type,
             metric, value, restated_flag);
    -- published_at, NOT period_end, governs availability

-- Computed ----------------------------------------------------------
features(symbol, ts, feature_name, raw_value, normalized_value,
         feature_version);

profiles(symbol, as_of, variance_ratio_5, hurst, vol_annual, atr_pct,
         downside_atr_pct, atr_asym, beta, idio_share, adv_20_bn,
         amihud, gap_median, gap_p90, limit_hit_freq, max_floor_streak,
         foreign_sensitivity);

market_regimes(as_of, regime, regime_score, breadth_score,
               concentration_score, liquidity_score, turnover_ratio,
               divergence, model_version);

sector_scores(as_of, sector_code, rs_20, rs_60, breadth, volume_impulse,
              valuation_z, earnings_revision_proxy, foreign_flow_proxy,
              leadership_score, model_version);

model_profiles(profile_id, regime, sector_code, archetype,
               weights_json, thresholds_json, valid_from, valid_to, version);

-- Output ------------------------------------------------------------
signals(id, symbol, as_of, model_version, feature_version, regime,
        sector_score, archetype_score, technical_score, fundamental_score,
        liquidity_score, data_quality, manipulation_risk_proxy,
        evidence_score, actionable_score, confidence, recommendation,
        setup_type, entry_low, entry_high, exit_stop, sizing_stop,
        target_1, target_2, qty, weight_pct, max_gap_pct,
        regulatory_sellable_date, policy_earliest_exit_fill_date,
        pre_settlement_stress_pct, universe_mode);
    -- qty and any currency amount are LOCAL ONLY, never published

rejections(as_of, symbol, gate, reason);
backtest_trades(...); backtest_equity(...); hit_rates(...);
scanner_kpi(as_of, gate_counts_json, score_distribution_json,
            rolling_ic_json, drift_flags);
journal(...);   -- LOCAL ONLY, always
```

**The most important field in the schema is `published_at`.** A quarter
ending 31 March cannot be used in a backtest dated 1 April if it had not been
published then.

---

# 8. FEATURE ENGINE

## 8.1. Output contract: raw and normalised

The engine emits **both** raw indicator values and normalised ones. Rules
consume normalised values so a single threshold is never applied across a
heterogeneous universe.

```
raw_rsi · rsi_percentile_252 · atr_pct · volume_z_60 · turnover_z_60
· return_20 · rs_stock_market_20 · rs_stock_sector_20 · sector_rs_market_20
· displacement_atr · breakout_distance_atr · liquidity_percentile
```

## 8.2. Recursive indicators without a loop

Wilder-smoothed indicators are first-order IIR filters:

```
y_t = α·x_t + (1−α)·y_{t−1}   ⟺   lfilter([α], [1, −(1−α)], x)

EMA(n):      α = 2/(n+1)
Wilder RMA:  α = 1/n          ← what RSI, ATR and ADX actually use
```

Both SMA-seeded. Rolling windows use strided views. No JIT dependency.

## 8.3. Formulas

Full definitions are in BRD §4 and §10. Implementation notes:

| Feature | Note |
|---|---|
| `downside_atr` | ATR over sessions closing lower only, forward-filled onto the full timeline. Mandatory — BRD §11.3 |
| `variance_ratio_5` | Non-overlapping 5-session blocks. Verified: AR(+0.35)→1.81, AR(−0.35)→0.56, iid→1.02 |
| `rs_*` | Three benchmarks: market, sector, sector-vs-market |
| `displacement_atr` | `|ΔC| / ATR₁₄`, never a fixed percentage |
| `volume_z_60` | Z-score, never a fixed multiplier |
| Confirmed pivots | `R` bars of delay before a swing is marked. **Non-negotiable** — marking a pivot on its own bar is look-ahead bias |
| EOD volume profile | Typical-price bins, labelled a proxy, multiplied by liquidity confidence |

## 8.4. Missing data policy — preserve missingness

```text
build the expected trading calendar from verified market/index sessions
for each security classify the session as:
    TRADED | NO_TRADE | SUSPENDED | NOT_LISTED | PROVIDER_MISSING | UNKNOWN

PROVIDER_MISSING:
    do NOT forward-fill OHLC
    do NOT set volume=0 as if a real flat session occurred
    exclude the security from same-day cross-sectional ranks
    penalize/block via Data Quality

SUSPENDED / genuine no-trade:
    preserve explicit status; only derive values according to a documented feature-specific policy

never synthesize historical bars merely to keep rolling windows rectangular
```

## 8.5. Cross-sectional normalisation

Ranks are computed over a **wider universe** than the trading universe. The
standard error of a cross-sectional rank correlation scales as `1/√(N−3)`:

```
N = 100 → SE ≈ 0.101      a five-rank difference is inside the noise
N = 350 → SE ≈ 0.054      nearly halved, at no cost
```

Use a rank-based inverse normal transform after winsorisation, not raw
z-scores: return distributions here are fat-tailed enough that z-scores are
dominated by outliers.

---

# 9. CLASSIFICATION ENGINE

## 9.1. Measured metrics, not asserted labels

Sixteen statistics per security, recomputed quarterly (BRD §8.2). The statistics themselves are `[M]`; **classification thresholds and decision-tree structure are `[D]` and can overfit** if chosen after observing performance. Every threshold must therefore live in the parameter registry and be validated out of sample.

## 9.2. Explicit decision tree, not clustering algorithms

A transparent tree rather than k-means: inspectable (you can read why a
security landed where it did), stable across runs (k-means relabels
arbitrarily), and every threshold is a testable claim.

```python
def assign(profile) -> tuple[str, str]:      # returns (archetype, reason)
    # EXCLUSION GATES first
    if adv_20_bn < 20:              return EXCLUDED, "cannot size a position"
    if max_floor_streak >= 5:       return EXCLUDED, "tail risk when locked"
    if gap_p90 > 0.045:             return EXCLUDED, "unusable for EOD entry"

    # SECTOR OVERRIDES where statistics miss the mechanism
    if symbol in BANKS:             return BANK, "banking sector"
    if symbol in COMMODITY:         return CYCLICAL, "commodity-driven"

    # STATISTICAL CLASSIFICATION
    if vol < 0.28 and beta < 0.85 and limit_freq < 0.02:
                                    return DEFENSIVE, ...
    if beta > 1.25 and vol > 0.38:  return HIGH_BETA, ...
    if vol > 0.45 or limit_freq > 0.05 or streak >= 3:
                                    return SPECULATIVE, ...
    if symbol in MEGA_CAP or (adv > 200 and vol < 0.35):
                                    return LARGE_CAP, ...

    # STATISTICAL FALLBACK — constrained (BRD §8.4)
    #   may reach ONLY statistically defined archetypes
    #   may NOT grant privileges the security has not demonstrated
    if vr > 1.15 and adv >= 100 and vol < 0.38:  return LARGE_CAP, ...
    if vr < 0.85 and vol < 0.33:                 return DEFENSIVE, ...
    return SPECULATIVE, "no clear signature; assigned conservatively"
```

**Every assignment must carry a human-readable reason.** A test asserts the
reason string is non-trivial.

## 9.3. Multi-tag support

A security may hold several archetype tags. The classifier returns a primary
archetype for routing plus a tag set for gating.

## 9.4. Stability requirement

```
stability = fraction of quarter-on-quarter assignments unchanged
< 0.60 → the classification is tracking noise; simplify
```

Recorded in `scanner_kpi` every run.

---

# 10. REGIME AND SECTOR ENGINES

## 10.1. Regime engine — deterministic before machine learning

```python
def compute_regime(cap_index, ew_index, breadth, turnover) -> Regime:
    def score(ix):
        return (ix.close > ix.ma50) + (ix.close > ix.ma200) + (ix.ma50 > ix.ma200)

    s = min(score(cap_index), score(ew_index))     # divergence → conservative
    tr = turnover.ratio_to_ma20                    # missing → NEUTRAL

    # Missing turnover is neutral / non-confirming: it may NOT promote a regime.
    if s == 3 and breadth.pct_ma50 >= 0.60 and breadth.ad_slope > 0 \
             and tr is not None and tr >= 1.00:      return STRONG_BULL
    if s >= 2 and breadth.pct_ma50 >= 0.45 \
             and tr is not None and tr >= 0.85:      return CONCENTRATED_BULL
    if s >= 1 and breadth.pct_ma50 >= 0.35:         return RANGE
    if s >= 1 or  breadth.pct_ma50 >= 0.25:         return RISK_OFF
    return PANIC_BEAR
```

Inputs also include realised-volatility regime, top-N contribution
concentration and sector participation.

> **A single condition such as "index above its MA200" must never determine
> regime alone.**

Turnover confirmation rationale is in BRD §6.3. Missing turnover data is neutral/non-confirming; the regression test must fail if `None` can produce `STRONG_BULL`.

## 10.2. Sector engine

```python
@dataclass(frozen=True)
class SectorContext:
    sector: str
    leadership_score: float
    rank: int
    rs_20: float
    rs_60: float
    breadth_score: float
    volume_impulse: float
    regime_alignment: float
```

Leadership score per BRD §7.1. Sector benchmarks must be **point-in-time** —
computed from the constituents that were in the sector on that date.

---

# 11. STRATEGY REGISTRY AND WEIGHT POLICY

## 11.1. Interfaces — no symbol-specific branching

```python
@dataclass(frozen=True)
class SecurityProfile:
    symbol: str
    sector: str
    industry: str
    archetypes: tuple[str, ...]
    beta_bucket: str
    liquidity_bucket: str
    fundamental_model: str
    technical_profile: str

class ValuationStrategy(ABC):
    @abstractmethod
    def score(self, fundamentals, market_context) -> float: ...

class SignalProfile(ABC):
    @abstractmethod
    def transform(self, features, profile) -> Mapping[str, float]: ...

class WeightPolicy(ABC):
    @abstractmethod
    def resolve(self, regime: str, profile: SecurityProfile
                ) -> Mapping[str, float]: ...
```

Concrete valuation strategies: `BankPBROEStrategy`,
`SecuritiesNormalizedPBPEStrategy`, `RealEstateRNAVStrategy`,
`CyclicalNormalizedEVEBITDAStrategy`, `TechnologyGrowthFCFStrategy`,
`RetailForwardPEGStrategy`, `UtilitiesDCFStrategy`, `OilGasMidCycleStrategy`,
plus an explicitly flagged `GenericFallbackStrategy`.

## 11.2. Configuration, not code

```yaml
# config/model_profiles.yaml   — all values [D]
regimes:
  strong_bull:
    weights: {trend: 0.30, momentum: 0.25, structure: 0.20,
              volume_flow: 0.15, valuation_quality: 0.05, sector_rs: 0.05}
  range:
    weights: {trend: 0.10, momentum: 0.10, structure: 0.30,
              volume_flow: 0.20, valuation_quality: 0.20, sector_rs: 0.10}

archetype_overrides:          # GATING and MULTIPLIERS only, not fitted weights
  high_beta_cyclical: {momentum_multiplier: 1.15,
                       atr_normalized_thresholds: true,
                       min_regime: strong_bull}
  defensive:          {momentum_multiplier: 0.75,
                       valuation_multiplier: 1.20,
                       min_regime: risk_off}

sector_overrides:             # ROUTING only
  banking:     {valuation_strategy: pb_roe_residual_income}
  real_estate: {valuation_strategy: rnav_sotp}
```

## 11.3. The fitting constraint, in code ⭐

```python
def resolve(self, regime, profile) -> Mapping[str, float]:
    """Weights are FITTED at regime level only.

    Sector and archetype contribute ROUTING and MULTIPLIERS, which cost no
    data, but never independently fitted weight vectors. A
    regime x sector x archetype grid yields roughly 9 signals per cell
    against a 30-signal minimum -- see BRD 5.2.
    """
    w = self.regime_weights[regime]                     # FITTED, 5 cells
    w = apply_archetype_multipliers(w, profile)         # gating, not fitting
    return w

def resolve_with_shrinkage(self, regime, profile, lam: float = 0.25):
    """If cell-level weights are attempted anyway, shrink hard toward global."""
    w_global = self.regime_weights[regime]
    w_cell = self.cell_weights.get((regime, profile.sector), w_global)
    return {k: (1 - lam) * w_global[k] + lam * w_cell[k] for k in w_global}
```

**A test must fail if a fitted weight vector is registered for a cell holding
fewer than 30 historical signals.**

---

# 12. SIGNAL ENGINE

## 12.1. Pipeline

Implements BRD §9 exactly. Every rejection records `(symbol, gate, reason)`.

```python
def recommend(symbol, as_of, ctx):
    profile = ctx.profiles.get(symbol, as_of)        # point-in-time
    market  = ctx.regime_engine.evaluate(as_of)
    if market.regime is PANIC_BEAR:
        return abort_run("regime is PANIC_BEAR")     # GATE 0

    sector  = ctx.sector_engine.evaluate(profile.sector, as_of)
    raw     = ctx.features.compute(ctx.data.history(symbol))
    feats   = ctx.signal_profiles.resolve(profile).transform(raw, profile)

    valuation = ctx.valuation_registry.resolve(profile.fundamental_model)
    fundamental = valuation.score(
        ctx.fundamentals.point_in_time(symbol, as_of), market)

    policy   = ctx.weight_policy.resolve(market.regime, profile)
    evidence = combine(sector, profile, feats, fundamental, policy)

    gates = ctx.gates.evaluate(market=market,
                               liquidity=feats["liquidity_score"],
                               data_quality=feats["data_quality"],
                               event_risk=ctx.events.for_symbol(symbol, as_of))

    actionable = evidence * gates.multiplier
    setup      = ctx.setups.detect(feats, market, sector, profile)
    execution  = ctx.execution_planner.plan(setup, bars, profile)
    return build_recommendation(...)
```

## 12.2. Volume gate — setup-aware ⭐

```python
VOLUME_CONFIRM_SETUPS = frozenset({
    "TREND_MA", "RS_LEADER", "MOM_20", "VCP", "REV_SUP",
})
# Pullback setups are ABSENT deliberately: their own detection rule requires
# volume CONTRACTION, so applying a floor contradicts the setup itself and
# silently rejects every pullback signal.

if primary_setup in VOLUME_CONFIRM_SETUPS:
    if volume_ratio < params.min_volume_ratio:
        reject("G4b", f"{primary_setup} needs volume expansion")
```

The same sign-flip must appear in the scoring formula (BRD §10.9). Stating it
correctly in one place and not the other is worse than getting it wrong in
both.

## 12.3. Pricing and dual stops

```python
entry = round_down_to_tick(close_t * (1 + SETUP_PREMIUM[setup]), exchange)

atr_eff     = max(atr_14, 1.3 * downside_atr_14)
exit_stop   = round_tick(min(structure_low - 0.5*atr_14,
                             entry * (1 - max_stop_pct)))
sizing_stop = round_tick(min(entry - atr_mult * atr_eff,
                             entry * (1 - max_stop_pct * 1.25)))

assert 0 < sizing_stop < exit_stop < entry        # tested invariant
```

Tick rounding is always **downward**, so an order never bids above the
intended price.

## 12.4. Exit engine — urgency separated from limit

```python
TAKE_PROFIT_LIMIT = {"target_1": "t1", "target_2": "t2"}
# Only these rest at a limit. Every other reason -- stop, anomaly, regime,
# time stop, thesis broken -- fills at the open. Conflating "must fill now"
# with "may wait at a limit" made a time stop wait at its target forever.

limit = TAKE_PROFIT_LIMIT.get(reason)   # None for everything else
```

---

# 13. EXECUTION SIMULATION AND BACKTEST

## 13.1. Entry simulation — structurally safe ⭐

```python
def simulate_entry(close_t, next_open, next_high, next_low, *,
                   premium, max_gap, exchange, mode) -> FillResult:
    """Accepts ONLY next-session OHLC. There is no parameter through which a
    same-session close could be passed as an entry price."""
```

A test inspects the signature itself:

```python
params = set(inspect.signature(simulate_entry).parameters)
assert {"next_open", "next_high", "next_low"} <= params
assert "entry_price" not in params    # must DERIVE the fill, never accept one
```

Fill logic — v3.1 conservative baseline:

```text
gap = next_open / close_t − 1
if gap > max_gap:                         NO FILL
limit = decimal_safe_round_down(close_t × (1 + premium))
if next_open <= limit:                    FILL at next_open
elif next_low < limit:                    FILL at limit        # traded through
elif next_low == limit:                   UNCERTAIN; no fill in conservative/base
else:                                     NO FILL
```

A daily bar that merely *touches* a limit does not prove queue priority or available quantity. Optimistic mode may credit the touch; model promotion must survive conservative mode.

## 13.2. Three binding constraints

1. **Entry is next-session only** after an EOD signal.
2. **Regulatory sellability:** entry-trade date + 2 trading sessions, after allocation around 13:00; persist this separately from strategy policy.
3. **EOD policy / liquidity:** an urgent exit is not a guaranteed next-open fill. If the next session is modeled as floor-locked/no executable liquidity, carry the exit forward and record the failed attempt.

## 13.3. Execution quality — the metrics that decide feasibility

```
Signals evaluated · Filled (rate) · Rejected on gap · Rejected at ceiling
· Limit never reached · Mean overnight gap · Mean fill vs close_t

VERDICT
  fill rate < 70%            → UNSUITABLE for end-of-day execution
  mean overnight gap > 1.5%  → UNSUITABLE
  mean overnight gap > 0.8%  → CAUTION, tighten the limit premium
```

A beautiful equity curve with a 40% fill rate describes a strategy that does
not exist.

Every promoted strategy must be evaluated in three execution modes: `optimistic`, `base`, `conservative`. Production approval requires acceptable results in **conservative** mode; optimistic mode is diagnostic only.

## 13.4. Exchange realism checklist

```
price bands · auction and order rules · lot sizing
· T+2 cash and securities availability · suspensions · corporate actions
· partial fills · liquidity cap as % of ADV · fees · tax · slippage
· failed fills at ceiling/floor · point-in-time constituents · delistings
```

## 13.5. Metrics

```
CAGR · annualised volatility · max drawdown · Sharpe · Sortino · Calmar
· profit factor · hit rate · avg win/loss · expectancy · turnover · exposure
· tail loss · benchmark-relative return · information ratio
· signal precision by score decile

⭐ Deflated Sharpe Ratio       corrects for the number of variants tried
⭐ Probability of Backtest Overfitting
⭐ Bootstrap confidence intervals on hit rate and expectancy
⭐ Statistical power: trades needed to separate an edge from zero
```

Performance must be reported **not only for the whole universe** but sliced
by: regime · sector · archetype · liquidity bucket · market-cap bucket ·
score decile · setup type · holding horizon. A weight policy is promoted only
if it does not depend on a single sector or a single period.

## 13.6. Deflated Sharpe — declare trials honestly

```
SR* = sqrt(Var[SR]) · [(1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))]
γ = 0.5772 (Euler–Mascheroni), N = number of variants tried
```

Measured on the implementation, with a **smaller** parameter space than the
hierarchical design:

| Declared trials | Deflated Sharpe |
|---|---|
| 1 (dishonest) | 27.0% |
| 24 (honest) | **0.4%** |

The `--n-trials` argument is not cosmetic. A test asserts monotonicity:
`dsr(1) > dsr(24) > dsr(500)`.

## 13.7. Validation scheme

```
Walk-forward with purge and embargo:

2014–2019 → train | 2020 → validate | 2021 → test
2014–2020 → train | 2021 → validate | 2022 → test    ... roll

Labels overlapping h sessions require an embargo of h + buffer around each
fold boundary. Never optimise on 2025 and then report "2025 backtest".
```

Random splits are prohibited for time-ordered data.

---

# 14. CALIBRATION LOOP

`SignalEngine` accepts a hit-rate mapping supplying `win_probability` at Gate
5. Without it the gate is inert and every ticket ships with an unknown
probability.

```
backtest → realised trades → calibrate_hit_rates() → hit_rates.json
        → loaded by the daily pipeline
```

## 14.1. It refuses thin samples

```
MIN_SAMPLE = 30 trades per (setup, archetype) bucket        [D]

Observed on the implementation: 7 buckets, none qualifying
    PB_MA20  LARGE_CAP  n=4   (raw 75%)
    PB_MA50  LARGE_CAP  n=3   (raw 33%)
Nothing published. The probability gate stays inert — correctly.
```

Partial exits are collapsed onto their entry so one position cannot inflate
the sample count.

`MIN_SAMPLE=30` is a publication floor, not an independence assumption. Calibration confidence intervals use **date-block / clustered resampling** so ten bank signals on one market day do not masquerade as ten independent experiments. Promotion reports must include effective sample size, regime concentration and sector concentration.

---

# 15. FORECAST ENGINE

Four components, reported in order of trustworthiness (BRD §13). Anything
failing its gate reports **unavailable**, never a number with a footnote.

## 15.1. Volatility

```
σ²_t = ω + α·ε²_{t−1} + β·σ²_{t−1}
MLE by L-BFGS-B subject to ω>0, α≥0, β≥0, α+β<0.999

Multi-step: LR = ω/(1−α−β);  σ²_{t+h} = LR + (α+β)^{h−1}(σ²_{t+1} − LR)
Cumulative: σ(h) = sqrt(Σ σ²_{t+i})
Fallback:   EWMA λ = 0.94 when the fit does not converge
```

**Verified:** a simulated process with true `α+β = 0.970` recovers as 0.971.

## 15.2. Price distribution — two independent methods

```
METHOD 1  filtered historical simulation
    z = (r − r̄)/σ_conditional, resampled, rescaled to unit variance
    r* = drift + σ_forecast(h)·z*, cumulated

METHOD 2  conditional analogues
    nearest historical states in standardised feature space,
    sampling the forward paths that actually followed

AGREEMENT = overlap of the two 5–95% intervals; below 0.6 the UI flags it
```

Output is a quantile fan, never a point.

## 15.3. Trend state

```
UP: C > MA50 > MA200 | DOWN: C < MA50 < MA200 | SIDE: otherwise
Transition matrix by counting, Laplace α = 1 (no exact zeros)
h-step: row of P^h;  expected duration: 1/(1 − P[i,i])
Requires ≥200 observed transitions
```

## 15.4. Direction — with self-suppression ⭐

```
model        logistic regression, standardised features
features     ~35 from the feature engine
validation   purged forward-chaining CV, embargo = horizon + 21 sessions
             train always precedes test with a gap ≥ horizon (tested)
calibration  sigmoid, so 0.58 means roughly 58% historically
GATE         out-of-sample AUC ≥ 0.52, else NO NUMBER IS SHOWN
```

**Verified:** on synthetic random-walk data the model reports AUC ≈ 0.49 and
suppresses itself.

## 15.5. ML roadmap — order matters

```
deterministic baseline → logistic / linear rank → tree boosting
→ regime-conditioned ensemble → probability calibration
→ only then evaluate deep models
```

Target is **forward excess return versus benchmark**, so the model learns
selection rather than market beta:

```
Y_{t,h} = R_stock,t→t+h − R_benchmark,t→t+h        for h ∈ {5, 10, 20}
```

---

# 16. VALIDATION HARNESS

```
python -m jobs.validate
```

Three validations, in an order where each can invalidate what follows.

## A — Corporate actions

Construct a known stock dividend plus a cash dividend; verify the
adjusted/raw ratio method recovers both ex-dates and both magnitudes.
Proves the arithmetic, not the data — still verify three real securities.

## B — Phantom profit ⭐

Run the identical strategy twice, entering at `close_T` versus on T+1.

| | close_T (impossible) | T+1 (real) |
|---|---|---|
| Trades | 21 | **15** |
| Hit rate | 33.3% | 40.0% |

**29% of trades simply never happen.** The counterintuitive direction — the
wrong arm has a *lower* hit rate — occurs because it also takes the trades the
gap gate would have refused.

## C — Grouping placebo ⭐

Assign securities to archetypes **at random** and rerun.

```
Real grouping     Sharpe −0.24   expectancy −0.02R   15 trades
Random grouping   Sharpe −0.40 (sd 0.41)
Advantage of real grouping: +0.16 Sharpe   → BELOW the +0.20 threshold
```

**Run this before building anything further on the classification layer.**
The hierarchical architecture rests entirely on the claim this test
evaluates. With few trades the test has low power and must say so —
"unproven", not "disproven".

---

# 17. USER INTERFACE

## 17.1. Caching semantics

`st.cache_data` for serialisable returns; `st.cache_resource` for shared
resources such as a database connection; `st.session_state` for state across
reruns within a session.

## 17.2. Pages

| Page | Purpose |
|---|---|
| **Market Dashboard** | Dual index overlay, regime timeline, divergence alert, breadth, concentration |
| **Sector Rotation** | Leadership scores, three-benchmark RS, rotation quadrants |
| **VN100 Screener** | Dual-RS scatter with the entry zone shaded — a literal picture of the entry rule |
| **Ticker Workbench** | Candles, structure, features raw and normalised, valuation route, full profile |
| **Recommendations** | Order tickets with entry zone, invalidation, targets, gap-check instructions |
| **Rejections** | Gate funnel plus a filterable table. **The most useful debugging page** |
| **Backtest Lab** | Fill rate and Deflated Sharpe **above** the equity curve, because they qualify it |
| **Model Diagnostics** | Rolling IC per factor, calibration curves, drift flags, cluster stability |
| **Data Quality** | Provider health, DQ scores, unresolved corporate actions, staleness |
| **Event & Risk Monitor** | Earnings dates, corporate actions, locked-breach warnings |

## 17.3. Two deliberate design choices

**The empty state is direction, not apology.** When regime is Panic/Bear:

> **No tickets, and that is the correct output.** Regime halts signal
> generation entirely. Herding on this market is documented to intensify in
> falling markets, so buying dips into a downtrend is how accounts get
> damaged. The position to hold right now is cash.

**The fan chart is the hero of the forecast page.** It is the honest shape of
a price forecast — a widening cone, not a line to a target.

## 17.4. Privacy boundary

Published artifacts carry **percentages of NAV only**, never currency amounts
or share quantities. A test scans every published file for currency-scale
integers and capital-related keys.

## 17.5. Secrets

Credentials, private keys and tokens are never committed. Read only from
environment variables or the platform secret store.

---

# 18. SCHEDULING AND OPERATIONS

## 18.1. Tasks

| Task | Schedule (local time) | Purpose |
|---|---|---|
| EOD | Weekdays 15:15 | Main pipeline |
| Pre-market | Weekdays 08:45 | Gap-check reminder |
| Weekly | Saturdays | Reports, backtest refresh |
| Quarterly | Monthly check, quarterly action | **Full adjusted rebuild**, re-profile, re-classify |

Registered to run when available and to wake the machine, so a missed or
sleeping window does not silently skip.

## 18.2. Late-data retry

Data may publish after the scheduled time. The job retries internally with
increasing delays before giving up and notifying — rather than relying on
multiple trigger times.

## 18.3. Missed-run recovery

```python
def catch_up():
    missing = sessions_between(latest_stored, latest_expected)
    if len(missing) <= 2:  backfill from dated daily files
    else:                  rebuild from the full-history archive
```

## 18.4. Monitoring

One-line notification on success; a detailed alert with the log path on
failure; a weekly digest of runs completed versus expected, quality failures,
classification stability, rolling IC and hit rate.

`scanner_kpi` logs every session: gate survival counts, score distribution,
rolling IC per factor with confidence intervals, turnover, PC1 share of
cross-sectional variance, and drift flags.

---

# 19. TESTING

**Legacy delivered Phase-1 implementation evidence: 18/18 tests passed via `python -m pytest -q`.** The earlier consolidated SRD carried a broader 58-test specification inventory; v3.3 does not present that inventory as a passed-build claim. Tests not present in the current repository are **PLANNED/TARGET**, not evidence of implementation.

The legacy 18-test build covers strict/proxy universe handling, sector-proxy labelling, three-way relative strength, regime turnover invariants, recommendation suppression in Panic/Bear, candidate generation, execution audit/non-fill retention, market-rule/cost/corporate-action safeguards and related Phase-1 functions. These tests do not validate the v3.3 provider path.

## 19.1. Target coverage inventory (includes tests not yet present in the current 18-test build)

| Area | Notable assertions |
|---|---|
| Environment | UTF-8 round-trips Vietnamese text; paths are path objects |
| Ingestion | URL date formats; layout detection across three cases; end-to-end shuffled-column parse |
| Indicators | SMA matches manual; Wilder recursion exact at every step; variance ratio discriminates |
| Normalisation | Same raw move with different ATR yields different normalised displacement; volume spike normalised against the security's own history |
| Relative strength | Stock-vs-sector and sector-vs-market computed correctly |
| Routing | Banks route to bank valuation; steel routes to cyclical valuation |
| Regime | Divergence resolves conservatively; Panic/Bear yields exactly zero signals; regime change alters policy **without mutating historical results** |
| Point-in-time | Current sector and archetype metadata cannot leak into a historical backtest |
| Volatility | GARCH recovers known parameters; horizon scaling near √t |
| Direction | **Purged splits never leak**; label alignment |
| Pricing | Tick boundaries; **never rounds up**; dual-stop ordering invariant |
| Execution | **Signature cannot accept a same-session close**; gap gate; ceiling lock |
| Metrics | **Deflated Sharpe falls monotonically with trial count**; CI narrows with data |
| Classification | Fitted not placeholder; **fallback never reaches sector-defined archetypes** |
| Gates | Low data quality or liquidity can cap or block an actionable recommendation |
| Hypotheses | An Elliott count never overrides a hard risk gate |
| Versioning | Fixed-weight MVP and hierarchical engine carry separate versions |
| Pipeline | Idempotent; settlement/policy dates enforced |

## 19.2. High-priority regression targets

1. **`test_execution_cannot_accept_same_session_close`** — inspects the
   function signature. Makes phantom profit structurally impossible.
2. **`test_signals_are_actually_producible`** — asserts non-zero signal
   count across years. Zero signals is a bug, not selectivity.
3. **`test_classification_is_fitted_not_placeholder`** — fails if more than
   half the universe lands in one archetype. Catches *plausible silence*, the
   most dangerous failure class.
4. **`test_no_magic_numbers`** — no numeric literal outside `constants.py` in
   the signal, feature and UI layers.
5. **`test_publish_no_pii`** — scans published artifacts for currency
   amounts and capital keys.


## 19.3. Current build evidence — 18 tests

The latest implementation report records expansion from 9 to **18** tests. Current named areas include:

- strict PIT universe refuses silent current-universe fallback;
- effective-dated universe resolution;
- current ICB used historically is explicitly labelled a proxy;
- missing turnover can never confirm Strong/Concentrated Bull;
- Strong Bull requires turnover confirmation;
- three-way relative-strength columns;
- Panic/Bear emits no candidates;
- pullback strategy family can fire;
- gap-rejected signals remain in the execution audit.

Build evidence from the latest delivered source:

```text
python -m compileall -q vnquant app.py    PASS
python -m pytest -q                       18 passed
```

Parquet/DuckDB end-to-end execution did **not** run in the build sandbox because `pyarrow`/`duckdb` could not be installed there. That limitation remains explicit.


---

# 20. RUNBOOK

## 20.1. First run

```bash
pip install -r requirements-local.txt

# v3.3 target runtime — the generic commands below are SPECIFIED/TARGET only
# until the SSI-free source migration is implemented.
python -m pytest -q

# [GUESS] after an automated provider passes Source Admission:
# python -m vnquant.jobs.source_doctor --provider <admitted_provider>
# python -m vnquant.jobs.bootstrap --provider <admitted_provider> --start 2015-01-01 --data-dir data
# python -m vnquant.jobs.pipeline --data-dir data --publish-dir publish
# python -m vnquant.jobs.backtest --data-dir data --costs config/my_broker.yaml --mode conservative
# streamlit run app.py

# Do NOT run the legacy SSI doctor/bootstrap path for v3.3 real-data validation.
```

## 20.2. The doctor command

Six checks, deliberately verbose, run before anything touches real data:

```
1  NETWORK       can the source be reached
2  DOWNLOAD      does the archive for this session exist
                 (walks back over weekends and holidays automatically)
3  ARCHIVE       member list, sizes, first 400 raw bytes
4  LAYOUT        per-column value-shape scores, chosen mapping, evidence
5  PLAUSIBILITY  price range, volume range, OHLC logic hit rates, dates
6  COVERAGE      symbols, sessions, how many clear the history minimum
```

Three specific alarms:

| Symptom | Meaning |
|---|---|
| Median close outside a plausible VND range | A column is misread |
| OHLC logic violated in > 2% of rows | Columns are very likely swapped |
| Negative volume | Wrong column identified as volume |

Exit codes: `0` all passed, `1` checks failed, `2` could not proceed.

## 20.3. Measured timings

| Step | Duration |
|---|---|
| Demo pipeline | 3–7 s |
| Backtest, 1,600 sessions | ~10 s |
| Full validation harness | ~30 s |
| Test suite | ~40 s |

## 20.4. First-week validations to run yourself

| # | Validation | Passing looks like |
|:---:|---|---|
| 1 | Admitted-provider doctor on real data | A provider first passes Source Admission, then its doctor validates access/schema/coverage; no SSI path is accepted in v3.3 |
| 2 | Source-admission review for any second provider | Rights/access basis, schema semantics, lineage and sample reconciliation recorded before canonical use |
| 3 | Plot a stock-dividend security over 5 years | No false gaps at ex-dates |
| 4 | Corporate actions for three known securities | Ex-dates and magnitudes match official evidence |
| 5 | Validation B on real prices | The phantom-profit gap is quantified |
| 6 | Validation C on real prices | Real grouping beats random by the predeclared placebo threshold `[GUESS]` |
| 7 | Variance-ratio histogram across the universe | If the empirical result invalidates momentum assumptions, remove/limit that family rather than defend it |
| 8 | Overnight-gap distribution | Tradeability thresholds are calibrated from real execution-relevant data |
| 9 | Signals-per-cell count for the intended partition | If sample is insufficient, do not fit weights at that level |
| 10 | Multi-source spot reconciliation | A predeclared sample of bars/flows is compared field-by-field after semantic normalization; unresolved disagreements remain quarantined |

Items 6, 7 and 9 can each restructure the system. The source-admission and reconciliation checks can also block a provider entirely; they run before capital is committed.

---

# 21. MIGRATION PLAN

```
Phase 0  PRESERVE BASELINE
         Keep the fixed-weight engine as model_version = mvp_fixed_v1

Phase 1  DATA CORRECTNESS FIRST — not AI
         point-in-time universe · EOD OHLCV · corporate actions
         · sector map · benchmark indices · foreign flow · disclosure
           timestamps
         Add layout detection and the doctor command here.

Phase 2  ADD METADATA
         sector taxonomy · security profiles · liquidity and beta buckets
         All effective-dated.

Phase 3  MARKET AND SECTOR CONTEXT
         regime · breadth · concentration · sector RS
         This is what decides whether the system understands the market or
         is merely an indicator dashboard.

Phase 4  NORMALISE FEATURES
         ATR-, volatility-, volume-z- and percentile-normalisation

Phase 5  BACKTEST ENGINE — BEFORE the hierarchical signal engine
         next-session fill, T+2 regulatory sellability, policy delay, costs, walk-forward
         Without this every [D] parameter stays a guess.

Phase 6  STRATEGY REGISTRIES
         valuation strategy · signal profile · weight policy

Phase 7  HIERARCHICAL RECOMMENDATION
         MarketGate × Sector × Archetype × individual evidence
         Weights fitted at regime level only.

Phase 8  VALIDATION
         walk-forward · Deflated Sharpe with honest trials · placebo test
         Compare against mvp_fixed_v1 and simple benchmarks.

Phase 9  PROMOTE ONLY ROBUST PROFILES
         Reject sector-specific overfits and unstable thresholds.
```

**Phase 5 before Phase 7 is not negotiable.** Building the signal engine
first produces confident-looking recommendations that nobody — including
their author — can evaluate. That is precisely the failure mode the system
exists to replace.

---

# 22. KNOWN LIMITATIONS

**The delivered executable code is still the legacy v3.1 Phase-1 implementation even though the documents are now v3.3.** It contains SSI-specific code, but SSI is disabled by product-owner decision and must not be used for real-data ingestion. Therefore there is currently **no v3.3-compliant automated market-data adapter** and no provider-specific real-data validation claim.

**True historical point-in-time VN100 membership is still not present in the delivered data store.** The target source of truth is effective-dated HOSE review/rule evidence or another independently verified PIT archive. Historical runs using a current/manual snapshot must stay labelled `CURRENT_UNIVERSE_PROXY`; do not substitute a liquidity reconstruction and call it true VN100 history.

**Classification has not passed its placebo test.** Random assignment came
within 0.16 Sharpe of the real scheme, below the +0.20 threshold. With few
trades the test is under-powered, so this is *unproven* rather than
*disproven* — but no further work should build on classification until it
passes on real data with a meaningful trade count.

**The hierarchical grid cannot be fitted at full depth.** Approximately 9
signals per cell against a 30-signal minimum. §11.3 constrains fitting to
regime level; anything deeper requires either far more data or heavy
shrinkage.

**Every `[D]` parameter is uncalibrated**, and all measured results come from
synthetic data.

**Fundamental data at scale remains a source-governance problem.** Public disclosures arrive as PDF/HTML in inconsistent formats. Vietstock markets a professional DataFeed/API service that may become a licensed normalized secondary source after admission; CafeF exposes useful public pages/Excel exports but is validation/manual research by default. Do not make undocumented scraping the production foundation.

**The directional forecast may never activate.** If out-of-sample AUC does
not clear the gate on real data it will suppress itself permanently. That is
designed behaviour, not failure — but the feature may simply report
unavailable, indefinitely.

---



# 23. v3.3 SPECIFICATION STATUS, IMPLEMENTATION EVIDENCE AND VERIFICATION SOURCES

## 23.1. Current code vs v3.3 specification

The companion source package `vnquant_realdata_v3_1` remains the latest **delivered legacy implementation**. It includes an SSI adapter and historically passed **18/18 tests**, but this is no longer the active provider architecture. Under v3.3, the SSI path is disabled and that 18/18 result is retained only as evidence about the legacy codebase, not as proof that the v3.3 data path works.

v3.3 requires an SSI-free provider registry, `NO_ADMITTED_PROVIDER` state, generic source doctor/bootstrap contracts, Vietstock DataFeed admission work, CafeF/manual-import validation boundaries, reconciliation lineage and mandatory BRD/SRD synchronization. These v3.3 runtime changes are **SPECIFIED, NOT IMPLEMENTED**.

## 23.2. Verification sources (accessed 2026-09-10)

- https://api.vietstock.vn/
- https://dichvu.vietstock.vn/Service.aspx
- https://cafef.vn/du-lieu/lich-su-giao-dich-cafef-1.chn
- https://cafef.vn/du-lieu/lich-su-giao-dich-prc-4/trang-1-ceo_02019.chn
- https://english.luatvietnam.vn/law-on-securities-no-54-2019-qh14-dated-november-26-2019-of-the-national-assembly-179050-doc1.html
- https://staticfile.hsx.vn/Uploads/UploadDocuments/2487402/Form_Factsheet_MCIndices_VN_T08.2026.pdf
- https://staticfile.hsx.vn/Uploads/LocalFiles/ef15ff11e799483abd11677ad0443887/20250114_20241230_QD%20747%20HOSE%20Index%20Ground%20Rules.pdf
- https://thuvienphapluat.vn/van-ban/Chung-khoan/Decision-1541-QD-BTC-2025-prices-of-securities-services-applied-to-Vietnam-Exchange-655935.aspx
- https://vbpq.mof.gov.vn/DKC.FileManagement/FileStorage/File/104328
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

Community Cloud remains a resource-constrained, hibernating hosted environment whose documented limits may change; it is therefore a viewer plane, not the source-of-truth compute scheduler.


# 24. RESEARCH / ASSESSMENT → BRD/SRD SYNCHRONIZATION CONTRACT

## 24.1. Mandatory impact assessment

The product owner requires BRD/SRD synchronization after material research/assessment changes. `[GUESS]` The following machine-readable impact flag is the proposed implementation contract:

Every research/verification/assessment run must emit one of:

```text
DOC_IMPACT = NONE
DOC_IMPACT = BRD_AND_SRD
```

A material change to product rules, source policy, architecture, execution, risk, validation, model routing, implementation status or known limitations requires `BRD_AND_SRD` in the same work cycle.

## 24.2. Evidence ledger

`[GUESS]` Add a versioned research ledger:

```text
research_id
performed_at
question
sources[]
verified_facts[]
guesses[]
changed_assumptions[]
brd_sections_changed[]
srd_sections_changed[]
implementation_impact
validation_required
status
```

The ledger is not a replacement for BRD/SRD. Its job is to make it impossible for a decision to exist only in chat notes or an implementation report.

## 24.3. Status vocabulary

Use only these explicit lifecycle labels in documentation and artifacts:

```text
SPECIFIED
IMPLEMENTED
TESTED_OFFLINE
VALIDATED_REAL_DATA
PRODUCTION_ACCEPTED
REJECTED / RETIRED
```

A feature may have several applicable statuses (e.g. `IMPLEMENTED + TESTED_OFFLINE`) but must never be described as real-data validated without actual real-data evidence.

## 24.4. Version invariant `[GUESS]`

After any material research/assessment change, BRD and SRD share the same project version. Source code is allowed to lag; when it does, the SRD must name the latest executable code version and the missing implementation delta.

**Current state — 2026-09-14:** BRD/SRD = **v3.5 SSI-Free DNSE-First Auto-Sync Baseline**. The formerly referenced standalone `vn100_multisource_feed_v1` artifact is absent from the working tree, Git history, and committed archives, so it is not a delivered executable subsystem. Maintained provider and source-sync code is integrated under `src/vnquant/`, with tests under `src/tests/`. Live provider validation remains pending; SSI stays DISABLED.


# 25. SSI-FREE RUNTIME MIGRATION CONTRACT `[GUESS]`

## 25.1. Required code changes

The next Codex Cloud implementation milestone must:

1. Remove `ssi-sdk` from the target runtime dependencies.
2. Remove/disable SSI credential checks and SSI-specific doctor/bootstrap entry points.
3. Keep the generic `MarketDataProvider` boundary and add an explicit `NO_ADMITTED_PROVIDER` runtime state.
4. Refuse real-data pipeline execution when no provider is admitted; do not substitute synthetic, Yahoo, CafeF scraping or any undocumented endpoint.
5. Add `SourceSyncOrchestrator` and an auto-refresh-on-run sync check; remote fetches are incremental and freshness-driven, and Streamlit widget reruns must not duplicate the same provider fetch. `[GUESS]`
6. Keep a controlled file-import adapter for authorized/manual CSV/Excel only as fallback/debug/recovery/bootstrap with provider/source metadata, retrieval/import timestamp and file hash.
7. Integrate the standalone DNSE-first market-data module into the main app; live DNSE Source Admission must pass before it becomes production operational.
8. Keep Vietstock DataFeed contract-gated; enable live calls only after authorized API/schema material is available and Source Admission passes.
9. Preserve official-source ingestion/import for VN100 review evidence, corporate actions and disclosures.
10. Add regression tests proving no SSI dependency is required, auto-refresh semantics are respected, and no silent fallback occurs.

## 25.2. Minimum acceptance tests

```text
test_no_ssi_runtime_dependency
test_no_ssi_credentials_required
test_no_admitted_provider_blocks_real_mode
test_synthetic_never_fallbacks_into_real_mode
test_manual_import_keeps_lineage_and_hash
test_undocumented_endpoint_cannot_be_admitted
test_pit_universe_requires_effective_dating
test_app_run_invokes_source_sync_check
test_fresh_cache_avoids_duplicate_remote_fetch
test_stale_data_triggers_incremental_fetch
test_streamlit_rerun_does_not_refetch_same_state
test_manual_file_not_required_for_normal_startup
```

## 25.3. Status

`SPECIFIED`. No v3.3-compliant executable build has yet been produced or real-data validated.




# 26. v3.4 AUTO-REFRESH DATA INGESTION CONTRACT `[GUESS]`

## 26.1. Runtime objective

Normal application startup must not wait for a user-prepared CSV/XLSX. Each application start/run invokes an idempotent provider synchronization check before actionable analytics are produced.

```text
Streamlit/app process
      ↓
SourceSyncOrchestrator.sync(required_capabilities)
      ↓
ProviderRegistry.get_admitted_provider(capability)
      ↓
FreshnessPolicy.evaluate(local_state, expected_market_state)
      ↓
FRESH  → no network fetch → canonical cache
STALE  → incremental fetch → immutable snapshot → normalize → DQ → commit
ERROR  → degraded cached mode or fail closed according to policy
```

The sync layer is below the UI. UI code must not call provider HTTP methods directly.

## 26.2. Proposed interfaces

```python
class MarketDataProvider(Protocol):
    provider_id: str

    def capabilities(self) -> set[str]: ...
    def health(self) -> ProviderHealth: ...
    def fetch(self, request: ProviderRequest) -> RawProviderResponse: ...


class SourceSyncOrchestrator:
    def sync(
        self,
        required_capabilities: set[str],
        *,
        force: bool = False,
    ) -> SyncReport: ...
```

`SyncReport` persists at least:

```text
run_id
started_at
finished_at
required_capabilities
provider_id
source_policy_version
fresh_before
remote_fetch_performed
requested_range
raw_snapshot_ids
canonical_rows_written
dq_status
last_accepted_market_date
failure_reason
mode = LIVE | CACHE_ONLY | DEGRADED_CACHED_DATA | FAILED
```

## 26.3. Incremental fetch algorithm

For each capability:

```text
1. resolve ADMITTED provider
2. read local watermark + provider revision metadata
3. determine expected latest market state
4. run freshness/completeness test
5. if fresh → return cached state
6. if stale → request only missing/recheck interval
7. snapshot raw response before transformation
8. normalize to canonical schema
9. reconcile against authority/secondary evidence when required
10. run DQ gate
11. atomically publish accepted canonical revision
12. persist SyncReport
```

A provider/config-specific recheck lookback may be used to detect vendor corrections; the window is `[GUESS]` until measured against the admitted provider's actual revision behaviour.

## 26.4. Streamlit rerun protection

Streamlit reruns must not produce accidental API storms. `[GUESS]`

The implementation must provide:

- process/session-level synchronization lock;
- deterministic freshness key;
- cached `SyncReport` reuse while the underlying freshness state has not changed;
- an explicit **Refresh now** action for a forced check;
- no provider fetch in presentation-only functions.

`st.cache_resource` / `st.cache_data` may be used where appropriate, but correctness must live in the application sync service rather than depend only on Streamlit caching. `[GUESS]`

## 26.5. Vietstock adapter admission

Official Vietstock service material verifies that DataFeed is supplied through **API or Sync Data** for professional integration. Public pages currently do not provide enough implementation contract detail for this project to safely hard-code production endpoints/authentication/schema/rate limits.

Target class:

```text
VietstockDataFeedProvider
status = IMPLEMENTED_GENERIC_CONTRACT_GATE / TESTED_OFFLINE / NOT_ADMITTED / NOT_LIVE_VALIDATED
```

Before implementation can move to `VALIDATED_REAL_DATA`, obtain authorized vendor material or credentials and record:

```text
base URL / environment
authentication contract
rate limits / quotas
request parameters
response schemas
field units / timezone / date semantics
raw vs adjusted price semantics
history depth / revision policy
corporate-action semantics
fundamental publication timestamps
licence / retention / redistribution rights
```

Do not implement against reverse-engineered `finance.vietstock.vn` or undocumented browser endpoints as a substitute for DataFeed.

## 26.6. Startup policy

`[GUESS]` Recommended application behaviour:

```text
startup
  -> sync check required datasets
  -> if fresh: launch analytics immediately from canonical store
  -> if stale and provider available: incremental refresh, then analytics
  -> if refresh fails but accepted cache is still usable: DEGRADED_CACHED_DATA
  -> if cache is unusable/missing: block actionable analytics
```

The UI must display `data_as_of`, `last_sync_at`, `provider_id`, `sync_mode`, and DQ status.

Both `src/app.py` startup and direct `src/vnquant/jobs/pipeline.py` invocation must consume the governed synchronization result before loading bars or running features. When neither an admitted provider nor a policy-accepted cache exists, the persisted and published status is `NO_ADMITTED_PROVIDER`; feature, signal, candidate, and recommendation generation is blocked. A permitted cache result exposes its provider, age, last successful synchronization, DQ status, cache-acceptance decision, and degraded mode. Blocked publication removes older candidate/sector artifacts so they cannot be mistaken for current output. No CSV, synthetic, CafeF, or undocumented source is selected implicitly.

## 26.7. Manual importer role

The file importer remains a first-class engineering tool but a second-class runtime source. It is reserved for controlled bootstrap/recovery/debugging/provider-comparison/official one-off evidence and test fixtures. Normal daily startup must not depend on it.

## 26.8. Additional acceptance tests

```text
test_app_run_invokes_source_sync_check
test_fresh_cache_avoids_duplicate_remote_fetch
test_stale_data_triggers_incremental_fetch
test_sync_is_idempotent_for_same_freshness_state
test_concurrent_reruns_share_sync_lock
test_provider_failure_records_degraded_or_failed_state
test_degraded_mode_displays_data_age
test_no_synthetic_or_undocumented_fallback
test_manual_file_not_required_for_normal_startup
test_raw_payload_persisted_before_canonical_commit
```

The dedicated offline harness is maintained in
`src/tests/test_auto_sync_acceptance.py`; its provider fixtures never perform
network I/O. Passing these tests demonstrates runtime mechanics only and does
not admit or live-validate DNSE, Vietstock, or CafeF.

## 26.9. Implementation status

Canonical validation is owned by `src/vnquant/data/quality.py`; `schema.py` retains
only schema contracts and a compatibility facade. DQ evaluations carry an immutable
canonical revision identifier and are append-persisted alongside synchronization
reports. The recommendation engine caps confidence to the DQ score below 70 and
marks output non-actionable below 50, using the existing BRD `[D]` thresholds.
Stale data, unresolved corporate actions, missing lineage/admission, ambiguous units
or adjustment semantics, blocked trading status, invalid/missing sessions, and
venue-band breaches fail closed; disagreement remains visible and is never averaged.

`IMPLEMENTED / OFFLINE_TESTED` as of 2026-09-14 for the application sync-service contract. Provider, cache, DQ, and source-sync capabilities are maintained under `src/vnquant/` and tested from `src/tests/`. The default weekday-only expected-session calendar and revision recheck intervals are configurable `[GUESS]` values pending authoritative calendar and admitted-provider revision evidence. Live Source Admission and real-data validation remain pending, so the default runtime still fails closed.

> ## DISCLAIMER
>
> Technical specification for **personal research software**. Not investment
> advice, not legal advice.
>
> Every parameter tagged `[D]` must be calibrated — following §20.4 — before
> being trusted with real capital. Every measured result quoted here comes
> from synthetic data.
>
> Designed for personal use by a single person, self-hosted. Publishing or
> selling its output as investment recommendations may carry legal
> consequences under Vietnamese securities law, and redistributing the
> underlying free data may breach its provider's terms of use.
>
> Securities bought on trade date T are allocated/sellable in the afternoon of T+2 under the current cycle. The risk model separately retains a conservative three-limit-move pre-settlement stress (~−19.56% on HOSE); this is not an absolute worst case and does not imply three full legally locked sessions.


# 27. v3.5 DNSE-FIRST MULTI-SOURCE MODULE CONTRACT

## 27.1. Verified provider surface

DNSE public/official material now establishes enough stable surface to implement a read-only market-data adapter without guessing the core operations:

```text
GET /instruments
GET /price/ohlc
GET /price/:symbol/foreign-trading
working dates / session / bid-ask / trades
official Python SDK: DNSEClient
WebSocket market-data examples
```

The official SDK example uses:

```python
client.get_instruments(..., index_name="", limit=100, page=1, dry_run=False)
client.get_ohlc(
    bar_type="STOCK",
    query={"symbol": "HPG", "resolution": "1", "from": ..., "to": ...},
    dry_run=False,
)
```

For this EOD module, `resolution="1D"` is used as `[GUESS]` based on the documented WebSocket daily-resolution token. The exact REST resolution acceptance, live response and accepted VN100 index filter still require runtime verification.

## 27.2. Missing standalone artifact and maintained path

The previously documented `vn100_multisource_feed_v1/` tree was not found in the repository working tree, any reachable Git commit, or the committed ZIP archives during the 2026-09-14 audit. Its proposed `vn100_feed/`, standalone tests, packaging files, and examples are therefore **not delivered repository content**.

The maintained, unversioned implementation path is `src/vnquant/`, including:

```text
src/vnquant/data/providers/   DNSE, contract-gated Vietstock, CafeF reference adapters
src/vnquant/data/storage.py   canonical SQLite storage
src/vnquant/data/quality.py   data-quality validation
src/vnquant/data/source_sync.py persisted governed synchronization
src/vnquant/jobs/doctor.py    application doctor checks
src/tests/                    integrated offline tests
```

This integrated code retains the fail-closed and provider-governance requirements in this section. It is not evidence of a delivered standalone scanner package, provider admission, or real-data validation.

## 27.3. Offline evidence correction

The formerly documented package-local commands cannot be reproduced because neither `vn100_feed/` nor its standalone `examples/` and packaging metadata were committed:

```text
python -m compileall -q vn100_feed examples   NOT REPRODUCIBLE (paths absent)
python -m pytest -q                           historical standalone result withdrawn
```

Validation of maintained code must instead be run from `src/` using its checked-in test configuration and dependencies:

```text
cd src
python -m compileall -q vnquant             PASS
python -m pytest -q                          99 passed (2026-09-14)
```

Such fixture/offline tests prove implementation mechanics only; they do not establish external API availability, live schema correctness, data accuracy, trading alpha, Source Admission, or `REAL_DATA_VALIDATED` status.

## 27.4. Live admission checklist

Before `DNSE_OPENAPI` is marked ADMITTED:

```text
[ ] valid user DNSE API Key/Secret
[ ] official SDK import/version pinned in deployment
[ ] /instruments live schema captured and hashed
[ ] VN100 index filter semantics verified
[ ] exactly/currently expected membership reconciled to official evidence
[ ] /price/ohlc live schema and VND units verified
[ ] daily resolution/date-boundary semantics verified
[ ] history depth measured
[ ] working dates/calendar verified
[ ] rate-limit/quota behaviour recorded
[ ] vendor correction/revision behaviour measured
[ ] representative cross-source OHLCV reconciliation passed
[ ] raw response retention/licence approved
```

Until then, provider status remains **NOT LIVE VALIDATED / NOT ADMITTED**. The missing standalone artifact must not be described as implemented, offline-tested, or `VALIDATED_REAL_DATA`.


# 28. v3.5 VERIFICATION SOURCES

- https://developers.dnse.com.vn/docs/guide/intro/api_platform/
- https://developers.dnse.com.vn/docs/dnse/market-data/
- https://developers.dnse.com.vn/docs/dnse/get-instruments/
- https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/
- https://developers.dnse.com.vn/docs/dnse/get-foreign-trading/
- https://github.com/dnse-tech/openapi-sdk
- https://pypi.org/project/dnse-sdk-openapi/
- https://api.vietstock.vn/
- https://dichvu.vietstock.vn/dao-tao/khoa-hoc---nhap-mon-tai-chinh-va-chung-khoan?index=44
- https://cafef.vn/du-lieu/lich-su-giao-dich-sdk-1.chn


# 31. HISTORICAL-ARTIFACT ISOLATION

The repository may retain `legacy/vnquant_realdata_v3_1_gptcode_impl.zip` and its disabled implementation report for audit history. The archive's SSI adapter and SSI-specific doctor/bootstrap are non-executable evidence, not source inputs.

The build configuration shall use `src/` layout and an explicit `vnquant` package allow-list. Source and wheel artifacts shall exclude `legacy/`, ZIP files, historical implementation reports, and tests. Declared runtime/optional dependencies shall contain neither SSI packages nor local/archive references. Pytest shall discover only `src/tests` and shall not recurse into `legacy`. A checkout-root `import legacy` shall fail closed, while `vnquant.data.ssi` shall remain unresolved. Automated boundary tests and a built-artifact inspection command shall enforce these properties. Existing negative SSI-retirement tests remain required.
