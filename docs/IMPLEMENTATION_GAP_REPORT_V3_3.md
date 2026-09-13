# VN100 Quant Platform — v3.3 Implementation Gap Report

**Audit date:** 2026-09-13  
**Specification baseline:** v3.3 SSI-Free Multi-Source (2026-09-10)  
**Implementation audited:** `src/`, reported by the package as v3.1.0  
**Audit status:** documentation-only assessment; no runtime functionality changed

## 1. Purpose and governing requirements

This report audits the delivered executable repository against the v3.3
SSI-Free provider and data-governance requirements. In particular, it assesses
the required retirement of SSI FastConnect, provider admission and fail-closed
behaviour, provider abstraction, source lineage/raw evidence, provider-related
tests, specification-to-code discrepancies, and undocumented assumptions.

The governing business requirements are BRD §§17, 19, 23–27. The corresponding
software contracts are SRD §§2–7, 19–25. The most immediate required outcome is
the BRD §27.3 / SRD §25 migration contract: SSI must not be a runtime dependency,
no automated provider is currently admitted, and a real-data request must fail
closed with `NO_ADMITTED_PROVIDER` rather than use SSI or an implicit fallback.

## 2. Scope and method

The audit covered all tracked repository files outside Git metadata, including:

- dependency manifests and environment examples;
- application and command entry points;
- every Python module under `src/vnquant/`;
- all 18 collected tests under `src/tests/`;
- current baseline, BRD, SRD, changelog, READMEs, configuration guidance, and
  retained legacy archive names.

The review used repository enumeration, full-text searches for provider/source,
SSI, fallback, lineage, snapshot, admission, and `[GUESS]` concepts, direct
source inspection, and execution of the existing test suite. It did not invoke
any network provider, ingest market data, inspect provider credentials, or
perform real-data reconciliation.

### Severity scale

| Severity | Meaning |
|---|---|
| **Critical** | Directly permits or instructs a provider-policy violation, or can misrepresent a non-compliant path as real-data ready. |
| **High** | Required v3.3 safety/governance control is absent, so canonical real-data operation cannot be admitted. |
| **Medium** | Important contract, lineage, validation, or specification coverage is incomplete but does not by itself activate a prohibited feed. |
| **Low** | Documentation, naming, or maintainability discrepancy that can mislead implementation or audit work. |

## 3. Executive conclusion

The repository matches its documented **legacy v3.1 Phase-1** status; it is not
a v3.3-compliant executable build. The primary bootstrap and doctor commands
instantiate SSI directly, the local dependency set requires `ssi-sdk`, and the
environment/README/UI still direct users toward SSI. There is no admission
registry, no admission state model, and no `NO_ADMITTED_PROVIDER` exception or
status. Consequently, the real-data path does not fail closed under v3.3; it
attempts the prohibited SSI path and fails for SSI configuration/dependency
reasons instead.

A minimal `MarketDataProvider` abstract base class and an offline CSV adapter do
exist, as does a small payload snapshot helper. These are useful v3.1 building
blocks, but they do not implement v3.3 source governance: callers are hard-wired
to SSI, the interface has no identity/trust/capability contract, CSV imports do
not retain source admission or file provenance, and snapshots omit required
timestamps, request parameters, adapter versions, immutable registry records,
and links from canonical observations to accepted evidence.

The existing suite passes **18 tests**. No test directly imports or instantiates
SSI, so the tests themselves do not require SSI credentials or network access.
However, that is a coverage gap rather than evidence of SSI-free compliance:
none of the seven minimum SRD §25.2 migration tests exists, and the runtime
dependency check explicitly treats `ssi_sdk` as mandatory.

## 4. SSI legacy inventory

