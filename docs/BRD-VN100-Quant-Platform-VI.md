# BRD — Nền tảng Nghiên cứu Định lượng & Khuyến nghị VN100

**Business Requirements Document · Tên file cố định · Version nội bộ hiện tại 3.5 · Bản tiếng Việt**

| | |
|---|---|
| File | `BRD-VN100-Quant-Platform-VI.md` |
| Version nội bộ hiện tại | **3.5 — SSI-FREE DNSE-FIRST AUTO-SYNC — 2026-09-13** |
| Tài liệu đi kèm | `SRD-VN100-Quant-Platform.md` |
| Bản tiếng Anh | `BRD-VN100-Quant-Platform.md` |
| Trạng thái hiện tại | **AUTO-SYNC, không dùng SSI. DNSE là automated market-data candidate hàng đầu `[GUESS]`; read-only adapter đã implement/offline-test nhưng chưa live-data validated/admitted. Vietstock vẫn contract-gated; CafeF là explicit reference validation.** |

## Quản lý tài liệu & Lịch sử thay đổi

**Chính sách tên file:** tài liệu này giữ **một tên file cố định**. Version được ghi **bên trong tài liệu**; các lần cập nhật sau phải sửa chính file này thay vì tạo filename theo version hoặc alias `LATEST`.

| Version nội bộ | Ngày | Thay đổi chính |
|---|---|---|
| 3.0 | 2026-09-09 | Hợp nhất BRD/SRD và kiến trúc quant phân tầng. |
| 3.1 | 2026-09-10 | Real-data-ready: sửa execution/settlement/cost, PIT discipline, provider boundary và validation honesty. |
| 3.2 | 2026-09-10 | Multi-source data governance, provider trust tiers, source-admission/reconciliation rules. |
| 3.3 | 2026-09-10 | Loại SSI FastConnect khỏi kiến trúc đang hoạt động; chuyển sang SSI-Free. |
| 3.4 | 2026-09-13 | Yêu cầu auto-refresh khi chạy app: sync-if-stale, cache, fail-safe; CSV/XLSX chỉ còn fallback/debug. |
| **3.5** | **2026-09-13** | **DNSE-first auto-sync: DNSE read-only adapter, CafeF reference validator, Vietstock contract gate, SQLite incremental scanner; claim offline-test sau đó bị rút lại bởi artifact audit ngày 2026-09-14. Chưa claim live-data validation.** |
| **3.5.1** | **2026-09-13** | **Tích hợp provider implementations ổn định tại `src/vnquant/data/providers/` và đăng ký mặc định ở trạng thái chưa admitted; HTTP success không đồng nghĩa Source Admission. Chưa claim live-data validation.** |
| **3.5.2** | **2026-09-13** | **Tích hợp `SourceSyncOrchestrator` persisted dưới app/pipeline, hiển thị cache lineage và chặn recommendation theo fail-closed. Chỉ offline-tested; trạng thái provider admission không đổi.** |
| **3.5.3** | **2026-09-14** | **Repository audit xác nhận `vn100_multisource_feed_v1` chưa từng được commit; bỏ claim 10/10 không thể tái lập và ghi nhận `src/vnquant/` là implementation path được duy trì. Không thay đổi trạng thái live validation/admission.** |
| **3.5.4** | **2026-09-14** | **Siết chặt provider boundary: Vietstock bắt buộc khai báo endpoint semantics và retention rights cùng các trường authorized contract khác, CafeF không thể được admitted, và mọi live assumption của DNSE vẫn là `[GUESS]`. Trạng thái provider admission không đổi.** |
| **3.5.5** | **2026-09-14** | **Thay cờ documented-access bằng hồ sơ admission evidence có cấu trúc và lifecycle bắt buộc. Không thay đổi trạng thái admission/live validation.** |
| **3.5.6** | **2026-09-14** | **Bắt buộc app và pipeline dùng synchronization result; publish/hiển thị `NO_ADMITTED_PROVIDER` khi không có provider admitted và cache được policy chấp nhận; công khai cache/degraded lineage và loại bỏ actionable artifact cũ. Chỉ offline-tested.** |
| **3.5.7** | **2026-09-14** | **Hoàn tất freshness theo capability, watermark theo provider/capability, deterministic rerun key, synchronization lock, incremental/recheck fetch, raw snapshot lineage và force refresh rõ ràng. Calendar chỉ loại cuối tuần và recheck defaults vẫn là `[GUESS]`; provider admission không đổi.** |
| **3.5.8** | **2026-09-14** | **Bắt buộc provider fetch trả raw payload bất biến cùng request metadata trước normalization; bootstrap và sync lưu evidence trước canonical bars, và CSV được ủy quyền hash mọi file giá/universe. Chỉ offline-tested; provider admission không đổi.** |
| **3.5.9** | **2026-09-14** | **Hợp nhất đánh giá DQ canonical, lưu lịch sử DQ/sync gắn canonical revision, và thực thi confidence/actionability gate hiện có tại §17. Chỉ offline-tested; provider admission và real-data status không đổi.** |
| **3.5.10** | **2026-09-14** | **Phân loại SSI adapter, doctor/bootstrap và implementation report v3.1 trong archive là lịch sử/bị vô hiệu hóa; thêm ranh giới package, distribution, dependency, import và test discovery. Bắt buộc giữ negative SSI-retirement tests.** |
| **3.5.11** | **2026-09-14** | **Đã implement bộ acceptance test offline §28.7 bằng DNSE SDK response giả, Vietstock contract data được inject, CafeF HTML cục bộ, clock/calendar deterministic, kiểm tra concurrency và temporary storage. Toàn bộ maintained suite: 99 passed; không claim provider admission hoặc live-data validation.** |
| **3.5.12** | **2026-09-14** | **Đối chiếu toàn bộ statement về implementation với nội dung repository được track: package độc lập `vn100_multisource_feed_v1` không có, còn `src/vnquant/` là implementation SSI-free được duy trì và full suite pass 99 tests offline. Không claim live validation/admission.** |
| **3.5.13** | **2026-09-14** | **Hợp nhất các bản BRD v3.3/v3.5 và ZIP bundle trùng lặp vào file canonical ổn định này. Nội dung lịch sử và các claim đã rút lại vẫn có thể truy xuất trong Git; không thay đổi business rule, trạng thái provider hoặc live validation.** |
| **3.5.14** | **2026-09-14** | **Audit constant/default argument runtime và chuyển các giá trị DQ, feature, regime, sector, recommendation, doctor và slippage có thể cấu hình vào registry có version `quant_parameters.v1.yaml`. Mọi giá trị chưa xác minh mang literal `[D] [GUESS]` cùng yêu cầu calibration/verification; identity về score/base và market rule mang `[S]`. Full suite: 101 passed offline.** |
| **3.5.15** | **2026-09-14** | **Làm rõ mỗi lần chạy là synchronization check, không phải fetch cả ba provider: capability state và force rõ ràng quyết định I/O; chỉ provider admitted mới hợp lệ, ưu tiên DNSE, Vietstock vẫn contract/admission-gated và CafeF chỉ dùng để sampled validation rõ ràng. Full suite: 102 passed offline; không thay đổi trạng thái admission/live validation.** |
| **3.5.16** | **2026-09-14** | **Đã triển khai ingestion review VN100 chính thức theo effective date và lineage snapshot nguồn, taxonomy ngành theo phiên bản/effective date, cùng quy tắc fail-closed cho tên backtest và qualification vốn thật. Chỉ test offline; không thay đổi live-data/provider admission.** |
| **3.5.17** | **2026-09-14** | **Bắt buộc OHLC và turnover VN-Index/VN100 canonical, có lineage raw snapshot cho nhánh cap-weighted. Series official thiếu hoặc stale phải công bố degraded proxy và không được tạo bull regime. Chỉ offline-tested; admission/live validation không đổi.** |
| **3.5.18** | **2026-09-14** | **Đã implement portfolio-risk fail-closed trước publication với sizing có costs, constraint portfolio/regime và audit decision. Chỉ offline-tested.** |
| **3.5.19** | **2026-09-15** | **Thêm reporting purged forward-validation fail-closed, gate riêng từng strategy family, accounting đầy đủ trials/placebo và gate shadow không dùng vốn. Chưa chạy validation giá thật vì chưa có provider admitted; mọi strategy/forecast vẫn suppressed.** |

