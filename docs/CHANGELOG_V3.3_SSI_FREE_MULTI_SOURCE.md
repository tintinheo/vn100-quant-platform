# CHANGELOG — VN100 Quant Platform v3.3 SSI-Free Multi-Source Baseline

**Date:** 2026-09-10  
**Documents:** BRD + SRD synchronized in the same baseline.

## Product-owner decision

SSI FastConnect is **OUT OF SCOPE / DISABLED** because the product owner cannot register for the service. It must not be recommended or used as primary, secondary, fallback, bootstrap dependency or real-data validation prerequisite unless the product owner explicitly reverses this decision.

## BRD changes

1. Removed SSI from the active provider hierarchy and canonical routing.
2. Changed automated-provider state to **NONE CURRENTLY ADMITTED**.
3. Promoted Vietstock DataFeed to the leading licensed machine-feed candidate `[GUESS]`, still subject to contract/access/schema/rights validation.
4. Retained HOSE/HNX/VSDC/SSC/issuer evidence as T0 field authority.
5. Retained CafeF as manual/reference/authorized-export validation by default.
6. Reframed historical VN100 membership around effective-dated HOSE evidence instead of broker API discovery.
7. Added a hard product rule that no undocumented/scraped endpoint may silently replace an unavailable provider.

## SRD changes

1. Removed `ssi-sdk` from the **v3.3 target dependency set**.
2. Removed SSI credentials/security flow from the active runtime contract.
3. Removed SSI doctor/bootstrap from the v3.3 runbook.
4. Added explicit `NO_ADMITTED_PROVIDER` behavior `[GUESS]`.
5. Added SSI-free runtime migration requirements and regression-test targets.
6. Reclassified the current v3.1 source package as **legacy implementation evidence**; its historical 18/18 tests do not validate the v3.3 data path.
7. No claim of real-data validation or production alpha.

## Implementation status

- Documents: **v3.3 synchronized**.
- Executable source: **legacy v3.1 only; not v3.3 compliant for real-data ingestion**.
- Vietstock adapter: **SPECIFIED / NOT IMPLEMENTED**.
- CafeF automated adapter: **NOT APPROVED / NOT IMPLEMENTED**.
- Official-source/manual import path: **partially specified; v3.3 generic importer still needs implementation**.
- Real-data validation: **NOT YET PERFORMED**.