| Legacy item | Current role/evidence | Required disposition | Severity | Recommended milestone |
|---|---|---|---|---|
| `src/vnquant/data/ssi.py` | Complete SSI FastConnect adapter, credential lookup, SDK import, authentication, current-index discovery, and OHLC history retrieval. | Remove from the v3.3 runtime tree or place in an unreachable archival location; no canonical writes. | **Critical** | **M0 — SSI runtime excision** |
| `src/vnquant/jobs/bootstrap.py` | Imports and instantiates `SSIFastConnectV3Provider` unconditionally. It is the only implemented bootstrap path. | Replace in a later implementation PR with a provider-registry lookup that fails closed when none is admitted. | **Critical** | **M0 — SSI runtime excision** |
| `src/vnquant/jobs/doctor.py` | SSI-specific preflight, SSI default symbol, authentication language, and SSI configuration exception handling. | Disable/remove this entry point; a generic source doctor may be implemented only against an admitted provider. | **Critical** | **M0 — SSI runtime excision** |
| `src/requirements-local.txt` | Pins `ssi-sdk==3.2.1`. | Remove SSI SDK from target runtime dependencies. | **Critical** | **M0 — SSI runtime excision** |
| `src/vnquant/jobs/dependencies.py` | Declares `ssi_sdk` a mandatory local dependency and fails when absent. | Limit checks to approved generic dependencies; provider clients become conditional only after admission. | **High** | **M0 — SSI runtime excision** |
| `src/.env.example` | Solicits three SSI credentials. | Remove SSI variables and retain only provider-neutral/local-mode settings. | **Critical** | **M0 — SSI runtime excision** |
| `src/README.md` | Calls SSI the real provider contract, documents SSI credentials, doctor/bootstrap, and describes the build as real-data ready. | Replace with v3.3 fail-closed status and explicitly state that no automated provider is admitted. | **Critical** | **M0 — SSI runtime excision** |
| `src/app.py` | Branding says “v3.1 — Real-Data Ready”; notes describe SSI integration as active market-data-only integration. | Remove the readiness claim and expose provider-policy state without suggesting SSI is usable. | **High** | **M0 — SSI runtime excision** |
| `src/config/universe/README.md` | Says current VN100 may be queried through SSI. | Point only to controlled official/effective-dated evidence or a future admitted provider. | **High** | **M0 — SSI runtime excision** |
| `src/config/sector/README.md` and `src/vnquant/data/sector_membership.py` | Current-sector proxy is explicitly described as SSI ICB and its warning embeds SSI. | Make proxy provenance provider-neutral; do not rely on SSI security master. | **High** | **M1 — provider-neutral metadata/import** |
| `src/IMPLEMENTATION_REPORT_GPTCODE_STYLE.md` | Historical implementation report presents SSI scope and unavailable-credential limitation. | Retain only if prominently labelled legacy/non-v3.3 evidence; it must not serve as the current runbook. | **Medium** | **M0 — documentation alignment** |
| `legacy/vnquant_realdata_v3_1_gptcode_impl.zip` | Archived legacy source package by name. | May remain as provenance if clearly non-runtime; ensure packaging/deployment cannot consume it. | **Low** | **M0 — archive boundary check** |

## 5. Requirement-to-implementation gap matrix