**Governance:** sau mỗi research/assessment/implementation discovery có thay đổi material, phải cập nhật BRD + BRD-VI + SRD trong cùng work cycle, thêm một dòng Change Log vào mỗi file và cập nhật `CURRENT_BASELINE.md`. Nội dung suy luận/chưa có nguồn phải gắn `[GUESS]`.

**Executable parameter registry:** runtime duy trì `src/vnquant/config/quant_parameters.v1.yaml`.
Mỗi entry bắt buộc có value, classification literal `[S]`, `[M]`, `[A]` hoặc
`[D] [GUESS]`, và yêu cầu kiểm chứng. Default mới hoặc chưa được xác minh không
được chỉ gắn `[D]`; phải đồng thời gắn `[GUESS]` và nêu rõ evidence real-data,
walk-forward, provider contract hoặc authoritative rule cần có để bỏ nhãn đó.
Đưa constant vào YAML không đồng nghĩa đã validate hay chứng minh alpha.

---

# 0. CÁCH ĐỌC TÀI LIỆU

## 0.1. Những gì được hợp nhất và lý do

Tài liệu hợp nhất hai hướng phát triển độc lập đã đi đến nhiều kết luận giống nhau từ các điểm xuất phát khác nhau:

| Nguồn | Điểm mạnh | Điểm yếu |
|---|---|---|
| **BRD/SAD v2** | Nguồn tham chiếu tốt, kỷ luật `[GUESS]`, kiến trúc phân tầng sâu | Mới ở mức specification, chưa chạy thực tế |
| **Implementation** | Phát hiện mâu thuẫn bằng thực thi code, có số đo | Nguồn tham chiếu yếu hơn, kiến trúc phẳng hơn |

Các mâu thuẫn đã được sửa trong BRD này và những lỗi có thể tái diễn phải có regression test.

## 0.2. Quy ước tag tham số

| Tag | Ý nghĩa | Có được thay đổi không? |
|:---:|---|---|
| **[S]** | Structural — cố định bởi quy định/thị trường | Chỉ thay đổi khi quy định thay đổi |
| **[M]** | Measured — đo trực tiếp từ dữ liệu | Phép đo không tune; threshold/routing dùng phép đo vẫn có thể overfit |
| **[A]** | Academic — dựa trên nghiên cứu liên quan thị trường | Giữ nguyên trừ khi được kiểm định lại |
| **[D]** | Default — giả định khởi tạo, tương đương `[GUESS]` | **Phải calibration trước khi dùng vốn thật** |

Mọi nội dung mới do suy luận, giả định, chưa có nguồn hoặc chưa verify phải mang marker `[GUESS]`, kể cả khi đã là `[D]`.

## 0.3. Giả thuyết chiến lược lõi v1 — không phải định luật phổ quát

> **Trend Pullback hypothesis:** relative strength trung hạn giúp chọn cổ phiếu đáng quan tâm; short-term weakness có thể giúp timing entry.

Đây chỉ là **Strategy Family #1**, không phải gate bắt buộc cho mọi setup. Hệ thống tách ba family: **Trend Pullback**, **Momentum Continuation**, **Structural Reversal / Mean Reversion**.

---

# 1. ĐỊNH NGHĨA SẢN PHẨM

## 1.1. Sản phẩm là gì

Đây là một **decision-support system** cho một người dùng tự giao dịch vốn của mình. Sau mỗi phiên, hệ thống:

- scan VN100 point-in-time;
- chấm điểm các mã đủ điều kiện;
- tạo tối đa 3 trade candidates;
- xuất entry zone, trigger, invalidation, targets, position size theo %NAV;
- báo forecast dưới dạng distribution/probability thay vì point prediction;
- người dùng tự quyết định và tự đặt lệnh phiên kế tiếp.

Mục tiêu không phải “AI biết giá ngày mai”, mà là hệ thống biết **khi nào evidence đủ mạnh để hành động, entry ở đâu, khi nào thesis sai, rủi ro bao nhiêu và khi nào phải kết luận không đủ thông tin**.

## 1.2. Persona [D]

| Persona | Horizon | Nhu cầu chính |
|---|---|---|
| Swing trader | 5–20 phiên | Entry zone, invalidation, R multiple, catalyst risk |
| Position investor | 1–6 tháng | Valuation, earnings, sector regime, weekly structure |
| Research user | n/a | Scan toàn rổ, inspect feature, backtest, thử nghiệm model |

Không thiết kế cho HFT/intraday latency.

## 1.3. Non-goals

| Không phải | Lý do |
|---|---|
| Dịch vụ tư vấn cho người khác | Có rủi ro pháp lý/licensing |
| Auto order placement | Giữ human-in-the-loop |
| Intraday/day-trading platform | EOD-first, không giả định T+0 resale |
| Naked short selling | `SELL` = reduce/exit long |
| Dự đoán một mức giá duy nhất | Forecast phải là distribution |
| Scan toàn bộ thị trường | Tail kém thanh khoản không phù hợp liquidity gate |

---

# 2. BỐI CẢNH THỊ TRƯỜNG

## 2.1. Lịch sử ngắn và structural breaks

Thị trường tập trung Việt Nam bắt đầu từ 2000, sau đó mở rộng HNX và derivatives. Dữ liệu dài hạn chứa nhiều structural breaks về luật, hạ tầng, thành phần nhà đầu tư, sản phẩm và thanh khoản.

**[D] Hệ quả:** backtest dài hạn không được coi 2005 và 2026 là cùng một distribution. Regime segmentation là bắt buộc.

## 2.2. Hàm ý theo chu kỳ

- 2000–2005: market formation — dữ liệu ít phù hợp với distribution hiện đại.
- 2006–2008: liquidity/momentum có thể kéo valuation regime dài hơn kỳ vọng.
- 2009–2016: breadth mở rộng giúp cross-sectional model có ý nghĩa hơn.
- 2017–2019: derivatives/global risk cần vào regime model.
- 2020–2021: liquidity/herding regime rõ rệt.
- 2022–2023: bank/property phải gắn với credit, bond và governance risk.
- 2024–2025: price và foreign flow có thể divergence lâu; foreign net buy không phải điều kiện bắt buộc của bull market.
- 2026–2027: FTSE implementation tạo index-event regime; rebalance/crowding/foreign room cần thành features.

## 2.3. FTSE không đồng nghĩa MSCI và không đồng nghĩa mọi friction đã hết

FTSE Secondary Emerging và MSCI Emerging là hai quá trình riêng. Accessibility friction vẫn có thể tồn tại ở foreign room, FX, clearing/settlement, information flow, lending/short selling.

Hệ quả:
1. Không giả định một “wall of money” duy nhất.
2. Cash/long-only design phản ánh constraint thực của thị trường.

## 2.4. VN100 thực sự là gì

VN100 không đơn giản là 100 cổ phiếu vốn hóa lớn nhất. HOSE định nghĩa VN100 là **VN30 + VNMidcap** theo bộ rule eligibility/free-float/liquidity.

Membership bắt buộc effective-dated:

```text
index_code | symbol | effective_from | effective_to | review_source
```

Dùng rổ VN100 hiện tại để backtest 2015 tạo survivorship bias.

---

# 3. THAM SỐ THỊ TRƯỜNG ĐÃ VERIFY

## 3.1. Settlement và trading rules [S]

| Tham số | Giá trị v3.3 |
|---|---|
| Equity settlement | Trade date + 2 phiên; chứng khoán được phân bổ khoảng 13:00 T+2 và có thể bán buổi chiều sau khi phân bổ |
| EOD strategy policy | Tách riêng khỏi settlement pháp lý |
| Intraday T+0 resale | Không giả định |
| Short selling | Không giả định cho retail cash equity |
| Price band HOSE | ±7% |
| Price band HNX | ±10% |
| Price band UPCOM | ±15% |
| Lot size | 100 shares, nhưng vẫn nên lấy từ metadata theo venue/security |
| HOSE tick | 10 / 50 / 100 VND tùy mức giá |
| Auction/LO priority | Không mã hóa khẩu hiệu “LO luôn ưu tiên”; matching phụ thuộc session/order type |

Stress scenario trước settlement:

```text
1 − (1 − 0.07)^3 ≈ 19.56%
```

Đây chỉ là **three-limit-move stress scenario**, không phải worst case tuyệt đối và không có nghĩa 3 phiên bị khóa bán về mặt pháp lý.

## 3.2. Transaction cost [S/D]

