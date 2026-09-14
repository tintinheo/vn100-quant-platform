# Provider Research Report — VN100 Data Sources

**File:** `PROVIDER-RESEARCH-REPORT.md`  
**Current internal revision:** **1.5 — 2026-09-14**
**Scope:** DNSE OpenAPI, Vietstock DataFeed, CafeF public data pages  
**Mục tiêu:** tự động quét current VN100 + OHLCV cho trading/research app, không phụ thuộc manual CSV/XLSX.

## Change Log

**Filename policy:** stable filename; append future provider research revisions here instead of creating a new filename.

| Revision | Date | Change |
|---|---|---|
| **1.0** | **2026-09-13** | **Verified DNSE documented OpenAPI/SDK; retained Vietstock as contract-gated candidate; CafeF as explicit reference source; recorded a standalone-module delivery claim later withdrawn by revision 1.2.** |
| **1.1** | **2026-09-13** | **Integrated the three adapters into the stable `vnquant` package with non-admitted default registry states and offline admission-separation tests; provider evidence is unchanged.** |
| **1.2** | **2026-09-14** | **Audit found the referenced `vn100_multisource_feed_v1` artifact was never committed; withdrew its unreproducible test claim and identified `src/vnquant/` as maintained implementation. Provider evidence/admission is unchanged.** |
| **1.3** | **2026-09-14** | **Hardened the maintained adapters so Vietstock requires endpoint semantics and retention rights before I/O and CafeF cannot be promoted from reference-only status. DNSE assumptions and provider evidence/admission are unchanged.** |
| **1.4** | **2026-09-14** | **Implemented evidence-backed admission records and legal lifecycle transitions. Provider research evidence/admission is unchanged.** |
| **1.5** | **2026-09-14** | **Documented the v3.1 SSI adapter and doctor/bootstrap archive as historical/disabled and added repository isolation checks. Provider evidence and admission are unchanged.** |

## 1. Kết luận

### DNSE — primary automated market-data candidate `[GUESS]`

**Verified:**

- DNSE có OpenAPI chính thức và tài liệu Market Data API.
- Tài liệu công khai xác nhận dữ liệu OHLC, instrument metadata, historical trades, bid/ask, foreign-investor data, working dates/session và market indices.
- Endpoint OHLC được tài liệu hóa là `GET /price/ohlc`.
- Endpoint instrument list được tài liệu hóa là `GET /instruments`.
- Official Python SDK repo có `DNSEClient`, `get_instruments(..., index_name=...)` và `get_ohlc(...)` examples.
- WebSocket SDK có OHLC, quote, trade, foreign-investor, market-index subscriptions.
- API Platform cấp API Key + API Secret; 2FA được mô tả cho đặt lệnh.
- PyPI hiện có `dnse-sdk-openapi` 1.4.6 và mô tả là official DNSE OpenAPI Python SDK.

**Chưa verified:**

- literal `index_name="VN100"` có được DNSE chấp nhận hay không. `[GUESS]`
- exact live response schema/units/history depth/rate limit của account người dùng.
- current VN100 returned count và reconciliation với HOSE.

**Decision:** implement read-only DNSE adapter; chưa production-admit cho đến live validation.

## 2. Vietstock DataFeed

**Verified:** Vietstock Service Center công bố DataFeed cung cấp thông tin/dữ liệu tài chính qua **API hoặc Sync Data**, phù hợp fintech/định chế/NĐT chuyên nghiệp. `api.vietstock.vn` tồn tại và mô tả dữ liệu realtime, company info, BCTC, macro data.

**Gap:** public material đã kiểm tra không cung cấp đủ endpoint/auth/request/response/rate-limit/licence contract để hard-code production adapter.

**Decision:** implement `VietstockDataFeedProvider` dạng **contract-gated**. Không hard-code/reverse-engineer `finance.vietstock.vn`/browser internal endpoint. Khi có contract chính thức, chỉ cần inject base URL, paths, headers, params, response paths và field mapping.

## 3. CafeF