| Requirement | BRD reference | SRD reference | Current implementation | Gap | Severity | Recommended milestone |
|---|---|---|---|---|---|---|
| SSI FastConnect is out of scope and cannot be primary, fallback, bootstrap dependency, or validation prerequisite. | §§24, 27.1–27.3 | §§4, 6.1, 6A.1, 20.1, 25.1 | SSI adapter is live; bootstrap/doctor instantiate it directly; SDK and credentials are required/documented. | Active executable path is the exact provider path prohibited by v3.3. | **Critical** | **M0 — SSI runtime excision** |
| No automated provider is admitted; real-data operation must fail closed with `NO_ADMITTED_PROVIDER`. | §§17.1, 24.2, 25.1–25.3, 27.2–27.3 | §§6.1A–6.1B, 6A.1, 25.1–25.2 | No admission state, registry lookup, named exception, status artifact, or UI state exists. Bootstrap instead attempts SSI and may raise SSI credential/import errors. Pipeline can consume any pre-existing Parquet bars without validating admission. | Required fail-closed state is wholly absent and canonical processing is not admission-gated. | **Critical** | **M0 — fail-closed provider policy** |
| Provider selection must be generic, capability-aware, and governed by trust tier/admission state. | §§25.1–25.3 | §§6.1, 6.1A, 6A.1, 6A.5, 25.1 | `MarketDataProvider` exposes only membership/history methods. No `provider_id`, trust tier, capabilities, source registry, admission record, or selection service exists; entry points import SSI concretely. | An interface exists nominally, but the provider-governance abstraction and dependency inversion are missing. | **High** | **M1 — provider registry and admission model** |
| A provider may exist in code without being admitted; only an admitted provider can write canonical data. | §§17.1, 25.2 | §§6.1A, 6A.1, 7 | `Warehouse.write_bars` accepts any frame and has no source/admission check. CSV and SSI output can be persisted equally. | No enforcement boundary separates research/quarantine observations from canonical bars. | **High** | **M1 — canonical-write admission gate** |
| Fallback must be explicit and limited to an already-admitted alternate; no Yahoo, CafeF scraping, undocumented endpoint, or synthetic substitution. | §§19.1, 24.2, 25.4, 27.3 | §§6.1B, 6A.1, 25.1 | No Yahoo/CafeF/vnstock/synthetic network fallback was found. However, no fallback policy object, provenance fields, or negative enforcement exists. Pipeline processes whatever bars already exist. | No current silent fallback implementation was found, but the invariant is neither represented nor tested. | **High** | **M1 — explicit fallback policy** |
| Raw provider responses/authorized files must be snapshotted before normalization with provider, time, request/import parameters, hash, and adapter/importer version; revisions are additive. | §§17.1, 25.2, 25.4 | §§6.3, 6A.2, 6A.6, 7 | `Warehouse.snapshot_payload` writes bytes plus provider/name/SHA-256. SSI/bootstrap never calls it. CSV reads normalized files directly. Metadata lacks request/import time, parameters, adapter version, source reference, admission/policy version, and immutable revision identity. | Helper is partial and disconnected from ingestion; required evidence chain and additive revisions are absent. | **High** | **M2 — immutable evidence and lineage** |
| Canonical observations/decisions must retain accepted provider, compared observations, reconciliation status/reason, and source-policy version. | §§17.1, 25.3–25.4 | §§6.1B, 6A.6, 7 | Bar schema carries only a provider string. No provider-observation or canonical-decision model/table exists; no reconciler exists. | Field-level lineage and reversible reconciliation are absent. | **High** | **M2 — observations and reconciliation** |
| Controlled manual/authorized CSV/Excel feasibility imports must preserve source basis, import timestamp, file hash, adapter version, and canonical invariants. | §§24.2, 25.1–25.4, 27.2 | §§6A.2–6A.5, 25.1 | `CSVProvider` accepts CSV files and adds provider=`csv`; it does not record authorization/access basis, source document, hash, imported-at, version, semantics, or admission/quarantine state. It also does not run quality validation internally. No Excel importer exists. | Existing CSV adapter is a fixture/offline reader, not the governed manual-import contract. | **High** | **M2 — controlled manual import** |
| Source admission must record rights, terms, schema semantics, units/timezone/trading-date rules, adjustment/revision policy, lineage method, validation plan, ownership, and review dates. | §§17.1, 25.2 | §§6.1A, 7 | No `config/providers.yaml`, source-admission model, persistent table, lifecycle state, or review metadata exists. | Complete admission control plane is missing. | **High** | **M1 — provider registry and admission model** |
| Data Quality must incorporate staleness, missing bars, suspicious gaps, provider disagreement, unresolved corporate actions, and source trust; below 50 blocks recommendations. | §17 | §§6.5–6.6 | Validator checks schema, emptiness, duplicates, OHLC, volume, positive prices, and sort order. A generic severity deduction computes a score. Signal/pipeline code never applies the DQ score. | Most specified DQ inputs and the recommendation cap/block integration are missing. Source admission is not part of DQ. | **High** | **M3 — ingestion/DQ gate integration** |
| Provider-missing sessions must retain explicit status and must not be silently forward-filled or treated as genuine zero-volume bars. | §§17, 19.1 | §§7, 8.4 | No explicit `bar_present` or trading-status representation is persisted. No OHLC forward-fill was found in current code, but expected-session comparison is absent. | The code avoids an obvious fill, yet cannot distinguish provider missing, suspension, no trade, not listed, or unknown. | **High** | **M3 — session/status integrity** |
| Historical universe and sector metadata must be effective-dated; current membership/classification can only be an explicit proxy. | §§2.4, 7.2, 19.1, 24.2 | §§6.1, 6.7, 6A.4, 7 | `UniverseStore` and sector PIT mapping support effective dates and tests cover explicit proxy labels. But bootstrap writes only a current SSI snapshot and pipeline hard-codes `CURRENT_UNIVERSE_PROXY`; current sector fallback relies on SSI ICB. | Useful PIT primitives exist, but ingestion and pipeline do not resolve the as-of universe, and proxy metadata is SSI-bound. | **High** | **M3 — PIT integration** |
| Application must not claim real-data readiness/validation until an admitted provider and real data have passed the required controls. | §§21, 23, 25.5, 27.2 | §§19, 22–25 | `src/README.md` and UI title call the v3.1 build “Real-Data Ready”; implementation report calls SSI a real provider path. Baseline/spec correctly say no v3.3 real-data validation. | Runnable-surface claims conflict with current baseline and can be mistaken for validation/readiness. | **Critical** | **M0 — documentation alignment** |
| Minimum SSI-free migration regression tests must prove no SSI dependency/credentials, fail-closed real mode, no synthetic fallback, lineage/hash, no undocumented admission, and PIT effective dating. | §27.3 | §§19.1–19.3, 25.2 | Existing 18 tests cover selected v3.1 strategy/data safeguards. None imports SSI, but no v3.3 provider-policy test exists. Dependency checker still requires SSI SDK. | All seven minimum migration acceptance tests are missing. | **High** | **M0/M1/M2 — tests alongside each migration slice** |
| Hosted view plane is read-only and consumes only sanitized artifacts. | §23 | §§1–2, 17.4 | `app.py` reads publish files only. No data-provider import was found in the UI. | Broad plane boundary is present, but no automated import-discipline/privacy scan exists, and source-policy/admission status is absent from published artifacts. | **Medium** | **M4 — view-plane contract tests** |
| v3.3 target architecture includes classification, profile/weight registries, sector-specific valuation, seven gates, dual stops/sizing, exits, forecasting, calibration, and walk-forward validation. | §§5–16, 23 | §§8–16, 19, 21 | Delivered code is a small Phase-1 baseline: indicators, relative strength, regime, simplified candidate selection, simple pullback execution/backtest, and selected market rules. Most target modules in SRD §3 do not exist. | Implementation remains substantially behind the broader v3.3 target, consistent with baseline status. This is not only a provider migration gap. | **High** | **M3–M9 — follow SRD §21 sequence** |