- Brokerage commission: theo broker/user; regulatory max 0.45%.
- Exchange trading-service fee listed stocks: 0.027%.
- Sale tax cá nhân: 0.10% sale proceeds.
- Cash dividend tax: xử lý trong corporate-action/tax module.
- Margin interest: chỉ dùng nếu margin mode được bật.

Critical rule:

```yaml
commission_rate: 0.0015
commission_includes_exchange_fee: true
exchange_fee_rate: 0.00027
sell_tax_rate: 0.001
```

Nếu commission đã bao gồm exchange fee thì không cộng lần hai.

---

# 4. CÁC GIẢ THUYẾT CHIẾN LƯỢC

## 4.1. Không dùng một dual-RS rule cho mọi setup

Momentum có bằng chứng ở một số horizon/sample; reversal ngắn hạn không đồng nhất. Vì vậy mỗi strategy family có rule riêng.

## 4.2. Relative-strength measurements

```text
rs_long_market  = R_stock,126 − R_market,126
rs_long_sector  = R_stock,126 − R_sector,126
rs_short_market = R_stock,20  − R_market,20
rs_short_sector = R_stock,20  − R_sector,20
sector_rs_market = R_sector − R_market
```

Các rank phải point-in-time cross-sectional.

## 4.3. Strategy Family #1 — Trend Pullback [D]

```text
Long-horizon RS: mạnh
Short-horizon RS: yếu/neutral tạm thời
Trend: established
Entry: pullback / retest / controlled contraction
```

## 4.4. Strategy Family #2 — Momentum Continuation [D]

```text
Long-horizon RS: mạnh
Short-horizon RS: mạnh
Regime: STRONG_BULL
Archetype: high-beta / momentum-permitted
Volume: expansion required
```

## 4.5. Strategy Family #3 — Structural Reversal / Mean Reversion [D]

```text
Long-horizon RS: optional context
Short-horizon RS: weak / extreme
Structure: confirmed reversal evidence
Regime: không PANIC_BEAR
```

## 4.6. Ba benchmark vẫn bắt buộc

```text
RS(stock / market)
RS(stock / sector)
RS(sector / market)
```

---

# 5. MÔ HÌNH PHÂN TẦNG VÀ GIỚI HẠN CỨNG

## 5.1. Quyết định nghiệp vụ lõi

Không áp một fixed weight vector cho toàn VN100.

```text
MARKET
  ↓ MARKET REGIME
  ↓ SECTOR / INDUSTRY
  ↓ STOCK ARCHETYPE
  ↓ INDIVIDUAL EVIDENCE
  ↓ LIQUIDITY / RISK / DATA-QUALITY GATES
  ↓ SETUP → ENTRY ZONE → TRIGGER → INVALIDATION → TARGETS
```

thay vì:

```text
RSI + MACD + SMC + fixed weights → BUY / SELL
```

## 5.2. Routing được sâu, fitting không được quá sâu

Hierarchical routing là hợp lý nhưng fitting trên quá nhiều cell gây sample scarcity và overfit.

Nguyên tắc:
- Market regime: có thể fit weights.
- Sector: routing, valuation model, sector RS.
- Archetype: gating/risk policy.
- Security: dùng measured facts, không ticker-specific tuning.

Nếu vẫn cần cell-specific weights:

```text
w_cell = (1 − λ)·w_global + λ·w_cell_fitted     λ ≈ 0.2–0.3   [D]
```

## 5.3. Model versioning

`mvp_fixed_v1` chỉ là baseline/benchmark. Không được branch kiểu `if symbol == ...`.

---

# 6. MARKET REGIME

## 6.1. Năm regime [D]

| Regime | Hành vi ưu tiên |
|---|---|
| Strong Bull | Trend/momentum/RS |
| Concentrated / Weak Bull | Giảm confidence, ưu tiên genuine leaders |
| Range / Neutral | Structure/mean reversion |
| Distribution / Risk-off | Capital preservation, confirmed reversal |
| Panic / Bear | Hard risk gate, không ép hệ thống sinh BUY |

## 6.2. Dual-index scoring

```text
VN-Index và Equal-Weight VN100:
score = 1[C>MA50] + 1[C>MA200] + 1[MA50>MA200]

s = MIN(score_cap_weighted, score_equal_weighted)
```

Input cap-weighted và Equal-Weight VN100 phải là hai series độc lập thật sự;
không được sao chép equal-weight sang nhánh cap-weighted. Ưu tiên VN-Index
official, chỉ dùng VN100 official khi provenance/semantics đã admitted. Nếu
series official thiếu hoặc không tới expected session mới nhất, phải công bố
`DEGRADED_PROXY_UNAVAILABLE` hoặc `DEGRADED_PROXY_STALE`; khi BRD chưa cho phép
ngoại lệ rõ ràng, trạng thái này **không được** phân loại Strong Bull hoặc
Concentrated Bull.

Không được quyết định regime chỉ bằng một điều kiện như “VN-Index > MA200”.

## 6.3. Turnover confirmation [D]

```text
turnover_ratio = session turnover / MA20(turnover)
STRONG_BULL requires turnover_ratio ≥ 1.00
BULL        requires turnover_ratio ≥ 0.85
Missing turnover = NEUTRAL, không bao giờ là confirmation
```

## 6.4. Hard rule

| Regime | Archetype được phép | Size multiplier [D] |
|---|---|---:|
| Strong Bull | all | 1.00 |
| Concentrated Bull | large-cap, defensive, cyclical | 0.85 |
| Range | large-cap, defensive | 0.65 |
| Risk-off | defensive only | 0.40 |
| Panic/Bear | none | 0.00 |

**PANIC_BEAR phải sinh đúng 0 new signals.**

---

# 7. SECTOR LAYER

## 7.1. Sector leadership score [D]

```text
S_sector = w₁·RS₂₀ + w₂·RS₆₀ + w₃·Breadth + w₄·VolumeImpulse
         + w₅·EarningsRevision + w₆·ValuationZ + w₇·ForeignFlow
```

Weights là bootstrap `[D]` và chịu constraint sample size/shrinkage.

## 7.2. Taxonomy effective-dated

```text
Financials → Banks | Securities | Insurance
Real Estate → Residential | Industrial Parks | Commercial
Industrials → Construction | Infrastructure | Logistics/Ports | Services
Materials → Steel | Chemicals | Construction Materials
Consumer → Retail | Food & Beverage | Consumer Services
Technology · Energy · Utilities · Healthcare
```

Không được lấy sector map hiện tại để backtest lịch sử.

## 7.3. Valuation theo ngành

| Sector | Primary model |
|---|---|
| Bank | P/B–ROE, residual income |
| Securities | P/B + normalized P/E |
| Real estate | RNAV / SOTP |
| Construction/infra | EV/EBITDA, P/E, DCF |
| Retail/consumer | Forward P/E, PEG |
| Technology | Growth-adjusted P/E, FCF |
| Utilities | DCF, EV/EBITDA |
| Steel/materials | Normalized EV/EBITDA |
| Oil & gas | Mid-cycle EV/EBITDA, DCF |
| Logistics/ports | EV/EBITDA, DCF |

Valuation tạo **fair-value band + quality gate**, không tự sinh BUY.

---

# 8. ARCHETYPE LAYER

## 8.1. Sector không đủ

Các archetype chính:
- Large-cap / index leader
- High-beta cyclical
- Defensive / stable
- Event-driven / asset play
- Low-float / speculative

Một security có thể mang nhiều tag.

## 8.2. Archetype assignment dựa trên measurement [M]

```text
variance_ratio_5 · hurst · annualised volatility · ATR% · downside ATR ratio
· beta · idiosyncratic share · ADV · Amihud illiquidity · overnight gap p90
· limit-hit frequency · longest consecutive limit-down streak
· free float · foreign-flow sensitivity
```

## 8.3. Exclusion gates [D]

```text
ADV_20 < 20bn VND               → EXCLUDED
longest limit-down streak ≥ 5   → EXCLUDED
overnight gap p90 > 4.5%        → EXCLUDED
```

## 8.4. Tránh classification bug

Statistical fallback không được route vào sector-defined archetype.

```text
VR > 1.15 AND ADV ≥ 100bn AND vol < 38%  → large-cap trend treatment
VR < 0.85 AND vol < 33%                  → defensive treatment
otherwise                                → most conservative archetype
```

---

# 9. SIGNAL PIPELINE

Mỗi gate fail phải có rejection reason.

