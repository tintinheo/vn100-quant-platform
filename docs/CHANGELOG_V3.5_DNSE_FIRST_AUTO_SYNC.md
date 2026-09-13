# CHANGELOG — VN100 Quant Platform v3.5 DNSE-First Auto-Sync

**Date:** 2026-09-13  
**Documents:** BRD EN + BRD VI + SRD synchronized.

## Research changes

1. Verified DNSE OpenAPI official market-data documentation for instruments, historical OHLC, foreign-investor data and broader market datasets.
2. Verified DNSE official Python SDK examples using `DNSEClient`, `get_instruments(..., index_name=...)` and `get_ohlc(...)`.
3. DNSE promoted to leading automated market-data candidate `[GUESS]`, pending live Source Admission.
4. Vietstock DataFeed reclassified as leading licensed secondary/alternative candidate; exact contract remains customer-specific.
5. CafeF remains T2 reference source; public historical pages expose OHLC/volume in thousand VND but are not treated as an official public API.

## Implementation changes

Delivered standalone module `vn100_multisource_feed_v1`:

- `DNSEProvider`: read-only instruments + OHLC via official SDK interface.
- `VietstockDataFeedProvider`: contract-gated generic adapter; no guessed endpoints.
- `CafeFReferenceProvider`: explicit opt-in public HTML parser/reference validator.
- `SQLiteMarketCache`: incremental local cache.
- `VN100Scanner`: auto-refresh, DQ, parallel primary retrieval, optional secondary reconciliation.
- No silent fallback and no provider-value averaging.
- No order-routing interface.

Offline evidence: **10/10 tests passing** plus compileall. No live provider validation has been performed.

## `[GUESS]` defaults added

- `index_name="VN100"` for DNSE until live-verified.
- `recheck_days=5`.
- validator sample size `10`.
- close disagreement alert threshold `0.5%`.

These are configurable and must not be described as validated provider behaviour.