## 6. Provider abstraction assessment

### Present

- `MarketDataProvider` establishes two abstract operations:
  `current_index_members` and `daily_history`.
- `SSIFastConnectV3Provider` and `CSVProvider` conform to that narrow shape.
- Canonical frame columns include a `provider` string.

### Missing for v3.3

1. Stable `provider_id`, trust tier, capabilities, adapter version, and declared
   role on the provider contract.
2. `SourceAdmission` and lifecycle states (`RESEARCH_ONLY`, `QUARANTINED`,
   `VALIDATION`, `ADMITTED`, `SUSPENDED`, `RETIRED`).
3. `SourceRegistry.get_admitted_provider(capability=...)` and a named
   `NoAdmittedProvider`/`NO_ADMITTED_PROVIDER` result.
4. A canonical-write guard that checks admission at the storage boundary.
5. Provider health, explicit admitted fallback selection, and persistence of
   primary/actual provider plus fallback reason.
6. Provider observations and canonical decisions at field granularity.
7. Cross-provider semantic reconciliation.
8. A provider-neutral doctor and bootstrap contract.
9. Governed official/manual importers distinct from a generic fixture reader.

## 7. Source lineage and raw snapshot assessment

`Warehouse.snapshot_payload` is the only raw-evidence mechanism found. It is
not called by either implemented provider path or bootstrap. Its sidecar stores
only provider, logical name, and SHA-256; therefore it cannot establish when,
how, under which adapter/policy, or with what rights/parameters an observation
was obtained. `write_bars` overwrites each symbol's Parquet file, so accepted
canonical history is not revision-addressed and no canonical record points back
to an immutable payload. The DuckDB views expose current Parquet outputs but no
`provider_snapshots`, `source_admission`, `provider_observations`, or
`canonical_decisions` tables specified by SRD §7.