```text
GATE 0  MARKET REGIME
        Panic/Bear → abort, no signal

GATE 1  UNIVERSE ELIGIBILITY
        point-in-time VN100 · ≥280 sessions · ADV ≥20bn
        · not exchange-flagged · archetype ≠ EXCLUDED

GATE 2  RISK + DATA QUALITY
        manipulation_risk_proxy < threshold
        data_quality ≥ threshold

GATE 3  ARCHETYPE × REGIME
        regime phù hợp archetype
        + exogenous condition nếu có

GATE 4a RELATIVE STRENGTH
        rs_long_rank ≥ 60
        AND (rs_short_rank ≤ 40 if non-momentum
             rs_short_rank ≥ 65 if momentum)

GATE 4b SETUP
        ≥1 setup hợp lệ
        + volume condition đúng hướng logic

GATE 5  SCORE + GEOMETRY
        technical_score ≥60
        win_probability ≥0.55 khi sample đủ
        R/ATR14 ≥0.8
        risk_reward ≥1.7
        sizing_stop < exit_stop < entry

GATE 6  PORTFOLIO
        not held · positions <10 · sector ≤35%
        owner-group cap · correlation cap · total risk ≤5% NAV
        cash sufficient · notional ≥10m VND

SELECTION
        composite = 0.6·(score/100) + 0.4·win_probability
        max 2/archetype, max 2/sector/day
        top N, N=min(3, free slots)
```

Nhiều hơn 3 signal/ngày được xem là dấu hiệu threshold quá lỏng.

---

# 10. SETUP CATALOG

## 10.1. Setup families

| Family | Ví dụ | Volume |
|---|---|---|
| Pullback | `PB_MA20`, `PB_MA50` | phải FALL |
| Reversal | `REV_SUP`, `BB_LOWER`, Wyckoff spring | rise / n.a. |
| Trend | `TREND_MA`, `RS_LEADER` | rise |
| Momentum | `MOM_20` | rise |
| Contraction | `VCP` | rise khi expansion |
| Structure | Breakout-retest, BOS+retest | rise |

## 10.2. `PB_MA20` [D]

```text
TREND      MA20 > MA50 > MA200 · slope(MA50,10)>0 · C>MA200×1.02
PULLBACK   −4% ≤ dist_MA20 ≤ +2%
QUALITY    mean(V,5) < mean(V,20)×1.10
TRIGGER    bullish close / strong close location / short breakout
```

## 10.3. Wyckoff được operationalize

```text
Trading range: confirmed support/resistance + low directional efficiency
Spring: low < range_low AND close > range_low AND no subsequent acceptance below
Upthrust: high > range_high AND close < range_high AND no acceptance above
Sign of strength: close > range_high + positive relative volume + follow-through
```

Dùng volume z-score, không dùng fixed absolute multiplier.

## 10.4. SMC được operationalize

```text
Swing high: local max, chỉ CONFIRMED sau R bars
Bullish BOS: close > recent confirmed swing high
Liquidity sweep: low breaks structure low AND close recovers above
Bullish FVG: low[t] > high[t−2]
Order block: last opposite candle before impulsive BOS, có threshold displacement/reaction
```

Delayed pivot confirmation là bắt buộc để tránh look-ahead.

```text
Displacement = |C_t − C_{t−1}| / ATR14
```

## 10.5. Elliott Wave [D]

Chỉ là hypothesis generator, giữ nhiều alternate counts, có invalidation, không bao giờ override risk management.

## 10.6. Volume Profile

Daily OHLCV chỉ cho `EOD Volume Profile proxy`, không được gọi là true volume-at-price.

## 10.7. Loại khỏi thiết kế

`GAP_GO` và intraday-triggered patterns không phù hợp EOD execution.

## 10.8. Volume sign-flip rule

```text
mean-reversion / pullback:  want volume LOW   → clip(2 − volume_z, 0, 1)
trend / momentum:           want volume HIGH  → clip((volume_z − 1)/1.5, 0, 1)
```

Phải áp dụng đồng nhất ở gate và scoring.

---

# 11. ENTRY, STOP, TARGET VÀ POSITION SIZING

## 11.1. Entry là zone

```text
1. Không BUY chỉ vì score cao
2. Xác định setup_type
3. Xây entry ZONE từ structure + ATR
4. Cần trigger xác nhận
5. Đặt invalidation ngoài structure
6. Targets từ resistance hoặc R multiples
```

## 11.2. Entry không dùng signal-day close

Signal sinh sau close T; lệnh chỉ có thể fill T+1.

```text
LO_raw = close_T × (1 + premium)
entry  = round_DOWN_to_tick(LO_raw)
```

Premium [D]:
- Pullback/reversal: +0.5%
- Trend/RS leader: +1.0%
- Momentum: +0.8%
- Contraction/breakout: +0.3%

## 11.3. Dual-stop system

```text
exit_stop = min(structure_low − 0.5·ATR14,
                entry × (1 − max_stop_pct))

atr_eff = max(ATR14, 1.3 × downside_ATR14)

sizing_stop = min(entry − atr_mult·atr_eff,
                  entry × (1 − max_stop_pct×1.25))

INVARIANT: 0 < sizing_stop < exit_stop < entry
```

`exit_stop` phục vụ exit decision; `sizing_stop` chỉ phục vụ quantity/risk sizing.

## 11.4. Targets [D]

```text
R        = entry − exit_stop
target_1 = entry + 2.0·R
target_2 = entry + 3.5·R
risk_reward = (target_1 − entry) / R
REQUIRE risk_reward ≥ 1.7
```

`MIN_RISK_REWARD` phải nhỏ hơn target_1 multiple để gate có ý nghĩa.

## 11.5. Position sizing

```text
budget = NAV × risk_per_trade × regime_multiplier × seasonal_multiplier
qty_raw = budget / (entry − sizing_stop)
```

Tightening per security [M]: beta, limit-down streak, free float.

Ceilings: weight cap, 3% ADV, available cash, owner-group budget.

Round down 100-share lot.

Nếu notional < 10m VND → reject [D].

Signal strength và position size phải tách biệt.

---

# 12. SCORING VÀ CONFIDENCE

## 12.1. Composite structure

```text
EvidenceScore = w_s·SectorScore + w_a·ArchetypeScore
              + w_i·IndividualScore + w_f·FundamentalScore

ActionableScore = EvidenceScore × MarketGate × LiquidityGate × DataQualityGate
```

`mvp_fixed_v1` chỉ dùng benchmark/testing.

## 12.2. Technical components [D]

```text
25% setup quality
20% volume confirmation
20% relative strength
15% trend context
10% sector strength
10% flow confirmation
− risk penalty
```

## 12.3. Confidence không phải probability

`confidence` phản ánh completeness/consistency/data quality. Chỉ được gọi win probability khi đã calibration OOS.

## 12.4. Win probability

Phase 1: empirical hit rate chỉ publish khi exact setup/archetype có ≥30 trades `[D]`.

Phase 2: calibrated model:
- triple-barrier labels;
- entry T+1;
- enforce T+2 sellability + policy delay;
- logistic trước boosting;
- purged forward-chaining CV + embargo;
- calibration isotonic/sigmoid;
- p-gate [D] `p ≥ 0.55`.

30 trades chỉ là minimum publication floor, không phải proof of reliability.

## 12.5. Output contract

```json
{
  "symbol": "ABC",
  "as_of": "...",
  "universe_version": "...",
  "market_regime": "STRONG_BULL|CONCENTRATED_BULL|RANGE|RISK_OFF|PANIC_BEAR",
  "sector_score": 0,
  "stock_rs_vs_market": 0,
  "stock_rs_vs_sector": 0,
  "technical_score": 0,
  "fundamental_score": 0,
  "liquidity_score": 0,
  "data_quality": 0,
  "recommendation": "STRONG_BUY|BUY|WATCH|REDUCE|EXIT",
  "actionable_score": 0,
  "confidence": 0,
  "setup_type": "...",
  "entry_zone": [0, 0],
  "trigger": "...",
  "invalidation": 0,
  "target_1": 0,
  "target_2": 0,
  "exit_stop": 0,
  "sizing_stop": 0,
  "weight_pct": 0,
  "regulatory_sellable_date": "...",
  "policy_earliest_exit_fill_date": "...",
  "rationale": [],
  "risk_flags": [],
  "quality_flags": [],
  "model_version": "...",
  "feature_version": "..."
}
```