**Verified:** CafeF public historical pages hiển thị OHLC, matched volume/value, adjusted price và cho export Excel; trang ghi đơn vị giá là **nghìn VNĐ** và nêu dữ liệu có giá trị tham khảo.

**Gap:** chưa verify official documented public API contract tương đương DNSE.

**Decision:** implement `CafeFReferenceProvider` bằng public HTML table, **explicit opt-in**, rate-limited/reference-only. Giá được chuyển từ thousand VND sang canonical VND. Không dùng CafeF làm authoritative VN100 membership hoặc silent production fallback.

## 4. Trạng thái artifact thực tế

Audit ngày 2026-09-14 không tìm thấy `vn100_multisource_feed_v1`, source tree `vn100_feed/`, standalone tests, packaging files hoặc examples trong working tree, Git history hay các archive đã commit. Artifact này chưa từng được commit vào repository; do đó các lệnh package-local và kết quả offline đã ghi trước đây không thể tái lập và bị rút lại.

Implementation được duy trì nằm tại `src/vnquant/`, với integrated tests tại `src/tests/`. Audit đã chạy `cd src && python -m compileall -q vnquant` thành công và `cd src && python -m pytest -q` với kết quả 60 passed. Trạng thái này không chứng minh provider live connectivity, schema/units thực tế, Source Admission hoặc real-data validation.

## 4.1. Stable-package integration

The providers are now also implemented under `src/vnquant/data/providers/` and connected to `provider_registry.py`. DNSE exposes only read-only market-data operations; Vietstock validates endpoint/authentication/schema/units/revision/rate-limit/retention/usage contract fields before I/O; CafeF is disabled/reference-only and cannot be admitted. All default registrations remain non-admitted, and successful fixture/HTTP mechanics cannot mutate admission state. Status remains **OFFLINE_TESTED / NOT LIVE VALIDATED / NOT ADMITTED**.

The registry no longer represents documentation with a boolean. It records the
full admission evidence contract and permits only the sequential `CANDIDATE →
DOCTOR_PASSED → CROSS_VALIDATED → ADMITTED` path. Missing evidence, incomplete
Vietstock contracts, undocumented/reference sources, synthetic/test providers,
and invalid transitions fail closed. This is offline governance evidence only;
it does not add or verify provider evidence.

## 5. `[GUESS]` operational defaults

- DNSE `index_name="VN100"` until live verified.
- cache recheck window = 5 calendar days.
- secondary-validator sample size = 10 symbols.
- close disagreement alert = 0.5%.
- initial app lookback example = 550 calendar days.

All are configurable and are not validated trading-alpha thresholds.

## 6. Verification sources

- DNSE API Platform: https://developers.dnse.com.vn/docs/guide/intro/api_platform/
- DNSE Market Data: https://developers.dnse.com.vn/docs/dnse/market-data/
- DNSE Instruments: https://developers.dnse.com.vn/docs/dnse/get-instruments/
- DNSE OHLC: https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/
- DNSE Foreign Trading: https://developers.dnse.com.vn/docs/dnse/get-foreign-trading/
- DNSE official SDK: https://github.com/dnse-tech/openapi-sdk
- DNSE SDK PyPI package: https://pypi.org/project/dnse-sdk-openapi/
- Vietstock API landing: https://api.vietstock.vn/
- Vietstock Services/DataFeed: https://dichvu.vietstock.vn/dao-tao/khoa-hoc---nhap-mon-tai-chinh-va-chung-khoan?index=44
- CafeF historical data sample: https://cafef.vn/du-lieu/lich-su-giao-dich-sdk-1.chn


## 8. Historical SSI evidence boundary

The unaltered `legacy/vnquant_realdata_v3_1_gptcode_impl.zip` contains the retired `SSIFastConnectV3Provider`, SSI credential environment variables, an `ssi-sdk` dependency, and SSI-specific doctor/bootstrap entry points. It and `legacy/IMPLEMENTATION_REPORT_GPTCODE_STYLE.md` are audit artifacts only and are excluded from active package discovery, built distributions, dependency resolution, imports, and pytest discovery. Negative SSI retirement tests remain deliberate regression controls. This classification supplies no new provider evidence and changes no admission or real-data-validation state.