This means the repository has **partial snapshot utility code but no end-to-end
lineage support**.

## 8. Test audit

### Existing result

Executed from `src/`:

```text
python -m pytest -q
18 passed, 390 warnings in 1.10s
```

All warnings originate in `tests/test_relative_strength.py` from construction
of `pandas.Timedelta(days=i)` with the installed NumPy/Pandas combination; they
do not indicate a provider test failure.

### SSI dependence and v3.3 coverage

- **Direct SSI-dependent tests found:** none. No test imports
  `vnquant.data.ssi`, `ssi_sdk`, SSI jobs, or SSI credentials.
- **Indirect runtime inconsistency:** `vnquant.jobs.dependencies` declares
  `ssi_sdk` mandatory, but this path is not exercised by tests.
- **Provider abstraction tests found:** none for provider identity,
  capabilities, admission state, or registry selection.
- **`NO_ADMITTED_PROVIDER` tests found:** none; the state/exception does not
  exist.
- **Lineage tests found:** none for snapshots, hashes, import timestamps,
  request parameters, adapter versions, revisions, or canonical decisions.
- **Fallback-policy tests found:** none.
- **Manual-import governance tests found:** none.
- **Existing useful adjacent coverage:** explicit PIT/proxy universe behaviour,
  explicit current-sector proxy labelling, OHLC validation, Panic/Bear
  suppression, missing-turnover regime protection, next-session-only execution,
  conservative exact-touch handling, settlement/policy dates, costs, and
  corporate-action anomaly naming.

The passing result is therefore valid legacy regression evidence only; it is
not evidence that the v3.3 provider contract is implemented.

## 9. BRD/SRD/implementation discrepancies

### 9.1. Specification versus implementation

The principal discrepancy is intentional but unresolved: BRD §26.4 and SRD
§§22–25 say code remains legacy v3.1, while executable documentation and UI
still describe that legacy code as “Real-Data Ready.” The version itself is
also explicit in `vnquant.__version__ == "3.1.0"`. No code state supports the
v3.3 provider lifecycle, fail-closed behaviour, or reconciliation schema.

The implementation also centralizes some thresholds inside
`recommendations/engine.py`, not in the single `constants.py` required by SRD
§3, and numerous numerical decisions remain distributed through features,
regime, execution, backtest, market rules, and sector scoring.

### 9.2. Internal documentation discrepancies

1. `docs/CURRENT_BASELINE.md` names BRD/SRD files with an embedded `-v3.3-`
   segment, but the tracked English files do not use those names.