Published output dùng %NAV, không công bố số tiền/số cổ phiếu trong artifact public.

---

# 13. FORECASTING

Hệ thống forecast theo mức độ đáng tin cậy:

| Thành phần | Mức forecastability | Output |
|---|---|---|
| Volatility | tốt hơn | sigma path/persistence |
| Trend state | trung bình | P(up/side/down) |
| Price level | không dự báo point | quantile fan |
| Direction | yếu | calibrated probability, có suppression gate |

## 13.1. Price forecast là distribution

Hai phương pháp chạy song song:
1. Filtered historical simulation.
2. Conditional analogues.

Không ép average nếu hai phương pháp bất đồng. Output:

```text
q05, q25, q50, q75, q95
```

Median không phải price target.

## 13.2. Suppression rule

```text
Directional forecast requires out-of-sample AUC ≥ 0.52 [D]
Below that: NO NUMBER IS SHOWN
```

## 13.3. Forecast cấp thị trường là scenario

```text
Index_t = EPS_t × Justified_PE_t
```

Bear/Base/Bull phải có assumptions hiển thị cho user.

---

# 14. EXECUTION TIMING

## 14.1. Lifecycle

```text
S0 after close      generate signal
E0=S0+1             order may fill
E0+1                unsettled
E0+2 ~13:00         allocated; regulatorily sellable in afternoon
E0+2 after close    EOD policy evaluates
E0+3                earliest fill under conservative EOD policy
```

Persist cả:

```text
regulatory_sellable_date
policy_earliest_exit_fill_date
```

## 14.2. Limit-order policy

Daily-bar backtest phải coi `low == limit` là uncertain fill trong conservative/base mode, không auto-fill chỉ vì “touch”.

## 14.3. Gap gate [D]

```text
gap = open/reference_price / close_T − 1
threshold = MIN(archetype default, security gap_p90)

gap ≤ threshold×0.5 → full size
gap ≤ threshold     → reduce 70%
gap > threshold     → cancel
gap < −2.0%         → review
locked at ceiling   → cancel
```

## 14.4. Setup nhạy với overnight gap

Breakout/momentum chịu gap risk cao; pullback/slow trend ít bị ảnh hưởng hơn. Đây là lý do ưu tiên pullback trong EOD-first architecture.

---

# 15. EXIT RULES

## 15.1. Thứ tự ưu tiên

1. Hard invalidation / risk event.
2. Structural failure.
3. Time stop / thesis decay.
4. Target/trailing profit management.

## 15.2. Urgency tách khỏi limit price

Một quyết định cần lưu riêng:

```text
exit_reason
exit_urgency
reference_stop
chosen_limit_price
```

Không được dùng cùng một biểu thức giá cho mọi exit reason.

## 15.3. Breach khi chưa thể/khó exit

Nếu stop breach xảy ra trước lúc policy cho phép fill hoặc khi thanh khoản khóa sàn, hệ thống phải:
- giữ position trong accounting;
- đánh dấu `UNEXECUTABLE_EXIT` / `LOCKED_FLOOR`;
- tiếp tục mark-to-market;
- không giả định fill ở stop price;
- giảm confidence và cập nhật stress/risk.

---

# 16. RISK VÀ PORTFOLIO CONSTRAINTS

Các constraint chính `[D]`:
- max positions <10;
- max 35% một sector;
- owner-group cap;
- max 2 highly-correlated names/archetype;
- max 1 speculative;
- total open risk ≤5% NAV;
- liquidity/ADV cap;
- no new signal trong PANIC_BEAR;
- cash sufficiency;
- no same-position duplication.

Các threshold là `[GUESS]` cho đến khi validated.

---

# 17. DATA QUALITY LÀ BUSINESS GATE

DQ không chỉ là observability; DQ có thể block recommendation.

Kiểm tra tối thiểu:
- stale data;
- missing sessions;
- OHLC impossible values;
- duplicated bars;
- unresolved corporate action;
- provider disagreement;
- suspicious zero volume;
- symbol/listing lifecycle inconsistency;
- PIT universe/classification gaps.

Ví dụ policy `[GUESS]`:
- DQ <70 → cap confidence;
- DQ <50 → không actionable recommendation.

## 17.1. Source trust là một phần của DQ

Data đúng số nhưng nguồn/semantics không rõ vẫn là DQ risk.

---

# 18. MANIPULATION RISK PROXY

Không tuyên bố phát hiện “manipulation”. Output chỉ được gọi là `manipulation_risk_proxy`.

Inputs có thể gồm [M/D]:
- low free float;
- extreme turnover/price divergence;
- repeated limit hits;
- abnormal gaps;
- illiquidity;
- concentrated ownership proxy;
- unusual volume/price acceleration.

Proxy chỉ dùng để gate/penalty, không đưa ra cáo buộc pháp lý.

---

# 19. TRAPS REGISTER

## 19.1. Trap dự kiến

- survivorship bias;
- look-ahead từ pivot/financial statement publication;
- forward-fill price như thể có giao dịch;
- adjusted/raw price mixing;
- corporate-action inference sai;
- optimistic fill;
- double-count fee;
- overfitting threshold;
- small-sample hit rate;
- ticker-specific branching;
- current sector map dùng cho historical backtest;
- data vendor disagreement bị “average away”.

## 19.2. Lỗi đã tìm được khi chạy specification

Các lỗi implementation trước đây là regression requirements, đặc biệt:
- general volume floor làm chết pullback family;
- risk/reward gate bị vacuous/impossible;
- optimistic touch fill;
- current-universe survivorship;
- classification fallback sai;
- settlement wording sai;
- source/provider assumptions quá mạnh.

---

# 20. PARAMETER REGISTRY

## 20.1. [S]

Version theo effective date: price band, lot size, tick size, settlement, fees/tax, venue rules.

## 20.2. [A]

Giữ làm research baseline cho đến khi re-test: momentum/reversal evidence, seasonality hypotheses, volatility asymmetry.

## 20.3. [M]

Computed, không tune trực tiếp: ATR, beta, gap p90, ADV, free float, breadth, RS, limit streak, etc.

## 20.4. [D]/[GUESS]

Các threshold/weights như:
- RS rank 60/40/65;
- technical score 60;
- p gate 0.55;
- R/ATR 0.8;
- risk/reward 1.7;
- turnover 1.00/0.85;
- premiums;
- target multiples;
- portfolio caps;
- DQ thresholds;
- stop multipliers;
- regime multipliers.

Tất cả phải walk-forward/OOS validate trước real capital.

---

# 21. KỲ VỌNG THỰC TẾ

Kết quả implementation cũ dùng synthetic data **không phải bằng chứng alpha**.

Bất kỳ metric như hit rate/expectancy/fill rate trên synthetic data chỉ dùng để verify pipeline mechanics.

Không được dùng synthetic result để quảng bá production performance.

---

# 22. COMPLIANCE

## 22.1. Hard constraints

- Personal research tool.
- Không auto-trading/order routing.
- Không naked short.
- Không xuất sizing theo số tiền/cổ phiếu trong artifact public.
- Không gọi confidence là probability nếu chưa calibration.
- Không tuyên bố pháp lý tuyệt đối.

## 22.2. Legal positioning

Securities investment consultancy có phạm vi pháp lý riêng; self-hosted/personal use không đồng nghĩa mọi legal risk “biến mất hoàn toàn”. Cần wording thận trọng và kiểm tra pháp lý nếu sản phẩm được mở cho người khác.

## 22.3. Disclosure

UI/report phải thể hiện rõ:
- research only;
- model limitations;
- data source/status;
- `[GUESS]`/default assumptions;
- no guarantee of return.

## 22.4. Privacy boundary

Credentials, account identifiers, balances và private broker data không được publish ra artifact/shareable reports.

---

# 23. DEFINITION OF DONE

Một phiên bản production research-ready phải đạt tối thiểu:

1. Provider đã qua Source Admission.
2. Raw snapshots có lineage/hash.
3. Canonical schema được kiểm tra.
4. PIT VN100 universe.
5. PIT sector taxonomy.
6. Corporate actions được verify và không infer type từ adjustment factor.
7. Fundamentals có publication/effective timestamps.
8. Missing/no-trade/suspended/provider-missing được phân biệt.
9. Regime/breadth/sector calculation không leak future data.
10. Backtest thực tế với price band, lot, T+2, partial/non-fill, gap, suspensions, costs, tax.
11. Conservative fill policy.
12. Walk-forward/purged CV + embargo khi dùng ML.
13. Trial count trung thực cho Deflated Sharpe.
14. Placebo / grouping test.
15. Calibration kiểm tra probability.
16. Regime/sector slices.
17. DQ gate.
18. Audit trail signal→attempt→fill/reject→exit.
19. Không auto-trading.
20. Không dùng real-data validated label cho đến khi thực sự chạy và reconciliation trên dữ liệu thật.

