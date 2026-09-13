# VN100 Quant Platform — Current Baseline

- Document baseline: **v3.5 SSI-Free DNSE-First Auto-Sync — 2026-09-13**
- BRD EN: `BRD-VN100-Quant-Platform-v3.5-DNSE-FIRST-AUTO-SYNC.md`
- BRD VI: `BRD-VN100-Quant-Platform-v3.5-DNSE-FIRST-AUTO-SYNC-VI.md`
- SRD: `SRD-VN100-Quant-Platform-v3.5-DNSE-FIRST-AUTO-SYNC.md`
- SSI FastConnect: **OUT OF SCOPE / DISABLED**.
- Leading automated market-data candidate: **DNSE OpenAPI `[GUESS]`**, documented and adapter implemented, but **NOT ADMITTED / NOT LIVE VALIDATED**.
- Licensed secondary/alternative candidate: **Vietstock DataFeed `[GUESS]`**; generic contract-gated adapter implemented, live contract/access pending.
- CafeF: **T2 reference / explicit opt-in validation**, not an official public API dependency.
- New executable subsystem: `vn100_multisource_feed_v1` — **IMPLEMENTED + TESTED_OFFLINE, 10/10 PASS**.
- Main trading/analytics app: legacy v3.1 remains to be migrated/integrated with the new module.
- Real-data validation: **NOT YET PERFORMED**.

## Mandatory governance rule

After every material research or assessment change, update **both BRD and SRD** in the same work cycle/version. Keep BRD English + BRD Vietnamese synchronized. Unsourced/invented/inferred content must be labelled `[GUESS]`.