2. `AGENTS.md` requires `docs/CHANGELOG_SSI_FREE_MULTI_SOURCE.md`, while the
   tracked file is `docs/CHANGELOG_V3.3_SSI_FREE_MULTI_SOURCE.md`.
3. SRD §16 Validation A says adjustment-ratio arithmetic should recover a
   stock-dividend and cash-dividend ex-date/magnitude. This conflicts with BRD
   §§19.2/24.1 and SRD §6.4, which correctly state that adjustment ratios cannot
   identify legal action type and official disclosures must supply it. The
   current unit test correctly checks that action type remains `UNKNOWN`.
4. SRD §3 says `constants.py` is the only place numeric parameters live, but
   that module does not exist and the implementation distributes thresholds.
5. SRD §19.2 names `test_no_magic_numbers` as a high-priority target, but it is
   absent, allowing discrepancy 4 to remain undetected.

No BRD/SRD files were changed in this audit. Item 3 is a material internal
specification inconsistency and should be corrected in a synchronized BRD/SRD
documentation milestone rather than silently altering one governing document
inside this implementation inventory PR.

## 10. Undocumented or incompletely documented `[GUESS]` assumptions

The following code-level assumptions are not consistently marked `[GUESS]` or
traceable to an exact BRD parameter. Some may be reasonable legacy defaults;
the gap is provenance and governance, not a claim that an alternative value is
correct.

| Assumption in implementation | Evidence/current use | Specification issue | Severity | Recommended milestone |
|---|---|---|---|---|
| Structural-reversal RSI threshold `32` and short-RS threshold `25`. | `features/technical.py` and `recommendations/engine.py`. | BRD defines family intent but does not register these values in §20.4. Only the feature comment marks the broad hypothesis `[D]`; the thresholds are not literal `[GUESS]`. | **High** | **M3 — parameter registry review** |
| Sector eligibility floor `45`. | `SECTOR_MIN` in `recommendations/engine.py`. | BRD Gate 3 requires sector context but does not define a sector-score minimum of 45. Comment calls thresholds `[D]`, not the required literal `[GUESS]`. | **High** | **M3 — parameter registry review** |
| Momentum volume z-score floor `0.5`. | Candidate routing in `recommendations/engine.py`. | BRD requires expansion but does not register 0.5. It is unlabelled beside the code path. | **High** | **M3 — parameter registry review** |
| Candidate score weights and default component values. | `0.35/0.15/0.25`, nested `0.6/0.4`, and fallback `0.5` in `recommendations/engine.py`. | They differ from BRD §12.2's component structure and are only collectively called an explainable `[D]` baseline. No versioned config/provenance exists. | **High** | **M3 — scoring contract alignment** |
| Reversal signal candle/RSI recipe. | RSI <32, reclaim, above MA200, candle-position >0.60 in `features/technical.py`. | Described as a `[D]` hypothesis, but it is not a named BRD setup definition and contains unregistered thresholds. Under governance it is an explicit `[GUESS]`, not validated alpha. | **High** | **M3 — setup registry review** |
| Default max entry gap `2%`. | `backtest/engine.py`. | BRD §14.3 uses minimum of archetype default and measured security gap p90; no universal 2% value appears in the registry. | **High** | **M5 — execution model alignment** |
| Floor-lock detection as `next_open <= floor` and `next_high <= floor`. | `backtest/execution.py`. | Code acknowledges daily-bar uncertainty, but the proxy rule is unsourced/unmarked and HOSE-only. | **Medium** | **M5 — venue-versioned execution** |
| Fixed 20-session time stop. | `backtest/engine.py`. | It falls within the broad holding range but is not selected by setup/archetype or tagged at definition. | **Medium** | **M5 — exit policy alignment** |
| Equal-weight sector leadership weights `30/30/25/15`. | `market/sector_rotation.py`. | Correctly marked `[D]`, but governance additionally requires literal `[GUESS]` for newly invented/unsourced values and config versioning. | **Medium** | **M3 — parameter registry review** |
| Equal-weight index base `1000`. | `market/breadth.py`. | Harmless scale convention, but it is a numeric default outside the required constants/config boundary and has no documented provenance. | **Low** | **M3 — constants consolidation** |
| DQ penalties of 35 per error and 10 per warning. | `data/quality.py`. | BRD specifies DQ components and action thresholds, not these generic penalty values. They are unmarked guesses and may yield materially different gating. | **High** | **M3 — DQ model alignment** |
| Corporate-action factor-jump threshold `0.5%`. | `data/corporate_actions.py`. | No matching BRD §20 parameter or `[GUESS]` marker was found. | **High** | **M3 — parameter registry review** |
| Pipeline substitutes the equal-weight series for the cap-index leg. | `jobs/pipeline.py`; output is labelled proxy. | Labelling avoids silent misrepresentation, but using identical series weakens the mandatory dual-index divergence control and remains an unvalidated proxy. | **High** | **M3 — official index/manual evidence path** |

