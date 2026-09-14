# BRD — VN100 Quant Research & Recommendation Platform

**Business Requirements Document · Stable filename · Current internal version 3.5**

| | |
|---|---|
| File | `BRD-VN100-Quant-Platform.md` |
| Current internal version | **3.5 — SSI-FREE DNSE-FIRST AUTO-SYNC — 2026-09-13** |
| Companion | `SRD-VN100-Quant-Platform.md` |
| Vietnamese companion | `BRD-VN100-Quant-Platform-VI.md` |
| Current status | **AUTO-SYNC, SSI-free. DNSE is the leading automated market-data candidate `[GUESS]`; its read-only adapter is implemented/offline-tested, but no provider is yet live-data validated/admitted. Vietstock remains contract-gated; CafeF remains explicit reference validation.** |

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
| **3.5.1** | **2026-09-13** | **Integrated stable `src/vnquant/data/providers/` implementations and default non-admitted registry entries; HTTP success remains separate from Source Admission. No live-data validation claim.** |
| **3.5.2** | **2026-09-13** | **Integrated the persisted `SourceSyncOrchestrator` below app/pipeline entry points, cache-lineage visibility, and fail-closed recommendation gating. Offline tests only; provider admission is unchanged.** |
| **3.5.3** | **2026-09-14** | **Repository audit found that `vn100_multisource_feed_v1` was never committed; removed its unreproducible 10/10 claim and recorded `src/vnquant/` as the maintained implementation path. Live-validation/admission status is unchanged.** |
| **3.5.4** | **2026-09-14** | **Hardened provider boundaries: Vietstock now requires endpoint semantics and retention rights in addition to the other authorized contract fields, CafeF cannot be admitted, and all DNSE live assumptions remain `[GUESS]`. Provider admission status is unchanged.** |
| **3.5.5** | **2026-09-14** | **Replaced the registry's documented-access flag with structured admission evidence and an enforced lifecycle. No admission/live-validation status changed.** |
| **3.5.6** | **2026-09-14** | **Made the synchronization outcome a mandatory app/pipeline gate, published `NO_ADMITTED_PROVIDER` when neither an admitted provider nor policy-accepted cache exists, exposed cache/degraded lineage, and suppressed stale actionable artifacts. Offline tested only.** |
| **3.5.7** | **2026-09-14** | **Completed capability-specific freshness, provider/capability watermarks, deterministic rerun keys, synchronization locking, incremental/recheck fetches, raw snapshot lineage, and explicit force refresh. Weekday-only calendar and recheck defaults remain `[GUESS]`; provider admission is unchanged.** |
| **3.5.8** | **2026-09-14** | **Required provider fetch contracts to expose immutable raw payloads and request metadata before normalization; bootstrap and sync now persist evidence before canonical bars, and authorized CSV imports hash every price/universe file. Offline tested only; provider admission is unchanged.** |
| **3.5.9** | **2026-09-14** | **Unified canonical DQ evaluation, persisted revision-linked DQ/sync history, and enforced the existing §17 confidence/actionability gates. Offline tested only; provider admission and real-data status are unchanged.** |
| **3.5.10** | **2026-09-14** | **Classified the archived v3.1 SSI adapter, doctor/bootstrap paths, and implementation report as historical/disabled, and added package, distribution, dependency, import, and test-discovery boundaries. Negative SSI-retirement tests remain mandatory.** |
| **3.5.11** | **2026-09-14** | **Implemented the §28.7 offline acceptance suite with fake DNSE SDK responses, injected Vietstock contract data, local CafeF HTML, deterministic time/calendar inputs, concurrency checks, and temporary storage. Full maintained suite: 99 passed; no provider admission or live-data-validation claim.** |
| **3.5.12** | **2026-09-14** | **Reconciled every implementation-status statement with tracked repository contents: the standalone `vn100_multisource_feed_v1` package is absent, while `src/vnquant/` is the maintained SSI-free implementation and its full suite passes 99 offline tests. No live-validation/admission claim.** |
| **3.5.13** | **2026-09-14** | **Consolidated the retained v3.3/v3.5 BRD copies and duplicate ZIP bundles into this stable canonical file. Historical wording and withdrawn claims remain recoverable in Git; no business rule, provider status, or live-validation status changed.** |

**Governance:** after every material research/assessment/implementation discovery, update BRD + BRD-VI + SRD in the same work cycle, append one row to each document's Change Log, and update `CURRENT_BASELINE.md`. Unsourced/inferred statements must be marked `[GUESS]`.

---

## 0. HOW TO READ THIS DOCUMENT

### 0.1. What was merged, and why

This consolidates two independent efforts that reached **twelve identical
conclusions from different starting points** — which is the strongest
evidence in the document. Where they differ, the reason is structural:

| Source | Strength | Weakness |
|---|---|---|
| **v2 BRD/SAD** | Strong sourced citations; disciplined `[GUESS]` tagging; more sophisticated hierarchical architecture | Specification only — never executed |
| **Implementation** | 7 self-contradictions found by running code; measured numbers | Weaker citations; flatter architecture |

Four of those seven contradictions were latent in the v2 design. All are
corrected here (§19.2) and each carries a mandatory regression test.

### 0.2. Parameter tagging — unified scheme

The two source documents used different tags for the same idea. Unified here:

| Tag | Meaning | May it change? |
|:---:|---|---|
| **[S]** | **Structural** — fixed by market regulation | Only if the regulation does |
| **[M]** | **Measured** — computed directly from observed data | The measurement itself is not tuned; **thresholds/routing rules that use it can still overfit** and are `[D]` unless independently fixed |
| **[A]** | **Academic** — grounded in research on this specific market | Preserve unless re-tested |
| **[D]** | **Default** — a starting guess. Equivalent to `[GUESS]` in v2 | **Must be calibrated before real capital** |

Every `[D]` in this document is an unvalidated assumption. There are
approximately 40 of them, listed in §20. **For project governance, every newly invented, inferred, unsourced or not-yet-verified statement must also carry the literal marker `[GUESS]`, even when it is already classified as `[D]`.**

### 0.3. Core strategy hypothesis v1 — not a universal law

> **Trend Pullback hypothesis:** medium-term relative strength can select *which* securities deserve attention, while short-term weakness can help time an entry.

This is retained as **Strategy Family #1**, not as a rule that every setup must pass. v3.1 separates three families: **Trend Pullback**, **Momentum Continuation**, and **Structural Reversal / Mean Reversion**. Each family has its own admissible short-horizon relative-strength condition and must earn promotion independently in walk-forward testing (§4).

---

## TABLE OF CONTENTS

