# Research Economics Memo — acquisition portfolio, priced

*2026-07-16. Every major remaining acquisition scored on seven attributes.
"Alpha/eng-week" is the summary judgment: expected long-term contribution to
alpha-discovery rate per engineering week, given everything else we hold.
Scores are judgment made explicit — revise as probes teach us.*

## Scoring table

| Acquisition | Eng. effort | Maintenance | Quality/licensing risk | Families unlocked | Throughput Δ (verdicts/mo) | P(permanent infra) | **Alpha per eng-week** |
|---|---|---|---|---|---|---|---|
| **1. Earnings-event calendar** (filing metadata, no OCR) | **hours** | ~zero (daily capture already pulls the feed) | Low — exchange-official timestamps; one caveat: `Created` = filing time, occasionally lags document date | F5 core; F9 partial | +1 immediately (H-006 becomes runnable) | 1.0 | **Extreme** (near-zero denominator) |
| **2. Per-stock OHLCV + volume** (~50–100 names, 2012→) | 2–4 days | Low (forward capture via NGX snapshot exists; periodic backfill top-ups) | Medium — aggregator (conf 0.5): unknown adjustment policy, survivorship gaps, rate-limiting observed; personal-research use of a public site, no redistribution | F2, F4, F5 (with #1), F8, F9, F13 | +2–4 sustained | 0.95 | **Highest absolute** (moves the detection frontier — see pivot memo) |
| **3. OCR pipeline** (tesseract, scanned filings) | 1–2 days incl. accuracy tuning | Low (batch tool) | Medium — OCR errors on stamps/low-res scans; mitigated by anchor validation + template structure; Apache-2.0 license, local install (user approval pending) | Enabler for #4, #6 | indirect | 0.9 | High (an enabler, not an end) |
| **4. Dividend & corporate-action parser** (template extraction over text+OCR) | 2–3 days | Medium — template drift across years/registrars needs occasional re-tuning | Medium — extraction accuracy must be proven vs anchors before promotion (process exists) | F6; TR truth upgrading F2/F5/F13; dividend-change directions (first non-hindsight direction source) | +1–2 | 0.9 | High |
| **5. T-bill history** (CBN, 2012→) | 0.5–1 day | Low | Low — official rates; parsing effort only | None directly; **corrects rf across every existing and future verdict** (cross-cutting) | 0 direct; raises verdict *quality* | 1.0 | High (cheap, cross-cutting) |
| **6. Fundamentals extraction from results filings** (EPS, book value, ROE from 70k corpus post-OCR) | 2–4 weeks | Medium-high | High — statement formats vary wildly; IFRS restatements; heavy validation burden | New F14 (value/quality factors), earnings-surprise-vs-history for F5 | +1–2, later | 0.8 | Medium now, high later — sequenced after #3/#4 prove OCR quality |
| **7. Full 70k-filing text corpus** (archive all types) | days of background runtime, ~0 attention | Low | Low (archival only) | Substrate for future NLP/tone (F10+), governance (F9) | 0 now | 0.95 | Medium (cheap option on future families) |
| **8. Additional regulatory expansion** (SEC/NAICOM/PenCom deep curation) | weeks, manual | Medium | Low | Increments F1/F7 — families already tested-or-gated at current design power | ~0 near-term | 0.7 | **Low now** — revisit if an event-driven family validates |
| **9. FX parallel-market history** | unknown (sources vanished) | High fragility | **High — ethics/legal gate unresolved; do not acquire without review** | F7, F12 | +0–1 | 0.5 | Gated, not scored |
| **10. Broker research archive** | relationship-dependent | Medium | **High — licensing; written permission required** | F10 | +0–1 | 0.4 | Gated, not scored |
| 11. Membership/weights PIT (archival) | 1–2 weeks archival work | Low after backfill | Medium (archive density unknown) | F3; benchmark-truth for capacity | +0–1 | 0.8 | Medium — no longer top-3 after the per-stock pivot (universe now defined by filings, not index membership) |

## Ranking by expected long-term alpha-discovery contribution

1. **Per-stock OHLCV + volume** — the only item that moves the detection
   frontier; everything else multiplies against it.
2. **Earnings-event calendar** — best ratio in the portfolio; hours of work
   for the platform's first adequately-powered event study.
3. **OCR pipeline → 4. dividend/corp-action parser** — one program in two
   stages: TR truth + F6 + the first mechanical direction labels.
4. **T-bill history** — cheapest integrity upgrade; every Sharpe and
   viability judgment inherits it.
5. **Fundamentals extraction (F14)** — the next frontier after OCR proves
   out; likely the largest *later* item.
6. **70k corpus archive** — cheap optionality, run in background.
7. Membership PIT — demoted by the pivot; acquire opportunistically.
8. Regulatory expansion — parked pending an event-family validation.
9/10. Parallel FX & broker research — remain gated on your review.

## Note on execution order vs. ranking

The approved execution sequence (backfill → survivorship audit → earnings
calendar → OCR/corp-actions → H-006/H-007 preregs) interleaves the top four
items with their gating audits; ranking here is by long-term contribution,
and the two orderings are consistent — the audit sits between acquisition
and use because trustworthy verdicts, not datasets, are the product.