---

# 24. v3.3 RESEARCH & ASSESSMENT CORRECTION REGISTER

## 24.1. Các correction giữ lại từ v3.1+

- T+2 sellability được tách khỏi EOD exit policy.
- Three-limit move chỉ là stress scenario.
- Exchange fee 0.027%; broker max 0.45%; anti-double-count.
- Không có blanket “LO always preferred”.
- Missing turnover không xác nhận bull.
- Missing data không forward-fill thành giao dịch giả.
- Threshold/routing vẫn có thể overfit dù raw metric là `[M]`.
- Touch limit không mặc định guaranteed fill.
- Compliance wording không tuyệt đối.
- Synthetic results không được trình bày như real results.

## 24.2. Real-data source contract — v3.3

Baseline v3.3 không phụ thuộc SSI. Provider mới phải qua admission trước khi write canonical production data.

## 24.3. Nguồn verification chính

Nguồn authority ưu tiên vẫn là HOSE, HNX, VSDC, SSC, issuer disclosures và văn bản pháp lý liên quan. DNSE/Vietstock/CafeF được dùng theo trust tier bên dưới; DNSE hiện là automated market-data candidate hàng đầu `[GUESS]` nhưng chưa production-admitted.

---

# 25. MULTI-SOURCE DATA GOVERNANCE

## 25.1. Provider trust tiers `[GUESS]`

| Tier | Vai trò | Nguồn ở v3.3 |
|---|---|---|
| **T0 — official truth** | Rules, index review, corporate action, listing/trading status | HOSE/HNX/VSDC/SSC/issuer |
| **T1 — documented machine feed** | Repeatable ingestion | **DNSE OpenAPI — candidate, CHƯA ADMITTED** |
| **T1L — licensed professional feed** | Candidate primary/secondary/validator | **Vietstock DataFeed** |
| **T2 — user-observable export/reference** | Manual cross-check | **CafeF pages/Excel export** |
| **TQ — quarantine** | Research only | undocumented/reverse-engineered/scraped endpoints |

Trust tier là field-specific.

## 25.2. Source Admission Policy `[GUESS]`

Trước khi provider được ghi canonical production data phải record:

```text
provider_id
provider_role / trust_tier
access_basis
terms_or_licence_reference
schema + field semantics
units / timezone / trading-date rules
raw-vs-adjusted policy
corporate-action policy
historical coverage and revision behaviour
rate limits / SLA
lineage snapshot method
independent validation plan
owner + reviewed_at + next_review_at
```

Admission lifecycle:

```text
CANDIDATE -> DOCTOR_PASSED -> CROSS_VALIDATED -> ADMITTED
active state -> SUSPENDED/RETIRED
SUSPENDED -> CANDIDATE/RETIRED; RESEARCH_ONLY -> RETIRED
```

Cấm promotion trực tiếp `CANDIDATE -> ADMITTED`; `RETIRED` là trạng thái cuối.
Registry phải lưu access basis, licence reference, định nghĩa từng capability,
schema và units, timezone/trading-date semantics, raw-versus-adjusted policy,
revision behavior, quotas, lineage method, validation results có evidence
reference, owner và ngày review/next review. Evidence thiếu/mâu thuẫn,
synthetic/test provider, reference-only/undocumented source hoặc authorized
contract chưa đầy đủ đều bị fail closed trước admission.

HTTP 200 không đồng nghĩa provider được admitted.

## 25.3. Canonical-field routing `[GUESS]`

| Field | Preferred authority |
|---|---|
| Trading rules/settlement/bands | Official venue/regulator/VSDC |
| VN100 definition/review | HOSE official evidence |
| Daily raw OHLCV | DNSE OpenAPI sau Source Admission `[GUESS]`; hiện chưa provider nào được production-admitted |
| Corporate-action legal event/type | VSDC/exchange/issuer |
| Sector/industry | Effective-dated project taxonomy từ sourced metadata |
| Fundamentals | PIT filings/disclosures first; licensed normalized vendor sau admission |

## 25.4. Reconciliation policy `[GUESS]`

1. Lưu raw payload/export với provider + retrieval time + hash.
2. Normalize units/semantics trước khi so sánh.
3. Không average conflicting OHLCV để che disagreement.
4. Ưu tiên source có semantics khớp canonical contract và authority cao hơn cho field đó.
5. Nếu unresolved → mark disputed, DQ cap/block recommendation.
6. Giữ losing observation cho audit; canonicalization phải reversible.

## 25.5. v3.3 không tuyên bố

- Vietstock DataFeed là free/open/already integrated.
- CafeF có official documented public API cho production ingestion.
- Reverse-engineered CafeF endpoints được approved.
- Current build đã multi-provider reconciliation trên VN100 thật.
- Production alpha.

---

# 26. CHÍNH SÁCH ĐỒNG BỘ BRD/SRD SAU RESEARCH/ASSESSMENT

Đây là governance rule bắt buộc do product owner yêu cầu.

## 26.1. Trigger

Mọi research, verification, backtest, provider test, regulatory review hoặc architecture assessment làm thay đổi assumption material đều phải có document impact assessment trong cùng work cycle.

## 26.2. Bắt buộc cập nhật

Khi có material impact:
1. Update **cả BRD và SRD** cùng baseline/version/date.
2. BRD ghi **vì sao business/product rule thay đổi và outcome yêu cầu**.
3. SRD ghi **system contract/architecture/test/runbook phải thay đổi thế nào**.
4. Ghi correction/changelog + evidence + implementation status.
5. Nội dung suy luận/chưa có nguồn gắn `[GUESS]`.
6. Phân biệt rõ `SPECIFIED`, `IMPLEMENTED`, `TESTED_OFFLINE`, `VALIDATED_REAL_DATA`, `PRODUCTION_ACCEPTED`.
7. Nếu research không tạo material change, ghi `NO_DOC_CHANGE` thay vì edit im lặng.

## 26.3. Versioning invariant `[GUESS]`

BRD và SRD phải cùng major/minor baseline sau material change. Code có thể lag nhưng SRD phải ghi rõ.

## 26.4. Current synchronization state

Tại **2026-09-14**, các tài liệu canonical đồng bộ ở baseline **3.5 SSI-Free DNSE-First Auto-Sync**. Executable implementation được duy trì là package được track tại `src/vnquant/`, với tests tại `src/tests/`; archive v3.1 có SSI đã bị quarantine và chỉ là historical evidence. Package độc lập `vn100_multisource_feed_v1` không có trong checkout hoặc Git history. Full maintained suite pass 99 tests offline; chưa provider nào được admitted hoặc live-data validated.

---

# 27. QUYẾT ĐỊNH PROVIDER SSI-FREE v3.3

## 27.1. Product-owner constraint

Product owner không thể đăng ký SSI FastConnect và đã yêu cầu **bỏ qua SSI**. Đây là hard scope decision, không phải retry policy tạm thời.

Future research/implementation **không được đề xuất SSI** làm primary, secondary, fallback hoặc prerequisite trừ khi product owner chủ động đảo ngược quyết định.

## 27.2. Hệ quả nghiệp vụ tức thời

- Automated real-data readiness chuyển từ provider-specific thành provider-agnostic specification.
- Chưa có automated market-data provider nào được ADMITTED.
- **DNSE OpenAPI là documented automated market-data candidate hàng đầu `[GUESS]`**, nhưng vẫn cần live Source Admission.
- **Vietstock DataFeed là licensed secondary/alternative candidate hàng đầu `[GUESS]`**, cần feasibility về price/access/contract/schema/rights.
- HOSE/HNX/VSDC/SSC/issuer là authority cho governed fields.
- CafeF mặc định chỉ dùng validation/manual import.
- Browser-visible endpoint không được xem là approved API.
- Trong thời gian chưa có admitted provider, chỉ được feasibility bằng authorized exports/manual files; không được gọi là production feed `[GUESS]`.

## 27.3. Implementation delta bắt buộc

