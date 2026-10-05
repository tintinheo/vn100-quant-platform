# P0.1b Live Independent Validation — Source Research Notes

Date: 2026-10-05
Status: research note; no provider admission is implied.

## Decision

P0.1b must not turn an undocumented browser/XHR endpoint into a production validator simply to obtain a second source.

### DNSE OpenAPI

DNSE publicly documents market-data capabilities including historical OHLC, security trading information and market working days. It remains subject to the repository's normal provider-admission evidence gates.

Evidence: https://developers.dnse.com.vn/docs/dnse/market-data/

### Vietstock DataFeed

Vietstock publicly describes DataFeed as a data-delivery service available through APIs or synchronized data. The exact authorized contract, endpoint schema, authentication, units, revision policy, rate limits, retention and usage rights are customer-specific and are not supplied in this repository.

Evidence: https://en.vietstock.vn/2021/10/vietstock-datafeed-intergrated-economic-and-financial-data-for-vietnam-36-458082.htm

The existing `VietstockDataFeedProvider` therefore remains contract-gated. P0.1b will consume it only after it is independently admitted and its upstream origin is verified.

### HOSE official EOD page

HOSE publishes an official end-of-day statistics page containing close/open/high/low and matched volume fields. The public website is JavaScript-driven and this research did not identify a documented, keyless machine API contract suitable for a production adapter. It is therefore not wired as an automated validator in this change.

Evidence: https://www1.hsx.vn/vi/du-lieu-giao-dich/thong-ke/du-lieu-cuoi-ngay

## Implementation consequence

P0.1b adds dual-provider live-validation orchestration using only providers that are:

1. `ADMITTED` for `daily_ohlcv`;
2. backed by explicit `independence_verified` upstream-origin evidence; and
3. distinct in verified origin from the primary provider.

If no such secondary source exists, the system records `WARNING/SINGLE_SOURCE_ONLY` rather than claiming `VERIFIED`. If two independent sources disagree materially under the governed comparison policy, the run is quarantined before new canonical analytics data is published.