| § | Section |
|---|---|
| [1](#1-product-definition) | Product definition |
| [2](#2-market-context) | Market context |
| [3](#3-verified-market-parameters) | Verified market parameters |
| [4](#4-the-unifying-principle) | The unifying principle |
| [5](#5-hierarchical-model-and-its-hard-constraint) | Hierarchical model and its hard constraint |
| [6](#6-market-regime-layer) | Market regime layer |
| [7](#7-sector-layer) | Sector layer |
| [8](#8-archetype-layer) | Archetype layer |
| [9](#9-signal-pipeline) | Signal pipeline |
| [10](#10-setup-catalog) | Setup catalog |
| [11](#11-pricing-stops-and-sizing) | Pricing, stops and sizing |
| [12](#12-scoring-and-confidence) | Scoring and confidence |
| [13](#13-forecasting) | Forecasting |
| [14](#14-execution-timing) | Execution timing |
| [15](#15-exit-rules) | Exit rules |
| [16](#16-risk-and-portfolio-constraints) | Risk and portfolio constraints |
| [17](#17-data-quality-as-a-business-gate) | Data quality as a business gate |
| [18](#18-manipulation-risk-proxy) | Manipulation risk proxy |
| [19](#19-traps-register) | Traps register |
| [20](#20-parameter-registry) | Parameter registry |
| [21](#21-realistic-expectations) | Realistic expectations |
| [22](#22-compliance) | Compliance |
| [23](#23-definition-of-done) | Definition of done |
| [24](#24-v33-research--assessment-correction-register) | v3.3 research & assessment correction register |
| [25](#25-multi-source-data-governance) | Multi-source data governance |
| [26](#26-research--assessment-document-synchronization-policy) | Research/assessment document synchronization policy |
| [27](#27-v33-ssi-free-provider-decision) | v3.3 SSI-free provider decision |
| [28](#28-v34-auto-refresh-on-run-data-acquisition) | v3.4 auto-refresh-on-run data acquisition |
| [29](#29-v35-dnse-first-multi-source-runtime-module) | v3.5 DNSE-first multi-source runtime module |

---

# 1. PRODUCT DEFINITION

## 1.1. What this is

A **decision-support system** that, on every application start/run, first executes a provider freshness/completeness check, incrementally refreshes admitted-source data when required, then scans the latest usable VN100 dataset. The analytical decision cycle remains EOD-first. It scores every eligible security and produces at most three order tickets with
entry zone, invalidation, targets and position size, and reports forecasts as
distributions rather than predictions — for one person trading their own
capital, who places the orders themselves the following morning.

The correct goal is not an "AI that knows tomorrow's price". It is a system
that knows **when evidence is strong enough to act, at what price, where it
is wrong, how much risk it carries, and when it must admit it does not know.**

## 1.2. Personas [D]

| Persona | Horizon | Primary needs |
|---|---|---|
| Swing trader | 5–20 sessions | Entry zone, invalidation, R multiple, catalyst risk |
| Position investor | 1–6 months | Valuation, earnings, sector regime, weekly structure |
| Research user | n/a | Full-basket scan, feature inspection, backtest, weight experimentation |

Not designed for HFT: free data and a Streamlit front end cannot meet those
latency requirements.

## 1.3. Non-goals, each for a specific reason

| Not this | Because |
|---|---|
| A service for other people | Publishing buy/sell recommendations without a licence may constitute unlicensed securities business activity |
| Automated order placement | Keeps a human between model and market, on a market prone to gaps and manipulation |
| Intraday/day-trading product | The system is EOD-first, has no T+0 resale assumption, and is deliberately optimized for swing/position decisions rather than intraday latency |
| Naked short selling | `SELL` means **reduce or exit a long**. MSCI's June 2026 accessibility review still marks stock lending and short selling as needing improvement |
| Point price prediction | Not forecastable; §13 specifies what replaces it |
| Whole-market scanning | The illiquid tail fails the system's own liquidity gate |

---

# 2. MARKET CONTEXT

## 2.1. Why history matters here, and why it also misleads

Vietnam's centralised market began with the Ho Chi Minh City trading centre
in July 2000; Hanoi followed in 2005; derivatives launched August 2017. That
is a short history containing many **structural breaks** in law,
infrastructure, investor composition, products and liquidity.

*Sources: HNX, SSC.*

**Consequence [D]:** long-history backtests cannot treat 2005 and 2026 as
draws from the same distribution. Regime segmentation is mandatory, not
optional.

## 2.2. Cycle map

| Period | What happened | Quantitative implication |
|---|---|---|
| 2000–2005 | Market formation, HCMC then Hanoi | [D] Not usable as a modern distribution — liquidity, universe size and mechanics differ too much |
| 2006–2008 | World Bank described late 2007/early 2008 as overheating after very large inflows | [D] Momentum plus liquidity can extend a valuation regime far longer than it "should" |
| 2009–2016 | Law and infrastructure deepen | [D] Cross-sectional models become more meaningful as breadth grows |
| 2017–2019 | Derivatives launch; VN-Index passes the 2007 peak April 2018, then falls ~27% from ~1,211 to ~888 by late October | [D] Global risk, USD/rates and derivatives positioning belong in the regime model |
| 2020–2021 | VN-Index passes 1,500 for the first time November 2021, up ~36% YTD, led by banks and real estate | [D] Textbook liquidity/herding regime |
| 2022–2023 | Real-estate and corporate-bond stress; a major bank fraud required unprecedented liquidity support | [D] Bank and property prices must be coupled with credit, bond and governance factors — technical analysis alone is insufficient |
| 2024–2025 | Non-prefunding reform; KRX live 2025-05-05. VN-Index +~41% in 2025 **while foreign investors sold a record ~USD 5.1bn** | [D] Price and foreign flow can diverge for a long time. Foreign net buying is **not** a precondition for a bull market |
| 2026–2027 | FTSE Secondary Emerging implementation begins 2026-09-21 in four tranches; MSCI continues to monitor | [D] This is an "index-event regime": rebalance, crowding and foreign room become features in their own right |

*Sources: HNX, SSC, World Bank, Reuters, VietnamPlus, Investing.com.*

## 2.3. FTSE is not MSCI, and neither means "solved"

FTSE Russell confirmed reclassification begins **Monday 2026-09-21**, phased
in four tranches: **10% (Sep 2026), 20% (Mar 2027), 35% (Jun 2027), 35% (Sep
2027)** — cumulative inclusion 10%, 30%, 65%, 100%.

MSCI's June 2026 accessibility review still marks `-` for foreign ownership
limit, foreign room, equal rights, FX liberalisation, clearing and
settlement, information flow, stock lending and short selling.

> **FTSE Emerging ≠ "every bottleneck resolved" ≠ MSCI Emerging.**

*Sources: LSEG/FTSE Russell FAQ and March 2026 review; MSCI Global Market
Accessibility Review June 2026.*

**Two consequences:**

1. **Upgrade ≠ a wall of money on one day.** The first tranche is 10%. Any
   design that assumes a single large inflow event is wrong.
2. **Accessibility friction persists.** The long/cash-only design (§1.3)
   follows from the market's actual constraints, not from conservatism.

## 2.4. What VN100 actually is

VN100 is **not** the 100 largest stocks by market capitalisation. HOSE
defines it as a capitalisation index combining **VN30 + VNMidcap**, totalling
100 constituents, screened on eligibility, free float and liquidity, using
free-float-adjusted market capitalisation, reviewed periodically.

*Source: HOSE HOSE-Index factsheet and index rulebook.*

**[D] Requirement:** membership must be stored effective-dated, never
hardcoded:

```
index_code | symbol | effective_from | effective_to | review_source
```

Taking today's basket and backtesting from 2015 produces immediate
survivorship bias.

## 2.5. Investor base

VSDC snapshots through 2026 show trading accounts rising from roughly 12.9
million in April to about 13.66 million by August. These are **accounts, not
unique individuals**, and must not be reported as such.

*Source: VSDC.*

---

# 3. VERIFIED MARKET PARAMETERS

## 3.1. Settlement and trading rules [S]

| Parameter | v3.3 value | Note |
|---|---|---|
| Equity settlement | **Trade date + 2 trading sessions; allocation by ~13:00 on T+2** | Securities bought on trade date T are sellable in the **afternoon of T+2** once allocated. This is the regulatory sellability boundary. |
| EOD strategy policy | **Separate from settlement** | An EOD strategy may choose to evaluate after the T+2 close and execute next morning; that delay is an **execution policy**, not a legal settlement lock. |
| Intraday T+0 resale | Not assumed | No same-day resale logic in this application. |
| Short selling | Not assumed for retail cash equity | `SELL` remains reduce/exit long; no naked-short path. |
| Price band — HOSE | ±7% | Ordinary-session baseline; exceptional/special cases must be venue-rule versioned. |
| Price band — HNX | ±10% | Same caveat. |
| Price band — UPCOM | ±15% | Same caveat. |
| Lot size | 100 shares | Venue/security metadata should still be checked from provider/reference data. |
| Tick — HOSE | 10 / 50 / 100 VND | `<10k / 10k–<50k / ≥50k`. Decimal-safe rounding is mandatory. |
| Auction/LO priority | **Do not encode “LO always preferred”** | KRX matching priority is session/order-specific. Execution simulation must not infer guaranteed fills from a simplified priority slogan. |

### Settlement versus tail-stress — corrected terminology

For a buy filled at/near the open, three daily price-band moves can occur before/through the settlement-day afternoon. Therefore the stress quantity

```text
1 − (1 − 0.07)^3 ≈ 19.56%
```

may be retained as a **three-limit-move pre-settlement stress scenario**, but it is **not** “three full sessions in which sale is legally impossible” and it is **not an absolute worst case**: a floor lock can continue after settlement when there are no buyers.

## 3.2. Transaction costs — broker-specific, versioned [S/D]

| Component | v3.3 rule | Note |
|---|---|---|
| Brokerage commission | **User/broker-specific; regulatory maximum 0.45%** | Actual online tiers may be far lower. |
| Exchange trading-service fee — listed stocks | **0.027% of trading value** | Current Ministry of Finance schedule (Decision 1541/QĐ-BTC). |
| Sale tax for individual equity transfer | **0.10% of sale proceeds** | Model by effective date. |
| Cash dividend tax | 5% where applicable | Corporate-action/tax module, not per-trade execution fee. |
| Margin interest | Broker-specific | Not used unless margin mode is explicitly enabled. |

**Critical anti-double-count rule:** a broker's quoted commission may already include the amount the broker pays to the exchange. The cost engine therefore requires:

```yaml
commission_rate: 0.0015
commission_includes_exchange_fee: true
exchange_fee_rate: 0.00027
sell_tax_rate: 0.001
```

If `commission_includes_exchange_fee=true`, the exchange fee is **not added again**. No generic “0.46% round trip” is trusted until the user's actual tariff is configured.

## 3.3. Current market conditions [D] — calibration context, not forecast

| Observation | Value | Design implication |
|---|---|---|
| Index P/E | ~12.5x vs ~15.3x ten-year mean | Valuation not stretched |
| Margin debt | Record, above VND 446tn | System-level fragility; reinforces the anomaly gate |
| Average daily value, August 2026 | **VND 18.7tn vs 26.9tn YTD** | Liquidity contracting |
| Turnover by cap tier, August 2026 | **Flat across large, mid and small while prices rose** | Directly motivated the turnover-confirmation rule (§6.3) |
| First FTSE tranche | ~USD 212m ≈ 58% of one day's trading in the affected names | Not a large cash injection |
| Brent, early September 2026 | Near USD 99 amid Middle East tension | Energy and inflation channel active |

---

# 4. STRATEGY HYPOTHESES — SEPARATED, TESTABLE, NON-UNIVERSAL

## 4.1. Why v3.1 changes the v3.0 framing

Vietnam research supports momentum in some samples/horizons, while evidence on short-term reversal is not uniform across every period, venue or method. Therefore v3.1 does **not** hard-code one dual-RS condition across every setup. The three-benchmark relative-strength framework remains mandatory as context, but each strategy family decides how it uses short-horizon strength.

## 4.2. Common relative-strength measurements

```text
rs_long_market  = R_stock,126 − R_market,126
rs_long_sector  = R_stock,126 − R_sector,126
rs_short_market = R_stock,20  − R_market,20
rs_short_sector = R_stock,20  − R_sector,20
sector_rs_market = R_sector − R_market
```

All ranks are point-in-time cross-sectional ranks. The 126/20 windows are `[A]/[D]` research baselines and must be re-tested on the actual dataset.

## 4.3. Strategy Family #1 — Trend Pullback [D]

```text
Long-horizon RS: strong / above threshold
Short-horizon RS: temporarily weak or neutral
Trend: established
Entry: pullback / retest / controlled contraction
```

This is the direct successor to the v3.0 “momentum selects which, reversal selects when” idea.

## 4.4. Strategy Family #2 — Momentum Continuation [D]

```text
Long-horizon RS: strong
Short-horizon RS: strong
Regime: STRONG_BULL only
Archetype: high-beta / momentum-permitted only
Volume: expansion required
```

This family buys strength, so execution/gap constraints are stricter.

## 4.5. Strategy Family #3 — Structural Reversal / Mean Reversion [D]

```text
Long-horizon RS: optional context, NOT a universal hard gate
Short-horizon RS: weak / extreme
Structure: confirmed reversal evidence (e.g. spring, sweep-reclaim, support reversal)
Regime: not PANIC_BEAR; stricter size/gating in RISK_OFF
```

This prevents a 126-session leadership requirement from mechanically deleting early-cycle reversal candidates before the backtest has established whether that filter helps.

## 4.6. Three benchmarks remain mandatory

```text
RS(stock / market)  = R_stock − R_market
RS(stock / sector)  = R_stock − R_sector
RS(sector / market) = R_sector − R_market
```

They are context and ranking features. A single market benchmark cannot distinguish a strong stock in a weak sector from a sector leader in a broad advance.

---

# 5. HIERARCHICAL MODEL AND ITS HARD CONSTRAINT

## 5.1. Core business decision

**A single fixed weight vector must not be applied across the whole VN100.**
The same technical feature can be computed identically for every security,
but its **meaning, threshold and weight** must vary by market state, sector,
archetype and liquidity.

```
MARKET
  ↓ MARKET REGIME
  ↓ SECTOR / INDUSTRY
  ↓ STOCK ARCHETYPE
  ↓ INDIVIDUAL EVIDENCE
  ↓ LIQUIDITY / RISK / DATA-QUALITY GATES
  ↓ SETUP → ENTRY ZONE → TRIGGER → INVALIDATION → TARGETS
```

replacing the naive:

```
RSI + MACD + SMC + one fixed weight vector → BUY / SELL
```

## 5.2. The constraint that limits how far this can go ⭐

The hierarchy above is correct as **routing logic** and impossible as
**fitting logic**. The arithmetic:

```
Signals available:  ~40/year × 15 years of usable history = ~600 total
Minimum for publishing a hit rate: 30 per cell
```

| Partitioning | Theoretical cells | Populated | Signals/cell | Viable? |
|---|---:|---:|---:|:---:|
| Regime × Sector × Archetype | 225 | ~68 | **8.8** | ❌ |
| Regime × Sector | 45 | ~25 | 24.0 | ❌ |
| Regime × Archetype | 25 | ~20 | 30.0 | ⚠️ marginal |
| **Regime only** | 5 | 5 | **120.0** | ✅ |
| Global | 1 | 1 | 600.0 | ✅ |

At ~9 signals per cell, the standard error of a hit rate is about 16
percentage points — a cell reporting "60%" has a 95% interval roughly from
28% to 92%. Weights fitted on that are fitted to noise, and a Deflated Sharpe
correction across 225 variants would collapse to near zero.

**The paradox:** the hierarchical design is more sophisticated *and* less
estimable than a flat one. The sophistication is real; the data to validate
it does not exist.

## 5.3. Resolution — separate routing from fitting

```
ROUTING and GATING   deterministic, no parameters to fit  → USE FULL HIERARCHY
    banks → P/B-ROE valuation, not EV/EBITDA
    high-beta → trade only in STRONG_BULL
    low liquidity → cap weight

WEIGHT FITTING       needs ≥30 signals per cell           → REGIME LEVEL ONLY
```

| Layer | Purpose | Fits parameters? |
|---|---|:---:|
| Market regime | Gate, size multiplier, **weight fitting** | ✅ 5 cells, sufficient data |
| Sector | Route valuation strategy, compute sector RS | ❌ routing only |
| Archetype | Gate permitted setups, risk thresholds, weight caps | ❌ gating only |
| Security | Tighten parameters using measured facts | ❌ measured, not optimised |

If sector- or archetype-level weights are still wanted, apply **heavy
shrinkage toward the global vector**:

```
w_cell = (1 − λ)·w_global + λ·w_cell_fitted        λ ≈ 0.2–0.3   [D]
```

Published work on forecast combination consistently finds equal weighting and
shrinkage hard to beat when weight estimates are noisy.

## 5.4. Model versioning requirement

The fixed-weight baseline is retained as `model_version = mvp_fixed_v1` for
pipeline testing and as a benchmark. It is **not** the production target. New
code must never branch on `if symbol == "..."`; routing is metadata- and
config-driven.

---

# 6. MARKET REGIME LAYER

## 6.1. Five business regimes [D]

| Regime | Description | Preferred model behaviour |
|---|---|---|
| **Strong Bull** | Index, breadth, leadership and liquidity all strong | Trend, momentum, relative-strength setups |
| **Concentrated / Weak Bull** | Index rising but breadth or leadership narrow | Reduce confidence; favour genuine leaders; do not extrapolate the index |
| **Range / Neutral** | Low directional efficiency, many failed breakouts | Structure and mean-reversion; reduce trend weight |
| **Distribution / Risk-off** | Breadth weakening, leadership fading | Capital preservation; only confirmed reversals |
| **Panic / Bear** | Volatility and liquidity stress; gap and limit risk elevated | Hard risk gate; **do not force the model to find a BUY** |

`MarketGate` is a multiplier in `[0, 1]`, not a binary — it scales
actionability rather than switching it off abruptly, except at the bottom
state (§6.4).

## 6.2. Dual-index scoring

```
For VN-Index and for a self-computed EQUAL-WEIGHT VN100 index:
    score = 1[C>MA50] + 1[C>MA200] + 1[MA50>MA200]      ∈ {0,1,2,3}

s = MIN(score_cap_weighted, score_equal_weighted)
```

Taking the minimum is not generic caution. A capitalisation index can be
carried by two or three mega-caps while the median security falls; the
equal-weight series is immune. When they disagree, the equal-weight reading
describes the market a stock-picker actually faces.

Additional regime inputs: percentage of VN100 above MA20/50/200,
advance/decline breadth, realised volatility regime, turnover z-score,
top-N index contribution concentration, sector participation.

> **A single condition such as "VN-Index above its MA200" must never be used
> alone to determine regime.**

## 6.3. Turnover confirmation ⭐ added from observation

```
turnover_ratio = session turnover / its own 20-session mean

STRONG_BULL requires turnover_ratio ≥ 1.00        [D]
BULL        requires turnover_ratio ≥ 0.85        [D]
Missing turnover data is NEUTRAL, never confirmation.
```

**Why.** In August 2026 prices rose across large, mid and small caps
simultaneously while average daily value fell to VND 18.7tn against a 26.9tn
year-to-date average, and turnover in all three tiers was essentially flat.
That is re-rating on expectation, not new money — and a regime rule built
only on moving averages and breadth reads it as strength. Volume is the check
that separates the two.

## 6.4. The absolute rule

| Regime | Archetypes permitted | Size multiplier [D] |
|---|---|:---:|
| Strong Bull | all | 1.00 |
| Concentrated Bull | large-cap, defensive, cyclical | 0.85 |
| Range | large-cap, defensive | 0.65 |
| Distribution / Risk-off | **defensive only** | 0.40 |
| Panic / Bear | **none — zero new signals** | 0.00 |

**Panic/Bear produces exactly zero signals, not fewer signals.** Herding on
this market is documented to intensify in falling markets, and several of the
system's own setups buy weakness. A test must fail if a single signal escapes.

---

# 7. SECTOR LAYER

## 7.1. Sector leadership score [D]

Rotation is computed, not narrated:

```
S_sector = w₁·RS₂₀ + w₂·RS₆₀ + w₃·Breadth + w₄·VolumeImpulse
         + w₅·EarningsRevision + w₆·ValuationZ + w₇·ForeignFlow
```

All weights are `[D]` bootstrap values, to be optimised on a rolling training
window — subject to the fitting constraint in §5.2 (sector-level weights need
shrinkage toward global).

Leadership rotates fast: HOSE sector performance in June 2026 showed
financials, real estate and industrials up while energy, healthcare and
materials fell; by August, IT, discretionary consumer and real estate led.

*Source: SSC monthly reports.*

## 7.2. Taxonomy, versioned

```
Financials → Banks | Securities | Insurance
Real Estate → Residential | Industrial Parks | Commercial
Industrials → Construction | Infrastructure | Logistics/Ports | Services
Materials → Steel | Chemicals | Construction Materials
Consumer → Retail | Food & Beverage | Consumer Services
Technology · Energy (Oil & Gas | Services) · Utilities · Healthcare
```

**Requirement:** taxonomy must store `effective_from` / `effective_to`. Using
today's sector map for a 2015 backtest leaks future information — sector
classification itself changes over time.

## 7.3. Valuation routes by sector

A single ratio is insufficient. Valuation produces a **fair-value band and a
quality gate**, never a BUY on its own.

| Sector | Primary model | Quality / risk variables |
|---|---|---|
| Bank | P/B–ROE, residual income | ROE, NIM, NPL, provision coverage, CASA, credit growth, capital |
| Securities | P/B + normalised P/E | Margin book, brokerage share, prop trading, leverage, dilution |
| Real estate | RNAV / SOTP | Presales, legal progress, net debt, bond maturity, cash conversion |
| Construction / infra | EV/EBITDA, P/E, DCF | Backlog, receivables, working capital, ROIC |
| Retail / consumer | Forward P/E, PEG | Same-store sales, margin, inventory, consumer credit |
| Technology | Growth-adjusted P/E, FCF | Recurring revenue, backlog, export mix, ROIC |
| Utilities | DCF, EV/EBITDA | Tariff/PPA, capex, debt, hydrology/fuel |
| Steel / materials | Normalised EV/EBITDA | Utilisation, spreads, inventory, global cycle |
| Oil & gas | Mid-cycle EV/EBITDA, DCF | Oil/gas price, crack spread, project pipeline |
| Logistics / ports | EV/EBITDA, DCF | Throughput, capacity, tariff, capex |

```
Fundamental = Attractive          Fundamental = Attractive
Trend       = Bear                Regime      = Bull
Structure   = No reversal         Structure   = BOS confirmed + retest held
⇒ WATCH, not BUY                  ⇒ BUY setup
```

Every important industry needs an explicit strategy or an explicitly flagged
generic fallback.

---

# 8. ARCHETYPE LAYER

## 8.1. Sector alone is insufficient

Within one sector, behaviour differs sharply by capitalisation, beta, free
float, liquidity and business maturity.

| Archetype | Character | Features and weights needing attention |
|---|---|---|
| **Large-cap / index leader** | High liquidity, index impact, institutional flow matters | Trend, RS, breadth, foreign/institutional flow. ⚠️ These securities *are* the cap index — use the equal-weight benchmark for their RS |
| **High-beta cyclical** | High volatility, liquidity- and cycle-sensitive | Momentum, volume impulse, sector cycle, ATR-normalised structure. **Only archetype permitted momentum logic**, and only in Strong Bull |
| **Defensive / stable** | Low volatility, steadier cash flow | Quality, valuation, dividend/FCF; lower momentum weight. Tightest stop **and** largest weight (§11.5) |
| **Event-driven / asset play** | Legal, project, M&A or capital-action catalysts | Event risk, RNAV/SOTP, disclosure timing, technical trigger |
| **Low-float / speculative** | Higher false-breakout, execution and manipulation-proxy risk | Liquidity penalty, free-float checks, non-fill and gap stress |

**A security may carry multiple archetype tags.** The system must not force
each into exactly one label.

## 8.2. Archetype assignment is measured, not asserted [M]

Assignment is driven by computed statistics, refreshed quarterly:

```
variance_ratio_5 · hurst · annualised volatility · ATR% · downside ATR ratio
· beta · idiosyncratic share · ADV · Amihud illiquidity · overnight gap p90
· limit-hit frequency · longest consecutive limit-down streak
· free float · foreign-flow sensitivity
```

Because these are **measured rather than optimised**, this layer cannot
overfit. The tuned parameters live downstream at regime level, where each
bucket holds enough observations.

## 8.3. Exclusion gates — untradeable for this style [D]

```
ADV_20 < 20bn VND               → EXCLUDED   cannot size a position
longest limit-down streak ≥ 5   → EXCLUDED   unacceptable tail risk when locked
overnight gap p90 > 4.5%        → EXCLUDED   unusable for EOD entry
```

## 8.4. The classification bug to avoid ⭐

A statistical fallback must **never** route into a sector-defined group.
Assigning a brokerage to the commodity archetype applies a commodity-price
gate that has no counterpart for that security, and its signals can never
fire. The fallback may reach only statistically defined archetypes, and must
not grant privileges the security has not demonstrated:

```
VR > 1.15 AND ADV ≥ 100bn AND vol < 38%  → large-cap trend treatment
VR < 0.85 AND vol < 33%                  → defensive treatment
otherwise                                → most conservative archetype
```

*(Found by running code — see §19.2, error 7.)*

---

# 9. SIGNAL PIPELINE

Sequential gates. Failing any gate is a hard rejection **with a recorded
reason** — that log is what makes the system's silence explainable rather
than indistinguishable from a bug.

```
GATE 0  MARKET REGIME
        Panic/Bear → abort the run, emit nothing

GATE 1  UNIVERSE ELIGIBILITY
        in point-in-time VN100 · ≥280 sessions · ADV ≥ 20bn
        · not exchange-flagged · archetype ≠ EXCLUDED

GATE 2  RISK PROXIES
        manipulation_risk_proxy < archetype threshold
        data_quality ≥ threshold (§17)

GATE 3  ARCHETYPE × REGIME
        regime rank ≥ archetype minimum
        AND exogenous condition satisfied
            (commodity price above trend for cyclicals;
             market turnover above MA20 for high-beta;
             sector index above MA50 for banks)

GATE 4a DUAL CONDITION                                       ← the core
        rs_long_rank ≥ 60
        AND (rs_short_rank ≤ 40  if logic ≠ momentum
             rs_short_rank ≥ 65  if logic = momentum)

GATE 4b SETUP
        ≥1 setup from the archetype's permitted list fires
        AND volume condition appropriate TO THAT SETUP'S DIRECTION (§10.9)

GATE 5  SCORE AND GEOMETRY
        technical_score ≥ 60
        AND win_probability ≥ 0.55        (skipped when sample < 30)
        AND R / ATR₁₄ ≥ 0.8
        AND risk_reward ≥ 1.7             (after any target trim)
        AND sizing_stop < exit_stop < entry
        AND entry < ceiling × 0.995

GATE 6  PORTFOLIO CONSTRAINTS
        not held · positions < 10 · sector ≤ 35% · owner group ≤ cap
        · max 2 in any highly-correlated archetype · max 1 speculative
        · total open risk ≤ 5% NAV · cash sufficient · notional ≥ 10m VND

SELECTION
        composite = 0.6·(score/100) + 0.4·win_probability
        max 2 per archetype and 2 per sector per day
        take top N, N = min(3, free slots)
```

More than three signals a day is a symptom of thresholds that are too loose,
not a productive day.

---

# 10. SETUP CATALOG

## 10.1. Setup families

| Family | Members | Volume must |
|---|---|:---:|
| Pullback | `PB_MA20`, `PB_MA50` | **FALL** |
| Reversal | `REV_SUP`, `BB_LOWER`, Wyckoff spring | rise / n.a. |
| Trend | `TREND_MA`, `RS_LEADER` | rise |
| Momentum | `MOM_20` (high-beta only) | rise |
| Contraction | `VCP` | rise on expansion |
| Structure | Breakout–retest, BOS + successful retest | rise |

## 10.2. `PB_MA20` — pullback to the 20-day average (primary)

```
TREND      MA20 > MA50 > MA200 · slope(MA50,10) > 0 · C > MA200 × 1.02
PULLBACK   −4% ≤ dist_MA20 ≤ +2% · min(L, last 5) ≤ MA20 × 1.005
           · RSI₁₄ < archetype threshold
QUALITY    mean(V,5) < mean(V,20) × 1.10     ← volume must FALL
           · max(C, last 20)/C − 1 ≤ 15%
TRIGGER    C > O and C > C₋₁  OR  (C−L)/(H−L) > 0.60  OR  C > max(H₋₁, H₋₂)
```

The volume condition separates a healthy pause from distribution. It is also
why this setup must be exempt from any general volume floor (§10.9).

## 10.3. Wyckoff, operationalised

Wyckoff is a price–volume–range framework, but "is this Phase C or D" has no
objective ground truth. Machine-usable definitions [D]:

```
Trading range:  rolling confirmed support/resistance
                + falling directional efficiency
                + compressed realised volatility

Spring:         low < established range_low
                AND close > range_low
                AND subsequent bars do not accept below range

Upthrust:       high > range_high
                AND close < range_high
                AND subsequent bars fail to accept above

Sign of strength:  close > range_high + positive relative volume
                   + widening spread + follow-through
```

Use **volume z-score**, not a fixed absolute multiplier. Do not attempt full
schematic recognition from images in the MVP; convert each concept into a
measurable feature and test incremental alpha.

## 10.4. Market structure (SMC), operationalised

```
Swing high:      local maximum with L bars left and R bars right;
                 CONFIRMED ONLY AFTER R BARS
Bullish BOS:     close above the most recent confirmed swing high
Liquidity sweep: low breaks structure low AND close returns above it
Bullish FVG:     low[t] > high[t−2]
Order block:     last opposite candle before an impulsive BOS,
                 retained only if displacement and reaction clear thresholds
```

⚠️ **Delayed pivot confirmation is mandatory.** Marking a swing high on the
bar that formed it, when three future bars were needed to know it was a high,
is look-ahead bias.

Displacement must be volatility-normalised, not a fixed percentage:

```
Displacement = |C_t − C_{t−1}| / ATR₁₄
```

## 10.5. Elliott Wave — hypothesis generator only [D]

```
OHLC → volatility-normalised ZigZag → pivot graph
     → enumerate 5-wave / ABC candidates
     → Fibonacci + non-overlap constraints
     → score candidate consistency → RETAIN MULTIPLE HYPOTHESES
```

Output a candidate structure with a consistency score explicitly labelled
**not a calibrated probability**, plus alternate counts and an invalidation
level. Never "this is certainly Wave 3". **Elliott must never override risk
management.**

## 10.6. Volume Profile — proxy, clearly labelled

With daily OHLCV, the price at which trades actually occurred within a bar is
unknown. The MVP allocates volume to typical-price bins and must label the
result `EOD Volume Profile proxy` [D]. It must not be called true
volume-at-price. `VPScore` should be multiplied by a liquidity-confidence
factor.

## 10.7. Excluded by design

`GAP_GO` and every intraday-triggered pattern are absent. They require acting
within the session the pattern appears, which end-of-day execution cannot do
(§14.4).

## 10.8. Applicability matrix

| Method | Cross-sector? | Mandatory adjustment |
|---|:---:|---|
| EMA / MACD / RSI | Yes, formula-wise | Regime, volatility, archetype-specific thresholds |
| ATR / realised vol | Yes | Used to normalise other thresholds |
| Relative strength | Yes | Both market and sector benchmarks |
| Wyckoff | Yes as price–volume framework | Volume z-score, liquidity profile, follow-through |
| SMC | Yes if operationalised | Confirmed pivots, ATR-normalised displacement |
| Volume Profile | Limited | Confidence scaled by data granularity |
| Elliott | Limited | Context only; multiple counts retained |
| Fundamental valuation | **No single model** | Sector-specific strategy |

## 10.9. The volume sign-flip rule ⭐

**This is the easiest rule in the document to implement backwards, and doing
so silently disables an entire setup family.**

```
mean-reversion / pullback:  want volume LOW   → clip(2 − volume_z, 0, 1)
trend / momentum:           want volume HIGH  → clip((volume_z − 1)/1.5, 0, 1)
```

The rule must be applied **in both the gate and the scoring formula**. Stating
it correctly in one place and incorrectly in the other is worse than getting
it wrong in both, because the inconsistency hides the error.

*Found by running code — a general volume floor rejected 100% of pullback
signals, the intended primary setup, silently. See §19.2, error 1.*

---

# 11. PRICING, STOPS AND SIZING

## 11.1. Entry is a zone, never a single price

```
1. Never buy on score alone
2. Identify setup_type: pullback / breakout-retest / spring / sweep-reversal
3. Build a ZONE from structure + ATR
4. Require a confirmation trigger
5. Place invalidation OUTSIDE structure
6. Set targets from resistance or R multiples
```

## 11.2. Entry price — never the signal-day close ⭐

Signals are generated after the close of session T; the order can only be
placed, and can only fill, on T+1.

```
LO_raw = close_T × (1 + premium)
entry  = round_DOWN_to_tick(LO_raw)
```

Premium by setup [D], because the setup determines gap exposure:

| Setup family | Premium | Rationale |
|---|:---:|---|
| Pullback, reversal | +0.5% | Buying weakness; no need to chase |
| Trend, RS leader | +1.0% | Timing not critical; prioritise the fill |
| Momentum | +0.8% | Needs the fill but carries gap risk |
| Contraction / breakout | +0.3% | Highest gap risk — prefer no fill to a bad price |

There is an asymmetry behind these numbers. For a **pullback**, a gap up
means the dip has already been bought and the thesis is void — failing to
fill is a *feature*. For a **momentum** setup, a gap up *confirms* the thesis,
so failing to fill costs a winner.

## 11.3. The dual-stop system ⭐ the most important risk rule

Because three sessions cannot be exited, every position carries **two
distinct stops**:

```
EXIT STOP — narrow; the price at which the system tells you to sell
    exit_stop = min( structure_low − 0.5·ATR₁₄ ,
                     entry × (1 − max_stop_pct) )

SIZING STOP — wide; used ONLY to compute quantity, never to exit
    atr_eff     = max( ATR₁₄ , 1.3 × downside_ATR₁₄ )
    sizing_stop = min( entry − atr_mult · atr_eff ,
                       entry × (1 − max_stop_pct × 1.25) )

INVARIANT (tested):  0 < sizing_stop < exit_stop < entry
```

**Why two.** Settlement and execution policy are now separated. A buy is regulatorily sellable in the afternoon of its trade-date T+2 once allocated; however, a conservative EOD policy may not generate an executable exit until the following session. The sizing stop is therefore a **tail-stress sizing device**, not a claim that the exit stop is legally unusable for three full sessions.

```text
three-limit-move pre-settlement stress (HOSE) = 1 − (1 − 0.07)^3 ≈ 19.56%
```

This stress is not an absolute worst case: a security can remain pinned at floor with no executable liquidity after settlement. Position size must therefore also be capped by liquidity/free-float and floor-lock history.

`downside_ATR` is the ATR computed only over sessions that closed lower.
Negative shocks on this market produce larger volatility than positive shocks
of equal magnitude, so symmetric ATR understates the risk that matters here.

## 11.4. Targets, and the resistance rule

```
R        = entry − exit_stop
target_1 = entry + 2.0·R    [D]   sell half
target_2 = entry + 3.5·R    [D]   remainder or trail

OVERHEAD CHECK — only when the trend is NOT confirmed:
    ceiling = 52-week high        (a level with genuine memory)
    if ceiling < entry × 1.03:            REJECT — no headroom
    if entry < ceiling < target_1:        target_1 = ceiling × 0.99

risk_reward = (target_1 − entry) / R
REQUIRE risk_reward ≥ 1.7     [D]
```

> **`MIN_RISK_REWARD` must be strictly less than the `target_1` multiple.**
> If they are equal the gate is vacuous when the target is untouched (the
> ratio equals the multiple by construction) and impossible the moment
> anything trims the target. The gap is the required slack.
> *(Found by running code — §19.2, error 2.)*

A short-horizon high is **not** resistance for a security in a confirmed
uptrend: it exceeds that level routinely, and a dip inside an uptrend sits
below its own recent high by construction.

## 11.5. Position sizing

```
1  RISK BUDGET
   budget = NAV × risk_per_trade × regime_multiplier × seasonal_multiplier

2  RAW QUANTITY — from the SIZING stop
   qty_raw = budget / (entry − sizing_stop)

3  PER-SECURITY TIGHTENING — only ever tightens        [M]
   if beta > 1.2:                  ×= 1.2 / beta
   if limit-down streak ≥ 3:       ×= 0.60
   if free float < 20%:            ×= 0.50

4  FOUR CEILINGS — take the minimum
   weight cap · 3% of ADV · available cash · remaining owner-group budget

5  ROUND DOWN to a 100-share lot

6  MINIMUM VIABLE
   if notional < 10m VND: REJECT — costs would consume the edge
```

**Signal strength must be separated from position size.** A score of 82 with
extreme volatility, low liquidity and earnings tomorrow is a strong signal
*and* no immediate position.

### Two settings that look wrong and are correct

**Defensives carry the tightest stop and the largest weight.** Low volatility
means a 7% stop still sits outside the daily noise band, so the same risk
budget buys more shares. Defensives are the intended **backbone** of an
end-of-day portfolio, not a garnish — most retail investors do the opposite.

**Speculative low-float names carry the widest stop and the smallest weight.**
The arithmetic says: accept a very small position, or do not trade them.

---

# 12. SCORING AND CONFIDENCE

## 12.1. Composite structure

```
EvidenceScore = w_s·SectorScore + w_a·ArchetypeScore
              + w_i·IndividualScore + w_f·FundamentalScore

ActionableScore = EvidenceScore × MarketGate × LiquidityGate × DataQualityGate
```

The baseline `0.35·Trend + 0.25·Momentum + 0.15·VolumeFlow + 0.20·Structure +
0.05·VolumeProfile` is retained as `mvp_fixed_v1` for pipeline testing and
benchmarking only. All weights are `[D]`.

## 12.2. Individual technical score components [D]

```
25%  setup quality        tightness, candle quality, additional setups
20%  volume confirmation  SIGN FLIPS BY LOGIC (§10.9)
20%  relative strength    0.6·long_strength + 0.4·short_state
15%  trend context        MA alignment, slope, distance above MA200, ADX
10%  sector strength      sector RS rank
10%  flow confirmation    foreign net, order imbalance
−    risk penalty         manipulation proxy, gap history, limit streak,
                          distance from MA20, nearby resistance
```

Seasonal adjustment [A]: pre-Tet window ×1.05; January ×1.03; **post-Tet
×1.00 — no bonus**, because the documented pre-holiday effect does not extend
past the holiday.

## 12.3. Confidence is not probability

`confidence` reflects evidence completeness, consistency and data quality. It
**must not** be called a win probability until calibrated out of sample.

## 12.4. Win probability, and when to publish none

```
Phase 1  Empirical hit rate for the exact (setup, archetype) pair,
         published ONLY if the sample reaches 30 trades.

Phase 2  Calibrated model:
         labelling    triple barrier (upper 2R, lower exit_stop, time hold_max)
                      MUST simulate entry at T+1
                      MUST enforce T+2 regulatory sellability and the chosen EOD execution-policy delay
         model        deliberately simple — logistic before boosting
         validation   purged forward-chaining CV with embargo
         calibration  isotonic or sigmoid, so 0.58 means roughly 58%
         gate         p ≥ 0.55
```

> **A 75% hit rate from three wins in four trades is noise dressed as data.**
> Below the sample threshold, publish nothing and leave the gate inert.

`30 trades` is only a **minimum publication floor [D]**, not proof of statistical reliability. Trades clustered in the same dates, sector or regime are correlated; confidence intervals and bootstraps must therefore cluster/block by trading date (and report regime/sector concentration) rather than treating every stock-trade row as independent.

## 12.5. Output contract

```json
{
  "symbol": "ABC", "as_of": "...", "universe_version": "...",
  "sector": "financials", "industry": "banking",
  "archetypes": ["large_cap", "liquid"],
  "market_regime": "STRONG_BULL|CONCENTRATED_BULL|RANGE|RISK_OFF|PANIC_BEAR",
  "market_score": 0, "sector_score": 0,
  "stock_rs_vs_market": 0, "stock_rs_vs_sector": 0,
  "technical_score": 0, "fundamental_score": 0,
  "liquidity_score": 0, "data_quality": 0,
  "manipulation_risk_proxy": 0,
  "recommendation": "STRONG_BUY|BUY|WATCH|REDUCE|EXIT",
  "actionable_score": 0, "confidence": 0,
  "setup_type": "...", "entry_zone": [0, 0], "trigger": "...",
  "invalidation": 0, "target_1": 0, "target_2": 0,
  "exit_stop": 0, "sizing_stop": 0,
  "weight_pct": 0, "risk_pct_exit": 0,
  "pre_settlement_stress_pct": 0,
  "max_gap_pct": 0,
  "regulatory_sellable_date": "...",
  "policy_earliest_exit_fill_date": "...",
  "holding_horizon": "5-20 bars",
  "rationale": [], "risk_flags": [], "quality_flags": [],
  "model_version": "...", "feature_version": "..."
}
```

Published output must express size as **percentage of NAV**, never currency
amounts or share counts (§22.4).

---

# 13. FORECASTING

Earlier drafts said the system does not forecast. That was imprecise. Three
things are forecastable to very different degrees, and the module reports
them **in order of how much they can be trusted**.

| Component | Forecastability | Method | Honest output |
|---|---|---|---|
| **Volatility** | **Good** — clusters and mean-reverts | GARCH(1,1) by MLE, EWMA fallback | Sigma path, persistence, long-run level |
| **Trend state** | Moderate — states persist | 3-state Markov chain, counted transitions | P(up/side/down) at horizon |
| **Price level** | **Not as a point** | Filtered historical simulation + conditional analogues | A quantile fan |
| **Direction** | **Weak** | Calibrated classifier on purged folds | Probability, **suppressed** below the AUC gate |

## 13.1. Price forecasts are distributions

Two independent methods run in parallel **so they can disagree**:

1. **Filtered historical simulation** — standardise returns by conditional
   volatility, resample, re-inflate by the volatility forecast. Inherits the
   real distribution's fat tails and skew rather than assuming normality.
2. **Conditional analogues** — sample the forward paths that actually
   followed historically similar states. Assumes no distribution at all.

When the two disagree, the disagreement is reported rather than averaged
away. Output is `q05, q25, q50, q75, q95` — the median is the centre of a
range, **not a price target**.

## 13.2. The suppression rule ⭐

```
Directional forecast requires out-of-sample AUC ≥ 0.52.
Below that: NO NUMBER IS SHOWN.
```

Verified: on synthetic random-walk data the model reports AUC ≈ 0.49 and
**suppresses itself**. A probability a user should not act on is worse than
none, because it invites action while carrying no information.

## 13.3. Market-level forecast is a scenario, not a number

```
Index_t = EPS_t × Justified_PE_t

Bear:  low EPS growth + multiple compression
Base:  normalised EPS growth + stable multiple
Bull:  broad earnings acceleration + justified re-rating
```

Assumptions must be user-visible and user-editable, never hidden behind an
"AI target". Sell-side 2026 targets ranged roughly 1,920 to 2,099 depending
on the house — that dispersion is precisely why no single target may be
treated as truth.

---

# 14. EXECUTION TIMING

## 14.1. Lifecycle — settlement and EOD policy are distinct

```text
Signal day S0, after close       Signal generated from close_S0
Entry day E0 = S0+1, morning    Limit order may fill from E0 market data
E0+1                            Position unsettled
E0+2, ~13:00                    Securities allocated; REGULATORILY SELLABLE in afternoon
E0+2, after close               Conservative EOD policy may evaluate exit
E0+3, next session              Earliest fill under that conservative EOD policy
```

Two dates must be persisted:

```text
regulatory_sellable_date
policy_earliest_exit_fill_date
```

Do not collapse them into `locked_sessions=3`.

## 14.2. Limit-order execution policy

The application uses limit orders for entry because it is designed around explicit price geometry. **Do not** justify this with a blanket statement that LO always outranks ATO/ATC under KRX. Matching priority is session/order-specific and must be versioned from venue rules. Daily-bar backtests must also treat a mere touch of a limit as an **uncertain fill**, not a guaranteed one.

## 14.3. The gap gate — an eighth, informal gate

```
gap = reference_or_open_price / close_T − 1
threshold = MIN( archetype default , this security's own gap_p90 )

gap ≤ threshold × 0.5   →  PROCEED at full size
gap ≤ threshold         →  REDUCE to 70%
gap >  threshold        →  CANCEL — R:R void; the stop has not moved
gap < −2.0%             →  REVIEW — check for adverse overnight news
opens locked at ceiling →  CANCEL — no sellers to trade against
```

## 14.4. Why this matters disproportionately

End-of-day execution does not damage all setups equally. It damages **exactly
the ones that look most attractive on a chart**:

| Setup character | Overnight behaviour | Effect on edge |
|---|---|---|
| Breakout with volume surge | Everyone sees it at once → gaps up | Severe: buying 2–5% higher, stop unchanged |
| Gap-and-go | Intraday by nature | Unusable |
| Locked at ceiling | Opens locked | Cannot fill at all |
| Pullback to a moving average | Buying weakness; a gap may **help** | Minimal, sometimes positive |
| Slow trend following | A session early or late barely matters | Negligible |

This is why §10 ranks pullback above breakout and deletes `GAP_GO`.

## 14.5. Parameter adjustments for EOD + T+2 [D]

| Parameter | Naive | **This system** | Reason |
|---|:---:|:---:|---|
| Default stop | 7% | **9–10%** | Must survive three sessions of noise |
| ATR multiplier | 2.0–3.0 | **3.0–4.0** | Same |
| Risk per trade | 0.5–1.0% | **0.4–0.7%** | Compensates pre-settlement stress, gap risk and non-fill risk |
| Target hold | 3–15 sessions | **8–25** | Minimum round trip is already 4 |
| Minimum R:R | 1.5 | **1.7** | Must sit strictly below the `target_1` multiple |
| Concurrent positions | 8–15 | **6–10** | Fewer names, watched closely |

---

# 15. EXIT RULES

## 15.1. Priority order

```
P1  ANOMALY SPIKE       risk proxy ≥ 75 or rise ≥ 25 since entry  → exit, urgent
P2  EXIT STOP BREACHED  C ≤ exit_stop                             → exit, urgent
P3  REGIME COLLAPSE     Panic/Bear                → exit all, riskiest first
P4  TARGET 1 REACHED    nothing sold yet          → sell half, patient
P5  TRAILING BREACHED   after P4 only             → exit remainder, urgent
P6  TIME STOP           held ≥ hold_max, profit < 0.5R  → exit all
P7  THESIS BROKEN       structure invalidated     → exit all
```

## 15.2. Urgency must be separate from limit price ⭐

```
Only genuine take-profit exits rest at a limit.
Every other exit reason fills at the open.
```

Conflating "must fill now" with "may wait at a limit" caused a real failure: a
time stop inherited a target limit and waited there indefinitely for a price
the position had just been declared unlikely to reach. Average holding period
was **103.8 sessions** against an intended 8–25; after the fix, 23.9.

*(§19.2, error 4.)*

## 15.3. Pre-settlement / illiquidity breach handling — a hard rule

```
If exit_stop is breached BEFORE the lock expires:
    log the event and the unrealised loss
    alert with the earliest possible sale date
    BLOCK all new buy signals until resolved
    NEVER average down — no discretion
    queue the sale for the first legal session
```

---

# 16. RISK AND PORTFOLIO CONSTRAINTS

| Rule | Limit [D] | Rationale |
|---|:---:|---|
| Maximum concurrent positions | 10 | Fewer names, properly monitored |
| Maximum new signals per day | 3 | More signals a symptom of loose thresholds |
| Maximum weight per security | 5–15% by archetype | See §11.5 |
| Maximum weight per sector | 35% | Diversification floor |
| Maximum weight per owner group | 10–15% | Related tickers are one economic bet |
| Max positions in a correlated archetype | 2 | A fourth bank is not a fourth bet |
| Max speculative / low-float positions | 1 | Highest tail risk under the lock |
| Total open risk | 5% NAV | Portfolio circuit breaker |
| Margin on speculative names | **Never** | Combines leverage with illiquidity |

Owner-group caps exist because several constituents are one economic bet
split across tickers; the exchange itself caps related-stock groups within
its flagship basket.

---

# 17. DATA QUALITY AS A BUSINESS GATE

> **A good signal on bad data is still a bad signal.**

```
DQ = 100 − stale_data_penalty
         − missing_bar_penalty
         − suspicious_gap_penalty
         − provider_disagreement_penalty
         − unresolved_corporate_action_penalty

DQ < 70  →  cap confidence                    [D]
DQ < 50  →  no actionable recommendation      [D]
```

This is a **business** gate, not a technical one: it changes what the system
is permitted to recommend, not merely what it logs.


## 17.1. Source trust is part of DQ, not an afterthought

A bar is not accepted merely because it parses. The recommendation path must also know **where it came from, under what access/licence basis, what the provider says the fields mean, and whether a second source agrees**.

`[GUESS]` v3.3 therefore retains these non-numeric source gates before an observation may become canonical:

```text
SOURCE_ADMISSION = access_rights_known
                AND schema_semantics_known
                AND lineage_snapshot_available
                AND date/time/unit normalization_verified
                AND provider_role_declared
```

If any item is false, the observation may remain in a research/quarantine store but must not silently become production canonical data.

Cross-provider disagreement is never solved by averaging two values. The system first reconciles **field semantics** (matched volume vs total volume, raw vs adjusted price, exchange date vs provider timestamp, corporate-action treatment). If the disagreement remains unresolved, the DQ gate caps or blocks the recommendation according to §17.


---

# 18. MANIPULATION RISK PROXY

## 18.1. The distinction that matters

Not every failed breakout is manipulation. But enforcement is real: in early
2026 the regulator published a case in which two individuals used **26
accounts** to trade a single security repeatedly, creating false supply and
demand, resulting in penalties and a trading ban.

*Source: SSC; Thoi bao Tai chinh.*

That establishes coordinated multi-account manipulation as a genuine risk. It
does **not** license inferring that any sharply rising security is
manipulated.

## 18.2. Proxy inputs, and the naming rule

```
abnormal turnover + repeated close-at-extreme + low free float
+ price-volume divergence + coordinated-looking bursts
+ extreme gap sequence + disclosure anomalies
+ unusual block/auction pattern
+ order-size stability (repeated near-identical sizes across sessions)
```

> **The field is named `manipulation_risk_proxy`, never `MANIPULATED`.**
> The system may report "statistically unusual price and volume patterns". It
> must never assert a legal conclusion. That determination belongs solely to
> the regulator.

---

# 19. TRAPS REGISTER

## 19.1. Anticipated traps

| Trap | Consequence | Defence |
|---|---|---|
| Index up, breadth down | Mistaking a narrow rally for a broad bull | Breadth dashboard + equal-weight index |
| One-security index dominance | Index signal wrong for most securities | Contribution decomposition |
| Limit-up breakout | Cannot buy at the backtested price | Non-fill simulation |
| Limit-down stop | Theoretical stop unexecutable | Gap and limit stress test |
| Corporate-action gap | False returns and RSI | Adjusted/raw dual price series |
| Current basket used historically | Survivorship bias | Point-in-time membership |
| Unconfirmed pivot | Look-ahead bias | Recognition delay of R bars |
| Earnings restatement | Fundamental hindsight | `published_at` + restatement version |
| EOD used as intraday | False precision | Restrict trigger granularity |
| Optimising 100 indicators | Data mining | Nested walk-forward validation |
| Foreign-flow one-day spike | False regime signal | Rolling standardised flow |
| Low-float technical breakout | Execution impossible | ADV and free-float filters |
| Price target with no invalidation | Uncontrolled risk | Every BUY requires a stop |
| **Rising price on flat turnover** | Re-rating read as strength | **Turnover confirmation (§6.3)** |
| **Sector map applied retroactively** | Classification leakage | **Effective-dated taxonomy (§7.2)** |
| **Undocumented endpoint treated as official API** | Fragile/contract-risk production dependency | Source Admission Policy (§25); quarantine until rights/schema verified |
| **Primary source failure silently triggers another website** | Hidden distribution shift and untraceable data | Explicit admitted fallback only; persist actual provider/fallback reason |
| **Two providers disagree and values are averaged** | Hides semantic/data errors | Reconcile semantics first; quarantine unresolved conflicts |

## 19.2. Seven errors found by executing the specification ⭐

These were not typos. Each was a rule that contradicted another rule, and
none was visible on paper. Every one now carries a named regression test.

| # | Error | Consequence | Fix |
|:---:|---|---|---|
| **1** | General volume floor applied to pullback setups | **Rejected 100% of pullback signals** — the primary setup — silently | Volume floor applies only to confirmation setups (§10.9) |
| **2** | `MIN_RISK_REWARD` equal to the `target_1` multiple | Gate **vacuous** when target untouched, **impossible** once trimmed | `MIN_RISK_REWARD` strictly below (§11.4) |
| **3** | Short-horizon high treated as resistance in a confirmed uptrend | Rejected 106 of 114 remaining candidates | Overhead check only when trend unconfirmed; use 52-week high; trim rather than void (§11.4) |
| **4** | `urgent` flag conflated "must fill now" with "may rest at a limit" | Time stop waited at target forever; hold 103.8 sessions vs 8–25 intended | Only take-profits rest at a limit (§15.2) |
| **5** | Corporate-action thresholds assumed one ratio direction | A 2-for-1 stock dividend labelled "cash dividend" | Classify on `min(ratio, 1/ratio)` |
| **6** | Placeholder assigned every security to the most restrictive group ⚠️ | **Produced plausible silence** — no signals while appearing to work perfectly | Fit groups from measured statistics; test fails if >50% land in one group |
| **7** | Statistical fallback routed into a sector-defined group | Brokerage received a commodity gate; signals could never fire | Fallback reaches only statistically defined archetypes (§8.4) |

**Error 6 is the most dangerous class of bug in the system.** Every other
error produced a crash or an obviously wrong number. That one produced
*plausible silence*.

---

# 20. PARAMETER REGISTRY

## 20.1. Structural / regulatory [S] — version by effective date

| Parameter | v3.3 value |
|---|---|
| Equity settlement | trade date + 2 trading sessions; allocation around/before 13:00 on T+2 |
| Regulatory sellability | afternoon of trade-date T+2 after allocation |
| EOD policy earliest exit | configurable; conservative baseline evaluates after T+2 close and executes next session |
| Pre-settlement stress scenario | `1 − (1−band)^3` is a **stress scenario**, not an absolute worst case |
| Price bands | 7% / 10% / 15% ordinary baseline |
| Tick sizes, HOSE | 10 / 50 / 100 VND |
| Lot size | 100 ordinary shares baseline |
| Exchange trading-service fee | **0.027%** for listed stocks under current schedule |
| Sale tax | 0.10% for individual equity transfer under current schedule |
| Brokerage regulatory maximum | **0.45%**; actual broker profile required |
| Commission includes exchange fee? | explicit boolean per broker tariff; never assume |
| Auction/LO priority | session-specific; no blanket `LO preferred` structural constant |

## 20.2. Academic [A] — preserve unless re-tested

| Parameter | Value |
|---|---|
| Medium-term momentum window | 126 sessions |
| Short-term reversal window | 20 sessions |
| Momentum skip | 21 sessions |
| Max hold for mean reversion | ≤ 60 sessions |
| Momentum logic | High-beta archetype only |
| Abort on Panic/Bear | Yes, absolutely |
| Downside-ATR substitution trigger | `atr_asym > 1.3` |
| Pre-Tet multiplier | 1.05 |
| **Post-Tet multiplier** | **1.00 — no bonus** |

## 20.3. Measured [M] — computed, never tuned

`beta` · `atr_asym` · `gap_p90` · `limit_hit_freq` · `max_floor_streak` ·
`ADV_20` · `free_float_pct` · `variance_ratio_5` · `hurst` · `vol_annual` ·
`idiosyncratic_share` · `amihud` · `foreign_flow_sensitivity`

## 20.4. Default [D] — the calibration list

| Parameter | Value | | Parameter | Value |
|---|---|---|---|---|
| `rs_long_rank` min | 60 | | `risk_per_trade` | 0.4–0.7% NAV |
| `rs_short_rank` max | 40 | | Total open risk | 5% NAV |
| `rs_short_rank` min (momentum) | 65 | | Max positions | 10 |
| `technical_score` min | 60 | | Max signals/day | 3 |
| `win_probability` min | 0.55 | | Sector cap | 35% |
| `risk_reward` min | **1.7** | | `target_1` / `target_2` | 2.0R / 3.5R |
| `R/ATR` min | 0.8 | | Trailing multiplier | 3.0 × ATR₂₂ |
| Min ADV | 20bn VND | | Setup premiums | 0.3% – 1.0% |
| Max ADV participation | 3% | | Regime breadth thresholds | 60/45/35/25% |
| Min notional | 10m VND | | Regime multipliers | 1.00/0.85/0.65/0.40/0 |
| Turnover ratio, strong | 1.00 | | Score weights | 25/20/20/15/10/10 |
| Turnover ratio, bull | 0.85 | | Backtest slippage | 15 bps |
| Min sample for hit rate | **30 trades** | | Shrinkage λ | 0.2–0.3 |
| DQ confidence cap | 70 | | DQ block threshold | 50 |
| Exclusion: floor streak | ≥ 5 | | Exclusion: gap p90 | > 4.5% |

Approximately **40 parameters require calibration.** Everything else is
structural, measured or academic.

---

# 21. REALISTIC EXPECTATIONS

| Metric | Achievable | Suspicious | Almost certainly fabricated |
|---|:---:|:---:|:---:|
| Hit rate | 52–58% | 60–65% | > 70% |
| Expectancy | +0.25R to +0.45R | +0.6R | > +1.0R |
| Sharpe, net of costs | 0.8–1.4 | 1.8 | > 2.5 |
| Max drawdown | 15–25% | 10% | < 8% |
| Longest losing streak | 6–9 trades | — | "never three in a row" |
| Fill rate | 70–85% | > 95% | 100% |

```
At 55% hit rate, +0.35R expectancy, 40 trades/year, 0.6% risked per trade:
    expected incremental return ≈ +8% of capital per year
    BEFORE subtracting 0.16%–0.86% round-trip friction
```

## 21.1. Measured results from the tested implementation

On **synthetic data** containing volatility clustering and a market factor but
deliberately **no genuine momentum or reversal structure**:

```
Signals              31 over 3.6 years on 22 symbols ≈ 9/year
                     scaled to 100 names ≈ 40/year — matches the design target
Primary setup        PB_MA20 accounted for 20 of 31, as intended
Fill rate            75.0%,  mean overnight gap +0.14%
Hit rate             40.0%,  95% CI [13.3%, 66.7%]
Expectancy           −0.02R
Average hold         23.9 sessions (inside the intended 8–25)
```

**Expectancy is negative and there is no edge — and that is the correct
answer.** A backtest reporting +0.4R on structureless data would be the
alarming result.

## 21.2. The most instructive number

```
Deflated Sharpe, declaring  1 trial (dishonest):  27.0%
Deflated Sharpe, declaring 24 trials (honest):     0.4%
```

Nothing about the strategy changed between those two rows — only the honesty
of the trial count. With a `regime × sector × archetype` design the trial
count is in the hundreds, which is exactly why §5.2 constrains where weights
may be fitted.

## 21.3. Phantom profit

Identical strategy, entering at `close_T` versus on T+1:

| | close_T (impossible) | T+1 (real) |
|---|---|---|
| Trades | 21 | **15** |
| Hit rate | 33.3% | 40.0% |

**Six of twenty-one trades — 29% — simply never happen.** Note the
counterintuitive direction: the wrong arm has a *lower* hit rate, because it
also takes the trades the gap gate would have refused.

---

# 22. COMPLIANCE

## 22.1. Hard constraints

```
Never claim guaranteed returns.
Never place orders automatically.
Never call a score a probability unless calibrated out of sample.
Never label manipulation as a legal conclusion.
Never use an unconfirmed swing in a backtest.
Never use current index membership for a historical universe.
Never call daily-bar Volume Profile true volume-at-price.
Never let an Elliott count override risk management.
Never publish BUY on stale data or an unresolved corporate action.
```

## 22.2. Legal positioning

- **Personal tool, one user, own capital.** Not licensed investment advice.
- **Publishing or selling output as buy/sell recommendations can enter regulated securities-investment-consultancy territory.** Vietnam's Securities Law defines securities investment consultancy as supplying analysis/reports and recommendations on buying, selling or holding securities to customers. Personal/internal use reduces the obvious customer-service exposure but **does not justify a claim that legal or data-licensing risk 'vanishes entirely'**.
- **Data-use rights are provider-specific.** The system must not assume that a publicly visible or exportable dataset may be programmatically scraped, redistributed, republished or used commercially. Terms/licence approval is a source-admission gate (§25).

## 22.3. Disclosure requirement

Every user-facing surface carries a disclaimer stating that outputs are
statistical signals for personal research, that `[D]` parameters are
uncalibrated, that forecasts are distributions rather than predictions, and
that a conservative three-limit-move pre-settlement HOSE stress is approximately −19.56%; this is a stress scenario, not a statement of three full legally locked sessions or an absolute worst case.

## 22.4. Privacy boundary

Any published artifact carries **percentages of NAV only** — never currency
amounts, share quantities or capital figures. A test must scan published
files for currency-scale integers and capital-related keys.

---

# 23. DEFINITION OF DONE

The system qualifies as **decision-support beta** only when all of the
following hold simultaneously.

| Gate | Condition |
|---|---|
| Data | Primary source admitted under §25 plus independent/official validation appropriate to the field; no undocumented fallback silently substitutes for a failed primary |
| Layout | Column identity **detected and cross-checked**, never assumed by position |
| Universe | Point-in-time VN100 snapshots stored at each review |
| Corporate actions | Derived and manually verified on ≥3 known cases |
| Classification | Sector, industry and archetype versioned and auditable |
| Normalisation | No absolute percentage or volume threshold applied universe-wide |
| Regime | Backtest results reported **per regime** |
| Sector | Stock-vs-sector and sector-vs-market RS with point-in-time benchmarks |
| Valuation routing | Every important industry has a strategy or a flagged fallback |
| Weight policy | Config-driven, versioned, never hardcoded by symbol |
| **Fitting discipline** | **Weights fitted only where ≥30 signals per cell exist (§5.2)** |
| Backtest | Non-fill/partial-fill uncertainty, next-session entry, T+2 regulatory sellability, EOD policy delay, floor locks and broker-specific costs modelled |
| Execution quality | Fill rate ≥ 70% and mean overnight gap ≤ 1.5% |
| Leakage | Automated tests against future data |
| Robustness | Profitable across multiple regimes, not one sector or one bull cycle |
| **Selection bias** | **Deflated Sharpe computed with an honest trial count** |
| **Placebo** | **Real grouping beats random grouping by ≥0.20 Sharpe** |
| Calibration | Score buckets show monotonic forward outcomes |
| Explainability | Output traces market → sector → archetype → security → gates |
| Reliability | Provider health, source-admission state, lineage and data-quality alerts |
| Security | No keys in the repository |
| Trading | No order-routing path exists |
| Governance | Model, feature, config and source-policy versions persisted with every signal; BRD and SRD synchronized after every material research/assessment change (§26) |

---



# 24. v3.3 RESEARCH & ASSESSMENT CORRECTION REGISTER

| Finding / prior claim | v3.3 decision | Production consequence |
|---|---|---|
| **SSI FastConnect is inaccessible to the product owner** | **Exclude SSI FastConnect from the active architecture and all future provider selection until the product owner explicitly re-enables it** | Existing SSI adapter/dependency is legacy code only; it must not be used as primary, fallback or a prerequisite for real-data validation |
| **DNSE now publishes a documented OpenAPI market-data surface and official Python SDK** | Promote DNSE to the leading automated market-data candidate `[GUESS]`, subject to Source Admission and live validation | Implement read-only DNSE adapter first for current-universe discovery and OHLCV; do not expose order APIs or trading tokens in the data module |
| **Vietstock offers a professional DataFeed product through API or Sync Data** | Retain Vietstock DataFeed as the leading **licensed secondary/alternative feed candidate**, subject to contract/access/schema/rights validation | It may become primary/secondary after Source Admission; no scraping assumption and no claim that access is currently available |
| **CafeF exposes historical data pages and Excel export, with a reference-use disclaimer; no equivalent official public API documentation was verified in this research** | Treat CafeF as **manual/spot-validation or research evidence only** by default | Undocumented endpoints are not a production dependency; automation requires explicit rights/terms verification |
| **Public visibility ≠ automation/redistribution permission** | Add source-rights gate to Data Quality / Definition of Done | Prevent technically successful but contractually unsafe ingestion |
| **Historical v3.1 documents disagreed between 58 and 18 tests** | Retain 18/18 only as historical evidence for the quarantined legacy archive; current maintained evidence is 99 offline tests under `src/tests/` | Historical evidence is not presented as current implementation or live-data validation |
| **Historical VN100 membership must not depend on a broker API** | Use HOSE official review/rule evidence and effective-dated snapshots as the target source of truth; manual import is acceptable until an admitted machine feed exists | `CURRENT_UNIVERSE_PROXY` remains explicit until PIT archive is supplied; no SSI dependency |
| **Compliance text said risk 'vanishes entirely' for personal/self-hosted use** | Remove categorical claim; personal use does not waive data/licensing or all legal obligations | More defensible product boundary |
| **Research/assessment changes could live outside core docs** | New mandatory BRD/SRD synchronization policy (§26) | No orphan architecture decisions |
| **Manual CSV/XLSX import was positioned too prominently for normal operation** | **Normal runtime becomes auto-refresh-on-run; manual files are fallback/debug/recovery only** `[GUESS]` | Application startup always performs a source sync check; network retrieval occurs only through an ADMITTED provider and according to capability-specific freshness/completeness policy |
| **Vietstock DataFeed is officially marketed as API/Sync Data, but public marketing pages do not provide enough contract detail to code safely** | Keep Vietstock as licensed secondary/alternative candidate; treat endpoint/auth/schema/rate-limit details as `TBD` until authorized documentation/access is obtained | Generic contract-gated adapter may exist, but no reverse-engineered Vietstock website endpoint is accepted as the production API |

### 24.1. Retained v3.1 corrections

| v3.0 item | v3.1 decision | Production consequence |
|---|---|---|
| T+2 described as three full locked sessions / earliest sale T+4 | **Corrected**: entry trade becomes sellable afternoon of its T+2; later EOD exit is policy | Persist regulatory and policy dates separately |
| Exchange fee 0.03% | **Corrected to 0.027%** | Versioned cost engine |
| Broker regulatory cap 0.5% | **Corrected to 0.45%** | Broker profile, no hardcoded 0.5% |
| Generic broker fee + exchange fee | **Unsafe** | Add `commission_includes_exchange_fee` to prevent double counting |
| Adjustment ratio classifies corporate-action type | **Removed** | Ratio is anomaly/validation only; official disclosure supplies action type |
| Missing OHLC forward-filled | **Removed for provider-missing bars** | Preserve missingness/status; never invent a flat trading session |
| Missing turnover could satisfy strong-bull pseudo-code | **Bug** | Missing turnover cannot confirm STRONG_BULL |
| `[M]` “cannot overfit” | **Terminology fixed** | Measured variable is `[M]`; selected threshold/tree is `[D]` |
| One dual-RS rule governs every setup | **Relaxed into three strategy families** | Trend pullback, momentum continuation, structural reversal tested independently |
| Touching a limit implies fill | **Too optimistic** | Conservative mode requires trade-through/open-better; exact touch is uncertain |
| Urgent exit = guaranteed next-open fill | **Too optimistic** | Floor-lock/no-liquidity can defer fill |

## 24.2. Real-data source contract — v3.3

**SSI FastConnect is OUT OF SCOPE / DISABLED by product-owner decision.** It is not a primary source, fallback, bootstrap dependency, validation prerequisite or planned near-term adapter. Historical references to its earlier implementation are retained only as provenance for the legacy v3.1 source package.

The active source contract is now:

1. **T0 official evidence** — HOSE / HNX / VSDC / SSC / issuer disclosures for the fields they govern.
2. **DNSE OpenAPI** — leading documented automated market-data candidate `[GUESS]`; integrated read-only adapter is implemented/offline-tested under `src/vnquant/`, but production use remains BLOCKED until live Source Admission passes.
3. **Vietstock DataFeed** — leading licensed secondary/alternative automated-feed candidate after access, contract, schema, rights, revision behaviour and sample reconciliation pass Source Admission.
4. **CafeF historical pages / authorized exports** — T2 reference validation by default; the implemented HTML adapter is explicit opt-in and is not a production primary source.
5. **No provider is production-ADMITTED yet.** Until DNSE or another provider passes live Source Admission, actionable live auto-refresh remains **BLOCKED**; the new module is offline-tested only. `[GUESS]`
6. Historical VN100 backtests require effective-dated official review snapshots or another independently verified PIT archive; current membership used retrospectively must remain `CURRENT_UNIVERSE_PROXY`.

## 24.3. Key verification sources retained from v3.2

These sources support provider capabilities/market governance previously researched. SSI links are intentionally omitted from the **active** source contract because SSI is excluded by product-owner decision.

- Vietstock API landing: https://api.vietstock.vn/
- Vietstock Services — DataFeed described as financial data via API or Sync Data: https://dichvu.vietstock.vn/Service.aspx
- CafeF historical data / Excel export and reference-use disclaimer: https://cafef.vn/du-lieu/lich-su-giao-dich-cafef-1.chn
- CafeF data contact / historical page disclaimer: https://cafef.vn/du-lieu/lich-su-giao-dich-prc-4/trang-1-ceo_02019.chn
- Vietnam Securities Law No. 54/2019/QH14, Article 4(32) / Article 72: https://english.luatvietnam.vn/law-on-securities-no-54-2019-qh14-dated-november-26-2019-of-the-national-assembly-179050-doc1.html
- HOSE VN100 Aug-2026 factsheet: https://staticfile.hsx.vn/Uploads/UploadDocuments/2487402/Form_Factsheet_MCIndices_VN_T08.2026.pdf
- HOSE-Index Ground Rules v4.0: https://staticfile.hsx.vn/Uploads/LocalFiles/ef15ff11e799483abd11677ad0443887/20250114_20241230_QD%20747%20HOSE%20Index%20Ground%20Rules.pdf
- Ministry of Finance Decision 1541/QĐ-BTC: https://thuvienphapluat.vn/van-ban/Chung-khoan/Decision-1541-QD-BTC-2025-prices-of-securities-services-applied-to-Vietnam-Exchange-655935.aspx
- Ministry of Finance Circular 102/2021/TT-BTC: https://vbpq.mof.gov.vn/DKC.FileManagement/FileStorage/File/104328


# 25. MULTI-SOURCE DATA GOVERNANCE

## 25.1. Provider trust tiers `[GUESS]`

| Tier | Role | Sources admitted in v3.3 | Rule |
|---|---|---|---|
| **T0 — official truth** | Market rules, index review documents, corporate actions, listing/trading status | HOSE / HNX / VSDC / SSC / issuer disclosures | Highest authority for the field it officially governs; still snapshot/version the evidence |
| **T1 — documented machine feed** | Repeatable market-data ingestion | **DNSE OpenAPI — candidate, NOT ADMITTED** | Official REST/WebSocket market-data surface and Python SDK verified; live credentials, response schema, VN100 filter semantics, quota/rate limits and reconciliation still require Source Admission |
| **T1L — licensed professional feed** | Candidate primary/secondary automated feed / independent validation | **Vietstock DataFeed** | Contract-gated candidate `[GUESS]`; generic adapter is implemented but cannot fetch live data until authorized endpoint/auth/schema mapping is supplied |
| **T2 — user-observable export/reference** | Manual cross-check, spot validation, gap investigation | **CafeF historical pages / Excel export** | Publicly visible data does not imply permission for automated scraping; no production dependency by default |
| **TQ — quarantine / research** | Experiments only | Undocumented endpoints, reverse-engineered calls, ad-hoc scraped pages | Never becomes canonical until it passes Source Admission |

The tier is **field-specific**. A provider may be authoritative for one field and merely a secondary check for another.

## 25.2. Source Admission Policy `[GUESS]`

Before a new provider adapter can write canonical production data, the project must record:

```text
provider_id
provider_role / trust_tier
access_basis (public documented API | user export | contract | official document)
terms_or_licence_reference
schema + field semantics
units / timezone / trading-date rules
raw-vs-adjusted policy
corporate-action policy
historical coverage and revision behaviour
rate limits / SLA if any
lineage snapshot method
independent validation plan
owner + reviewed_at + next_review_at
```

`[GUESS]` Admission lifecycle: `CANDIDATE -> DOCTOR_PASSED -> CROSS_VALIDATED -> ADMITTED`; active states may transition to `SUSPENDED` or `RETIRED`, a suspended provider must return to `CANDIDATE` for revalidation, and `RETIRED` is terminal. `RESEARCH_ONLY` may only transition to `RETIRED`. Direct `CANDIDATE -> ADMITTED` promotion is forbidden.

The registry stores access basis, licence reference, definitions for every
declared capability, schema and units, timezone/trading-date semantics,
raw-versus-adjusted policy, revision behavior, quotas, lineage method,
referenced validation results, owner, and review/next-review dates. Missing or
inconsistent evidence is a hard stop. Synthetic/test providers, reference-only
providers, undocumented sources, and incomplete authorized contracts cannot
enter admission states.

No provider can auto-promote itself because the endpoint returned HTTP 200.

## 25.3. Canonical-field routing `[GUESS]`

| Field | Preferred authority | Secondary role |
|---|---|---|
| Trading rules / price bands / settlement | Official venue/regulator/VSDC | Provider metadata for sanity checks |
| VN100 definition/review | HOSE official rulebook/review evidence | Admitted vendor or controlled manual import for operational scanning |
| Daily raw OHLCV | **DNSE OpenAPI after Source Admission** `[GUESS]`; no provider is yet production-admitted | Vietstock DataFeed after contract admission; CafeF opt-in reference pages for cross-check only |
| Corporate-action legal event/type | VSDC / exchange / issuer disclosure | Vendor adjustment factors only as anomaly evidence |
| Sector/industry classification | Effective-dated project taxonomy backed by sourced metadata | Admitted vendor taxonomy may be used as an explicitly versioned proxy; no SSI dependency |
| Fundamentals | Point-in-time filings/disclosures first | `[GUESS]` licensed DataFeed may become a normalized secondary source after admission |

## 25.4. Reconciliation policy `[GUESS]`

1. Preserve every raw provider payload/export with provider + retrieval time + hash.
2. Normalize units and semantics **before** comparing values.
3. Never average conflicting OHLCV values to make the disagreement disappear.
4. Prefer the source whose field definition matches the canonical contract and whose evidence is more authoritative for that field.
5. If unresolved, mark the observation disputed and let DQ cap/block recommendations.
6. Keep the losing observation for audit; canonicalization is a reversible decision.

## 25.5. What v3.3 does **not** claim

- It does **not** claim that Vietstock DataFeed is free, open, or already integrated.
- It does **not** claim that CafeF has an officially documented public API suitable for automated production ingestion.
- It does **not** approve reverse-engineered CafeF endpoints merely because third-party code can call them.
- It does **not** claim the current build has completed real VN100 multi-provider reconciliation.
- It does **not** claim production alpha.

---

# 26. RESEARCH / ASSESSMENT DOCUMENT SYNCHRONIZATION POLICY

This policy is mandatory for this project from v3.2 onward. It is a project governance requirement requested by the product owner, not a model-inferred rule.

## 26.1. Trigger

Any research, verification, backtest, code execution, provider test, regulatory review or architecture assessment that changes a material assumption must perform a **document impact assessment** in the same work cycle.

Material impact includes changes to: scope, business rule, data source, source trust, market rule, strategy hypothesis, threshold, feature definition, execution/fill assumption, risk rule, validation method, model routing, storage schema, security boundary, deployment rule, known limitation or implementation status.

## 26.2. Required update

When impact exists:

1. Update **both BRD and SRD** in the same version/date baseline.
2. BRD records **why the product/business rule changed and what outcome is required**.
3. SRD records **how the system contract/architecture/test/runbook must change**.
4. Add an entry to the correction/change register with evidence and implementation status.
5. Mark unsourced/invented/inferred content `[GUESS]`.
6. Distinguish `SPECIFIED`, `IMPLEMENTED`, `TESTED_OFFLINE`, `VALIDATED_REAL_DATA`, and `PRODUCTION_ACCEPTED`; never collapse them into one status.
7. If research finds no material change, record `NO_DOC_CHANGE` in the research log rather than silently editing prose.

## 26.3. Versioning invariant `[GUESS]`

BRD and SRD **must share the same major/minor project baseline** after a material research/assessment change. Code may legitimately lag the specification, but the SRD must say so explicitly.

## 26.4. Current synchronization state

As of **2026-09-14**, the canonical documents are synchronized at the **3.5 SSI-Free DNSE-First Auto-Sync baseline**. The maintained executable implementation is the tracked `src/vnquant/` package with tests under `src/tests/`; the quarantined v3.1 SSI archive is historical evidence only. The separately documented `vn100_multisource_feed_v1` package is absent from this checkout and Git history. The maintained suite passes 99 offline tests; no provider is admitted or live-data validated.


# 27. v3.3 SSI-FREE PROVIDER DECISION

## 27.1. Product-owner constraint

The product owner cannot register for SSI FastConnect and has instructed the project to **skip it**. This is a hard scope decision, not a temporary retry policy. Future research and implementation must not recommend SSI FastConnect as primary, secondary, fallback or a prerequisite unless the product owner explicitly reverses this decision.

## 27.2. Immediate business consequences

- **Automated real-data architecture remains provider-agnostic, but DNSE OpenAPI is now the leading documented market-data candidate `[GUESS]`.** No provider is production-admitted until live validation passes.
- **Vietstock DataFeed remains the leading licensed secondary/alternative candidate `[GUESS]`**, subject to price/access/contract/schema/rights feasibility.
- **Official HOSE/HNX/VSDC/SSC/issuer evidence remains the source of truth for governed fields.**
- **CafeF remains validation/manual import by default.** A publicly callable or browser-visible endpoint is not treated as an approved API.
- Until an automated provider passes Source Admission, the project may perform controlled feasibility/recovery work with authorized exports/manual files, but must not represent this as the normal production data path. `[GUESS]`

## 27.3. Implementation delta required

The maintained `src/vnquant/` revision now removes SSI from active runtime dependencies/configuration, uses a generic evidence-gated provider registry, exposes `NO_ADMITTED_PROVIDER`, and fails closed rather than silently selecting scraped or synthetic data. Remaining work is live provider admission, authorized contract verification, and real-data validation; the absent standalone package is not an implementation dependency.




# 28. v3.4 AUTO-REFRESH-ON-RUN DATA ACQUISITION

## 28.1. Product-owner requirement

Normal operation must **not require the user to prepare or import CSV/XLSX before each run**. `[GUESS]`

Every application start/run executes a **Source Sync Check** before actionable analytics are generated:

```text
APP START / RUN
      ↓
SourceSyncOrchestrator
      ↓
Provider Registry + Source Admission
      ↓
Freshness / completeness / revision check
      ↓
┌──────────────────────────────┐
│ data fresh and complete      │ → reuse canonical cache
│ data stale/incomplete        │ → incremental provider fetch
│ no admitted provider         │ → NO_ADMITTED_PROVIDER
│ provider temporarily failed  │ → degraded cached mode only if policy permits
└──────────────────────────────┘
      ↓
immutable raw snapshot
      ↓
normalize + reconcile + DQ
      ↓
canonical warehouse
      ↓
market / sector / signal / forecast / recommendation pipeline
```

A Streamlit UI rerun caused by a widget interaction is **not** treated as permission to repeatedly hit the remote provider. `[GUESS]` The application-level sync service must de-duplicate concurrent/rerun fetches and reuse a cached synchronization result for the same freshness state.

## 28.2. Incremental refresh, not full-history reload

After initial bootstrap, the normal fetch mode is incremental. `[GUESS]`

The orchestrator determines the latest accepted canonical session per capability and requests only the missing/recheck window needed to reach the expected current state. The exact revision-lookback window is provider/config specific and remains `[GUESS]` until real revision behavior is measured.

The system must not download the entire history on every launch unless an explicit rebuild/reconciliation job is requested.

## 28.3. Capability-specific sync policy

Each provider capability has an independent freshness state. `[GUESS]`

```text
daily_ohlcv
index_bars
vn100_membership
sector_metadata
corporate_actions
fundamentals
foreign_flow
disclosures
intraday_snapshot   # optional; not required for EOD-first v3.4
```

An app run always checks freshness/completeness for the capabilities required by the selected workflow. A remote fetch occurs only when policy says that capability is stale, incomplete, revised, or explicitly force-refreshed.

## 28.4. Vietstock role

Verified public Vietstock service material states that **DataFeed** provides financial information/data through **API or Sync Data** and is intended for professional integration. This supports Vietstock as a legitimate automated-provider candidate.

However, v3.4 does **not** claim that:

- the user currently has Vietstock DataFeed credentials or a contract;
- public documentation exposes the exact production endpoints, authentication flow, schema, revision semantics or rate limits needed by this application;
- `finance.vietstock.vn` browser/internal endpoints are an approved substitute for DataFeed;
- Vietstock DataFeed has passed project Source Admission or real-data reconciliation.

From v3.5, `VietstockDataFeedProvider` is `IMPLEMENTED_GENERIC_CONTRACT_GATE / TESTED_OFFLINE / NOT_ADMITTED / NOT_LIVE_VALIDATED`. It still cannot make legitimate production calls until authorized integration material supplies endpoint/auth/schema mappings.

## 28.5. Manual file role after v3.4

CSV/XLSX import remains supported only as a controlled auxiliary path: `[GUESS]`

- historical bootstrap where rights allow;
- disaster/recovery import;
- provider comparison and debugging;
- one-off official evidence import;
- reproducible test fixtures.

It is **not** the expected daily user workflow.

## 28.6. Degraded mode `[GUESS]`

If an ADMITTED provider is temporarily unavailable but the local canonical warehouse has a previously accepted snapshot, the UI may enter `DEGRADED_CACHED_DATA` only when:

- the data age is shown prominently;
- actionable recommendations are blocked or confidence-capped according to the DQ/freshness policy;
- the failed provider, last successful sync time and failure reason are persisted;
- no synthetic or undocumented source silently replaces the failed provider.

If no acceptable cached state exists, real-data analysis fails closed.

Application startup and direct pipeline execution must consume the governed synchronization result before feature, signal, candidate, or recommendation generation. If neither an admitted provider nor a policy-accepted cache exists, they persist, publish, and display `NO_ADMITTED_PROVIDER`; no CSV, synthetic, CafeF, or undocumented source may be substituted implicitly. When policy permits cache use, the result exposes provider, data age, last successful synchronization, DQ status, cache acceptance, and degraded mode. Older actionable artifacts must be hidden or removed when the gate blocks a run.

## 28.7. Acceptance criteria

The v3.4 runtime is not complete until tests prove at least:

```text
test_app_run_invokes_source_sync_check
test_fresh_cache_avoids_duplicate_remote_fetch
test_stale_data_triggers_incremental_fetch
test_streamlit_rerun_does_not_refetch_same_state
test_no_admitted_provider_fails_closed
test_provider_failure_never_falls_back_to_undocumented_source
test_manual_file_is_not_required_for_normal_startup
test_raw_response_snapshotted_before_normalization
test_sync_lineage_records_provider_and_fetch_time
```

These criteria are covered by the maintained offline suite under `src/tests/`,
including the dedicated `test_auto_sync_acceptance.py` harness. Fixture-only
admission transitions do not change any real provider's governance state.

## 28.8. Verification sources — refreshed 2026-09-13

- Vietstock Service Center — DataFeed described as financial data supplied via **API or Sync Data**: https://dichvu.vietstock.vn/Service.aspx
- Vietstock API landing: https://api.vietstock.vn/

The public material verifies the **existence and intended machine-integration role** of DataFeed. Exact implementation contract details remain pending authorized vendor documentation/access.

> ## DISCLAIMER
>
> This document describes the intended behaviour of a **personal research
> tool**. It is not investment advice and not legal advice.
>
> Every parameter tagged **[D]** is an uncalibrated starting value that must
> pass walk-forward validation, a Deflated Sharpe correction with an honest
> trial count, the execution-quality gate and the grouping placebo test
> before being trusted with real capital.
>
> Every measured result in §21 comes from **synthetic data**. No real market
> prices have been processed by the implementation these numbers describe.
>
> Forecasts are distributions and probabilities, never predictions. Past
> behaviour of any documented market effect does not guarantee future
> results.
>
> Under the current equity settlement cycle, securities are allocated by approximately 13:00 on trade-date T+2 and can be sold that afternoon. The model separately uses a conservative **three-limit-move pre-settlement stress scenario (~−19.56% on HOSE)** for sizing; this is not an absolute worst case and does not imply three full legally locked sessions.


# 29. v3.5 DNSE-FIRST MULTI-SOURCE RUNTIME MODULE

## 29.1. Research decision — 2026-09-13

Current public DNSE material verifies a documented OpenAPI market-data surface with REST endpoints for instrument metadata (`GET /instruments`), historical OHLC (`GET /price/ohlc`), foreign-investor data, market working dates and other market datasets. DNSE also publishes an official Python SDK and WebSocket market-data examples. This materially changes the provider feasibility ranking established in v3.4.

**Decision:** DNSE becomes the leading automated market-data **candidate** `[GUESS]` for the VN100 runtime. This is a candidate routing decision, not Source Admission. Production admission still requires live verification of credentials, exact response schema, data units, accepted `index_name` values, history depth, revision behaviour, quotas/rate limits and cross-source reconciliation.

Vietstock DataFeed remains a strong licensed feed candidate, especially for broader normalized financial/fundamental/event data, but its exact contract remains customer-specific/TBD until authorized material is supplied. CafeF remains T2 reference evidence: the historical pages expose OHLC/volume and label prices as `nghìn VNĐ`, but no equivalent official public API contract was verified.

## 29.2. Actual implementation status

A repository audit on 2026-09-14 found no package, tests, packaging files, or examples for `vn100_multisource_feed_v1` in the working tree, Git history, or committed archives. The standalone artifact was therefore **never committed to this repository**, and its former `10/10 PASS` claim is withdrawn as unreproducible.

The maintained implementation is instead integrated under `src/vnquant/`, with tests under `src/tests/`. DNSE/Vietstock/CafeF providers and source-sync logic exist there; the full integrated suite run from `src/` passed 99 offline tests on 2026-09-14. The list below describes the intended contract of the missing artifact, not a delivered standalone package:

Intended components:

```text
DNSEProvider
  -> current_index_members(index_name=...)
  -> daily_history(... via official SDK get_ohlc)

VietstockDataFeedProvider
  -> requires official contract mapping
  -> no guessed endpoints/auth/schema

CafeFReferenceProvider
  -> explicit opt-in
  -> public HTML historical table parser
  -> converts published thousand-VND price unit into canonical VND

SQLiteMarketCache
  -> per-provider/symbol/date cache
  -> incremental recent-window recheck

VN100Scanner
  -> universe -> stale/missing check -> parallel primary fetch
  -> DQ -> cache -> optional validator comparison
  -> never silently swaps primary source
  -> never averages unresolved provider disagreement
```

`recheck_days=5`, validator sample size `10` and close-disagreement flag threshold `0.5%` are `[GUESS]` operational defaults. They are configurable and are not trading-alpha parameters.

## 29.3. VN100 membership caveat

The DNSE official SDK example verifies the existence of `get_instruments(..., index_name=...)`. The public material inspected for this research did **not** expose the accepted enumeration/value set proving that the literal `index_name="VN100"` is valid. Therefore that literal remains `[GUESS]` until a live call is verified. The module fails closed if no symbols are returned and warns if the unique count is not 100.

Historical backtests remain governed by the point-in-time universe requirement. Even if DNSE successfully returns the current VN100 list, that list must not be silently used as historical membership.

## 29.4. Runtime routing policy `[GUESS]`

```text
Current VN100 + EOD OHLCV
  primary candidate: DNSE OpenAPI (after Source Admission)
  licensed alternative: Vietstock DataFeed (after contract admission)
  reference validator: CafeF (explicit opt-in only)

Fundamentals / corporate events / broader normalized financial data
  official issuer/HOSE/HNX/VSDC/SSC evidence remains field authority
  Vietstock DataFeed may become normalized operational source after contract admission

No silent fallback.
No production dependency on undocumented Vietstock/CafeF browser endpoints.
No auto-trading/order interface in this module.
```

## 29.5. Next validation gate

Before this module is described as `VALIDATED_REAL_DATA`, execute at least:

1. DNSE credential/SDK smoke test with read-only market-data methods.
2. Verify `index_name="VN100"` or replace it with a documented/current-universe resolution contract.
3. Reconcile at least a representative VN100 sample against CafeF and/or authorized Vietstock/official evidence for date, OHLC, volume and units.
4. Verify trading-calendar behaviour, corrections/revisions and history depth.
5. Record DNSE quotas/rate-limit behaviour observed under the user's plan.
6. Confirm Vietstock contract/licence before enabling its automated adapter.
7. Keep live evidence separate from fixture/offline test evidence.

## 29.6. Verification sources — accessed 2026-09-13

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


# 33. HISTORICAL v3.1 SSI ARTIFACT BOUNDARY

`legacy/vnquant_realdata_v3_1_gptcode_impl.zip`, including its embedded `vnquant/data/ssi.py`, SSI-specific `vnquant/jobs/doctor.py` and `vnquant/jobs/bootstrap.py`, credential/setup files, and `ssi-sdk` reference, is retained solely as immutable historical evidence. `legacy/IMPLEMENTATION_REPORT_GPTCODE_STYLE.md` describes that same retired build and is explicitly disabled. Neither artifact states the current implementation, test status, or real-data validation status.

The active package and deployment distributions must be discovered exclusively from `src/vnquant`. `legacy/` must be absent from wheel/source distributions, dependency declarations and pytest discovery, and direct checkout imports must fail closed. Negative tests rejecting SSI provider identifiers, credentials, modules, and dependencies are regression controls and must not be deleted merely because SSI is retired. No provider evidence, admission, or real-data-validation status changes under this archival classification.