Maintained revision tại `src/vnquant/` đã remove SSI khỏi active runtime dependency/config, dùng generic evidence-gated provider registry, expose `NO_ADMITTED_PROVIDER`, giữ lineage/hash cho controlled file import và fail closed thay vì silent fallback sang scraped/synthetic data. Phần còn thiếu là live provider admission, authorized contract verification và real-data validation; package standalone bị thiếu không phải implementation dependency.

---

# DISCLAIMER

Tài liệu này mô tả hành vi dự kiến của một **personal research tool**, không phải investment advice hay legal advice.

Mọi tham số `[D]` là starting value chưa calibration và phải qua walk-forward validation, honest trial count/Deflated Sharpe, execution-quality checks và placebo/grouping tests trước khi dùng vốn thật.

Mọi measured result từ implementation cũ dùng **synthetic data**, không phải kết quả thị trường thật.

Forecast là distribution/probability, không phải prediction chắc chắn.

Theo settlement hiện hành, chứng khoán mua được phân bổ khoảng 13:00 T+2 và có thể bán buổi chiều sau khi phân bổ. Model đồng thời dùng stress scenario ba phiên giảm sàn khoảng −19.56% trên HOSE cho sizing; đây không phải worst case tuyệt đối và không có nghĩa 3 full sessions bị khóa bán về mặt pháp lý.


# 28. v3.4 — TỰ ĐỘNG QUÉT/ĐỒNG BỘ DỮ LIỆU MỖI LẦN CHẠY APP

## 28.1. Yêu cầu nghiệp vụ

Luồng sử dụng bình thường **không được yêu cầu người dùng chuẩn bị/import CSV hoặc Excel trước mỗi lần chạy**. `[GUESS]`

Mỗi lần app khởi động/chạy phải thực hiện **Source Sync Check** trước khi tạo phân tích/khuyến nghị có thể hành động:

```text
APP START / RUN
      ↓
SourceSyncOrchestrator
      ↓
Provider Registry + Source Admission
      ↓
Kiểm tra freshness / completeness / revision
      ↓
┌──────────────────────────────────────┐
│ dữ liệu đủ mới và đầy đủ             │ → dùng canonical cache
│ dữ liệu stale/thiếu                   │ → incremental provider fetch
│ chưa có provider ADMITTED             │ → NO_ADMITTED_PROVIDER
│ provider lỗi tạm thời                 │ → cached degraded mode nếu policy cho phép
└──────────────────────────────────────┘
      ↓
immutable raw snapshot
      ↓
normalize + reconcile + DQ
      ↓
canonical warehouse
      ↓
market / sector / signal / forecast / recommendation
```

Do Streamlit có thể rerun script khi người dùng tương tác widget, **một UI rerun không đồng nghĩa với việc được phép gọi API lại**. `[GUESS]` Sync service phải chống duplicate/concurrent fetch và tái sử dụng kết quả sync khi freshness state chưa thay đổi.

## 28.2. Incremental refresh

Sau lần bootstrap đầu tiên, hệ thống chỉ tải phần dữ liệu thiếu hoặc cửa sổ cần kiểm tra revision; không tải lại toàn bộ lịch sử sau mỗi lần mở app. `[GUESS]`

Revision-lookback cụ thể phụ thuộc provider và giữ trạng thái `[GUESS]` cho đến khi đo được behaviour sửa dữ liệu thực tế.

## 28.3. Các capability cần quản lý freshness riêng

```text
daily_ohlcv
index_bars
vn100_membership
sector_metadata
corporate_actions
fundamentals
foreign_flow
disclosures
intraday_snapshot   # optional, không bắt buộc cho EOD-first
```

Mỗi lần app chạy đều kiểm tra freshness/completeness của các capability cần cho workflow hiện tại; chỉ gọi remote provider khi policy xác định dữ liệu stale, thiếu, có revision hoặc người dùng force refresh.

Sync check không phải là lệnh gọi provider vô điều kiện. Chỉ được chọn DNSE sau
khi admission và chỉ khi capability bắt buộc cần I/O theo quy tắc trên. Nếu DNSE
và Vietstock đều admitted cho capability đó, routing preference v3.5 `[GUESS]`
chọn DNSE mà không gọi thêm Vietstock. Vietstock chỉ hợp lệ sau khi authorized
contract và capability liên quan được admitted. CafeF mặc định bị disable và chỉ
được gọi trong workflow sampled cross-validation rõ ràng, khi quyền sử dụng cho
phép; CafeF không nằm trong routine startup fan-out.

Nếu product owner yêu cầu gọi cả ba provider ở mọi lần chạy, đó là thay đổi policy
material, không phải cách hiểu của force refresh. Trước khi implement phải giải
quyết licensing Vietstock và automation rights CafeF, rồi cập nhật đồng bộ cả hai
BRD, SRD, baseline và provider report.

## 28.4. Vai trò Vietstock

Nguồn dịch vụ chính thức của Vietstock xác nhận **DataFeed** cung cấp thông tin/dữ liệu tài chính qua **API hoặc Sync Data** và hướng tới tích hợp chuyên nghiệp. Điều này đủ để giữ Vietstock ở vị trí automated-provider candidate hợp lệ.

Nhưng v3.4 **không tuyên bố** rằng:

- hiện đã có credentials/contract Vietstock DataFeed;
- public website đã cung cấp đầy đủ endpoint/auth/schema/rate-limit để code production an toàn;
- endpoint nội bộ của `finance.vietstock.vn` có thể thay thế API DataFeed;
- Vietstock đã pass Source Admission hoặc real-data reconciliation.

Từ v3.5, `VietstockDataFeedProvider` generic contract-gated đã **IMPLEMENTED + TESTED_OFFLINE**, nhưng vẫn `NOT ADMITTED / NOT LIVE-VALIDATED`; nó không thể gọi live cho đến khi có endpoint/auth/schema mapping từ contract chính thức.

## 28.5. Vai trò CSV/XLSX từ v3.4

CSV/XLSX chỉ còn là đường hỗ trợ có kiểm soát `[GUESS]` cho:

- bootstrap lịch sử khi quyền sử dụng cho phép;
- disaster/recovery;
- debug và đối chiếu provider;
- import bằng chứng chính thức một lần;
- test fixtures tái lập được.

Đây **không phải** daily workflow mong đợi.

## 28.6. Degraded mode `[GUESS]`

Nếu provider ADMITTED lỗi tạm thời nhưng local warehouse còn snapshot đã được chấp nhận, UI có thể chạy `DEGRADED_CACHED_DATA` khi:

- hiển thị rõ tuổi dữ liệu;
- recommendation bị block hoặc confidence-cap theo DQ/freshness policy;
- lưu provider lỗi, thời gian sync thành công cuối và failure reason;
- không âm thầm thay bằng synthetic hay nguồn undocumented.

Nếu không có cache đủ điều kiện, real-data analysis phải fail closed.

`src/app.py` và direct pipeline đều phải kiểm tra synchronization result trước khi tạo feature, signal, candidate hay recommendation. Nếu không có provider admitted và cũng không có cache được policy chấp nhận, phải persist, publish và hiển thị `NO_ADMITTED_PROVIDER`; không được dùng ngầm CSV, synthetic, CafeF hoặc nguồn undocumented. Nếu policy cho phép cache, kết quả phải hiển thị provider, tuổi dữ liệu, lần đồng bộ thành công gần nhất, DQ status, cache-acceptance và degraded mode; artifact actionable cũ phải bị ẩn hoặc xóa.

## 28.7. Acceptance criteria

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

Các tiêu chí này được cover bởi maintained offline suite trong `src/tests/`,
bao gồm harness riêng `test_auto_sync_acceptance.py`. Admission transition chỉ
dùng fixture không làm thay đổi governance state của bất kỳ provider thật nào.

## 28.8. Nguồn verify cập nhật 2026-09-13

- Vietstock Service Center — DataFeed được mô tả cung cấp dữ liệu qua **API hoặc Sync Data**: https://dichvu.vietstock.vn/Service.aspx
- Vietstock API landing: https://api.vietstock.vn/

Các nguồn public này xác nhận **sự tồn tại và vai trò machine-integration** của DataFeed; implementation contract cụ thể vẫn cần tài liệu/access được Vietstock cấp.


# 29. v3.5 — MODULE AUTO-SYNC ĐA NGUỒN, DNSE LÀ PRIMARY CANDIDATE

## 29.1. Quyết định sau research ngày 2026-09-13