None of these assumptions was validated against real VN100 data during this
audit. They must not be presented as validated alpha.

## 11. Recommended milestones

1. **M0 — SSI runtime excision and truthful status.** Remove SSI SDK,
   credentials, adapter reachability, bootstrap/doctor wiring, and active SSI
   instructions; update executable branding; add tests for no SSI runtime
   dependency/credentials. This milestone should still fail closed and should
   not add a replacement automated provider.
2. **M1 — Provider policy core.** Add provider identity/capability contracts,
   source admission registry/lifecycle, canonical-write enforcement, explicit
   fallback policy, and `NO_ADMITTED_PROVIDER`; add the corresponding negative
   tests.
3. **M2 — Governed evidence/import/reconciliation.** Add immutable snapshots,
   authorized manual file import with hashes/provenance, provider observations,
   canonical decisions, and semantic reconciliation. Do not implement
   Vietstock until authorized schema/rights evidence passes admission.
4. **M3 — Data correctness integration.** Wire source trust and full DQ into
   pipeline/recommendation gates; integrate PIT universe/sector resolution and
   explicit trading-session status; consolidate and govern `[GUESS]`
   parameters.
5. **M4–M9 — Remaining SRD roadmap.** Continue in SRD §21 order: metadata,
   context/normalization, execution/backtest, registries, hierarchical
   recommendation, validation, and promotion only after robust evidence.

## 12. Assumptions, unresolved issues, and real-data status

### Audit assumptions

- Tracked source and documentation represent the intended repository state;
  generated/untracked runtime data was not present in the clean worktree.
- The legacy ZIP was inventoried as an archive by path/name; the active source
  tree was used for implementation findings.
- “Depends on SSI” distinguishes direct test imports from untested runtime
  dependencies. Under that definition no existing test directly depends on
  SSI, while the implemented real-data commands do.

No new trading threshold, provider capability, or provider-access assertion is
introduced by this report.

### Unresolved issues

- Whether the legacy SSI archive should be retained or moved is a repository
  governance decision; it must remain unreachable from runtime either way.
- Vietstock access, contract, schema, field semantics, rights, revisions, and
  capabilities remain unknown and must not be inferred from marketing material.
- CafeF remains manual/reference/authorized-export validation only; this audit
  did not inspect or approve any endpoint.
- No true historical PIT VN100 dataset or effective-dated production sector
  dataset was found.
- The material SRD corporate-action validation inconsistency identified in
  §9.2 requires synchronized BRD/SRD correction in a documentation milestone.

### Real-data status

**NOT VALIDATED.** No real market data was fetched, imported, processed,
reconciled, backtested, or used to validate provider access during this audit.
The successful test run used repository unit fixtures/synthetic frames only and
must not be interpreted as v3.3 provider validation or production-alpha
evidence.