Tài liệu DNSE hiện tại xác minh OpenAPI có market-data REST cho danh sách/metadata mã (`GET /instruments`), lịch sử OHLC (`GET /price/ohlc`), dữ liệu NĐT nước ngoài, ngày giao dịch và các dataset thị trường khác. DNSE cũng công bố Python SDK chính thức và WebSocket market-data examples.

Vì vậy, **DNSE trở thành automated market-data candidate hàng đầu `[GUESS]`** cho runtime VN100. Đây chưa phải Source Admission. Trước production cần live-verify credentials, response schema, units, accepted `index_name`, history depth, correction/revision behavior, quota/rate limits và reconciliation với nguồn thứ hai.

Vietstock DataFeed vẫn là licensed feed candidate mạnh cho normalized financial/fundamental/event data, nhưng contract chi tiết vẫn phải lấy từ Vietstock. CafeF ở T2 reference: trang lịch sử công khai OHLC/volume và ghi giá theo `nghìn VNĐ`, nhưng chưa xác minh official public API contract tương đương DNSE.

## 29.2. Trạng thái implementation thực tế

Audit repository ngày 2026-09-14 không tìm thấy package, tests, packaging files hoặc examples của `vn100_multisource_feed_v1` trong working tree, Git history hay các archive đã commit. Vì vậy artifact độc lập này **chưa từng được commit trong repository này** và claim `10/10 tests PASS` trước đây không thể tái lập nên đã bị rút lại.

Implementation được duy trì hiện nằm tại `src/vnquant/`, với tests tại `src/tests/`. Các provider DNSE/Vietstock/CafeF và source-sync logic đã được tích hợp ở đó; full integrated suite chạy từ `src/` đã pass 99 tests offline ngày 2026-09-14. Danh sách dưới đây chỉ mô tả contract dự kiến của artifact bị thiếu, không phải package đã giao:

Module dự kiến gồm:

```text
DNSEProvider
VietstockDataFeedProvider (contract-gated)
CafeFReferenceProvider (explicit opt-in)
SQLiteMarketCache
VN100Scanner
Data Quality + cross-source disagreement flags
```

Scanner không silent fallback và không average giá khi provider bất đồng. `recheck_days=5`, validator sample `10`, close-difference flag `0.5%` là `[GUESS]` operational defaults, cấu hình được.

## 29.3. Lưu ý VN100

Official DNSE SDK xác minh `get_instruments(..., index_name=...)` tồn tại, nhưng public material đã kiểm tra chưa chứng minh literal `index_name="VN100"` là accepted value. Vì vậy literal này là `[GUESS]` cho đến live validation. Module fail closed nếu không có symbol và cảnh báo nếu unique member count khác 100.

Current membership, kể cả lấy thành công từ DNSE, **không được dùng im lặng cho historical backtest**. PIT universe requirement vẫn giữ nguyên.

## 29.4. Routing target `[GUESS]`

```text
Current VN100 + EOD OHLCV:
  DNSE OpenAPI        -> primary candidate sau admission
  Vietstock DataFeed -> licensed alternative sau contract admission
  CafeF               -> opt-in reference validator

Fundamental/events:
  official disclosures -> field authority
  Vietstock DataFeed   -> normalized operational candidate sau admission
```

Không reverse-engineer Vietstock/CafeF browser endpoint thành production API. Module này không có order routing/auto trading.

## 29.5. Gate tiếp theo

Để chuyển sang `VALIDATED_REAL_DATA` cần chạy live DNSE read-only smoke test, verify VN100 filter, đối chiếu sample OHLCV/units với nguồn thứ hai, kiểm tra calendar/history/revision/rate-limit, và chỉ enable Vietstock sau khi có contract hợp lệ.

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


# 33. RANH GIỚI ARTIFACT SSI v3.1 LỊCH SỬ

`legacy/vnquant_realdata_v3_1_gptcode_impl.zip`, gồm `vnquant/data/ssi.py`, `vnquant/jobs/doctor.py`, `vnquant/jobs/bootstrap.py`, các file credential/setup và tham chiếu `ssi-sdk`, chỉ được giữ làm bằng chứng lịch sử bất biến. `legacy/IMPLEMENTATION_REPORT_GPTCODE_STYLE.md` mô tả cùng build đã retired và được ghi rõ là bị vô hiệu hóa. Không artifact nào thể hiện implementation, test status hoặc real-data validation hiện tại.

Active package và deployment distribution chỉ được discover từ `src/vnquant`. `legacy/` phải vắng mặt khỏi wheel/source distribution, dependency declarations và pytest discovery; import trực tiếp từ checkout phải fail closed. Negative tests từ chối SSI provider ID, credentials, module và dependency là regression controls bắt buộc giữ lại. Phân loại archive này không thay đổi provider evidence, admission hoặc real-data-validation status.


## 34. Phân loại effective-dated và governance backtest (2026-09-14)

Bằng chứng review VN100 chính thức phải được lưu raw immutable/content-addressed trước khi ghi membership. Mỗi record giữ `index_code`, `symbol`, `effective_from`, `effective_to`, `source`, và `source_snapshot_id`; chỉ record cover đúng ngày mới là `STRICT_PIT`.

Taxonomy ngành giữ `symbol`, `sector_code`, `sector_name`, `taxonomy_version`, `effective_from`, `effective_to`, `source`, và `source_snapshot_id`. Join lịch sử phải truyền lineage taxonomy/snapshot. Thiếu phân loại PIT chỉ được dùng current-sector proxy có cảnh báo cho exploratory work.

Mọi output mang tên **historical VN100 backtest** bắt buộc dùng universe `STRICT_PIT`. Run `CURRENT_UNIVERSE_PROXY` hoặc current-sector proxy phải giữ cảnh báo leakage và luôn `NOT_ELIGIBLE_FOR_REAL_CAPITAL_STRATEGY_QUALIFICATION`. Muốn có eligibility để qualification cần cả universe và sector PIT; eligibility này không chứng minh strategy profitable hay đã qualified.


## 35. Phê duyệt portfolio-risk trước publication (2026-09-14)

Mọi recommendation đã dựng phải qua portfolio-risk trước publication. Quantity được làm tròn xuống theo lot cấu hình sau khi tính account equity, loss từ entry đến risk stop, round-trip costs và maximum permitted loss do chủ tài khoản cung cấp. Recommendation theo thứ hạng giữ capacity tuần tự; signal score không được làm tăng size.

Service áp dụng limit versioned `[D] [GUESS]` cho total exposure, concurrent positions, sector concentration, số lượng/exposure của correlated group, ADV participation, total open risk, per-security exposure, cash và multiplier exposure/risk theo regime. Thiếu/sai account state, entry, risk stop hoặc ADV phải fail closed. Recommendation bị reject nếu stop-distance ngoài biên hoặc các ceiling không đủ minimum lot/minimum viable notional.

Mọi kết quả được lưu thành decision event `ACCEPTED`, `RESIZED` hoặc `REJECTED`, kèm quantity, estimated loss/notional, binding constraint, timestamp/ID, regime và configuration version chính xác. Chỉ accepted/resized mới được publish actionable; rejected vẫn nằm trong audit dataset. Offline mechanics không chứng minh alpha, provider admission hoặc real-data validation.


# 36. VALIDATION SAU PIT VÀ SHADOW OPERATION (2026-09-15)

Sau khi có giá và classification point-in-time từ nguồn admitted, từng strategy
family phải được đánh giá riêng bằng expanding forward folds với purge/embargo
bằng label horizon cộng 21 phiên `[D] [GUESS]`. Report phải giữ sample/effective
sample, fill và mọi unfilled attempt, costs, turnover, drawdown, stability theo
fold, calibration, OOS performance, toàn bộ model/parameter combination đã thử,
và phân phối grouping placebo của classification.

Không đạt sample, conservative execution, stability, multiple-testing trung thực,
placebo, AUC hoặc calibration thì trạng thái là `SUPPRESSED`. Report đạt validation
chỉ được sang `SHADOW_ONLY`; chỉ sau giai đoạn quan sát không dùng vốn rõ ràng mới
đủ điều kiện để con người review production acceptance, không tự động accepted.
Hiện chưa có provider admitted hoặc dataset giá thật được validate, nên run bị
chặn bởi prerequisite và mọi strategy/forecast vẫn suppressed. Unit test offline
chỉ kiểm tra contract, không phải bằng chứng backtest hoặc alpha.
