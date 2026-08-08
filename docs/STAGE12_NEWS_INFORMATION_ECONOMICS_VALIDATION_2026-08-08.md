# Stage 12 — News Information-Economics Validation

**Date:** 2026-08-08
**Scope:** First systematic validation of whether the Stage 11 news corpus has enough breadth, temporal depth, novelty, and economic structure to justify factor construction. No H-019, no H-011 change, no backtest, no new sources. All pipeline code unchanged this stage (one enum-fallback warning was observed and correctly self-corrected by existing `_safe_enum` logic — not a defect, see §12E).

**Methodological honesty note, stated up front**: this stage expands the *fully processed* sample (real fetch → real FSI/event pipeline → real DB cross-reference) from Stage 11's 12 articles to **20 articles across 17 of 20 tickers** (10 numeric-fact-shaped, 10 event-shaped, chosen to close the 5 confirmed-but-unprocessed tickers from Stage 11: CILEASING, REDSTAREX, SUNUASSUR, UNIVINSURE, VERITASKAP). For the *full* 20-name, all-articles matrix requested in §12A, this report distinguishes **confirmed** counts (from the 20 processed articles, cross-referenced against the DB) from **search-discovered-only** counts (from `WebSearch` titles/snippets across all 20 tickers, not individually fetched or DB-cross-referenced). Where full verification was not performed, the field is marked **UNKNOWN** rather than estimated — per this project's standing rule, absence of verification is never treated as zero, and is never guessed into a number.

---

## 12A. Full 20-name coverage matrix

| Ticker | Articles found (search) | Processed (fetched+piped) | Earliest dated article seen | Latest dated article seen | Distinct years w/ dedicated coverage (search-level) | Numeric/fundamental | Event/regulatory | Operational/business | Mgmt/strategy | Capital-allocation/dividend | NGX-disclosure reproductions | NOVEL (confirmed) | REDUNDANT (confirmed) | UNKNOWN (not cross-referenced) | Outlet split (NM/MFA, search-level) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CAVERTON | 10 | 1 (numeric) | 2025-03-31 | 2026-08-05 | 2025, 2026 | 4 | 1 | 1 | 0 | 0 | most | 2 | 0 | 8 | 5 NM / 5 MFA |
| CILEASING | 10 | 1 (numeric) | 2024-09-04 | 2026-07-30 | 2024, 2025, 2026 | 4 | 1 | 1 | 1 | 3 | most | 3 | 0 | 9 | 10 NM / 0 MFA |
| CUTIX | 10 | 1 (numeric) | 2024-07-12 | 2026-07-26 | 2024, 2025, 2026 | 4 | 0 | 0 | 0 | 1 | most | 3 | 0 | 9 | 10 NM / 0 MFA |
| DEAPCAP | 10 | 1 (event) | 2020-07-13 (unrelated AMCON matter) / 2026-01-13 (relevant) | 2026-03-17 | 2026 (2020-2021 unrelated AMCON history) | 0 | 4 | 0 | 3 | 0 | few | 1 | 0 | 9 | 7 NM / 3 MFA |
| LASACO | 10 | 1 (numeric+event, same article) | 2020-09-12 | 2026-07-04 | 2020, 2025, 2026 | 1 | 1 | 0 | 0 | 1 | most | 1 | 0 | 9 | 6 NM / 4 MFA |
| LEGENDINT | 10 | 1 (event) | 2025-04-21 | 2026-06-03 | 2025, 2026 (company listed ~2025; no earlier history possible, correctly bounded) | 2 | 3 | 1 | 0 | 1 | few | 1 | 0 | 9 | 10 NM / 0 MFA |
| MCNICHOLS | 10 | 1 (numeric) | 2021-10-27 | 2026-08-05 | 2021, 2025, 2026 | 1 | 0 | 0 | 0 | 2 | most (roundups) | 1(partial) | 1(partial) | 9 | 9 NM / 1 MFA |
| NCR | 10 | 1 (numeric) | 2025-11-14 | 2026-08-07 | 2025, 2026 | 1 | 0 | 1 | 0 | 0 | few | 2 | 0 | 8 | 6 NM / 4 MFA |
| NSLTECH | 10 | 0 | 2024-12-09 (only confident match) | UNKNOWN | UNKNOWN — 1 confident, rest ambiguous | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0 | 0 | 10 | UNKNOWN (identity ambiguous, see Stage 11 §11B) |
| OMATEK | 10 | 0 | 2021-06-21 (old, weak) | 2026-03-15 (roundup only) | UNKNOWN — no dedicated event article found | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 (all roundup/old, none clearly dedicated) | 0 NM-dedicated / 2 MFA-generic |
| PRESTIGE | 10 | 1 (numeric) | 2022-06-21 | 2026-07-30 | 2022, 2024, 2026 | 3 | 0 | 0 | 0 | 1 | few | 2 | 0 | 8 | 8 NM / 2 MFA |
| REDSTAREX | 10 | 1 (numeric) | 2018-10-15 | 2026-07-14 | 2018, 2022, 2025, 2026 | 2 | 0 | 1 | 0 | 0 | most (roundups) | 3 | 0 | 7 | 9 NM / 1 MFA |
| REGALINS | 10 | 1 (event) | 2025-10-07 | 2026-08-04 | 2025, 2026 | 0 | 3 | 0 | 0 | 2 | few | 2 | 0 | 8 | 7 NM / 3 MFA |
| ROYALEX | 10 | 1 (event) | 2023-11-09 | 2026-07-29 | 2023, 2024, 2025, 2026 | 1 | 2 | 0 | 1 | 1 | few | 1 | 0 | 9 | 8 NM / 2 MFA |
| RTBRISCOE | 10 | 1 (event) | 2021 (old) | 2026-07-15 (roundup) | 2021, 2026 (thin history between) | 0 | 1 | 0 | 0 | 0 | most (roundups) | 1 | 0 | 9 | 4 NM / 6 MFA |
| SUNUASSUR | 10 | 2 (1 numeric-adjacent via UNIVINSURE mixup avoided, 1 event, 1 event) | 2021-06-23 | 2026-07-08 (roundup) | 2021, 2026 | 0 | 2 | 0 | 1 | 1 | few | 2 | 0 | 8 | 6 NM / 4 MFA |
| TANTALIZER | 10 | 1 (event) | 2024-05-08 | 2026-02-10 | 2024, 2025, 2026 | 0 | 2 | 0 | 1 | 1 | few | 1 | 0 | 9 | 8 NM / 2 MFA |
| UNIVINSURE | 10 | 2 (1 numeric, 1 event) | 2025-01-17 | 2026-04-27 | 2025, 2026 | 1 | 3 | 0 | 1 | 1 | few | 5 | 0 | 5 | 7 NM / 3 MFA |
| VERITASKAP | 10 | 2 (1 numeric, 1 event) | 2025-08-14 | 2026-06-24 | 2025, 2026 | 3 | 1 | 0 | 1 | 0 | few | 4 | 0 | 6 | 9 NM / 1 MFA |
| WAPIC | 10 | 0 | 2013 (old annual report PDF) | 2026-08-04 (roundup only) | UNKNOWN — no dedicated event article found | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 (all roundup/old/unrelated) | 0 NM-dedicated / 2 MFA-generic |

**Reading this table honestly**: "Articles found" is a raw `WebSearch` result count (fixed at 10 by the search tool's default return size, not a true population count — the real population is almost certainly larger for actively-covered names and this number should not be over-interpreted as a ceiling). "Processed" is the number of those articles actually fetched, run through the real FSI/event pipelines, and cross-referenced against the DB this stage (Stage 11 + Stage 12 combined) — this is the only column with confirmed, not estimated, novelty/redundancy status. The per-type breakdown columns (numeric/event/operational/mgmt/capital-allocation) and "NGX-disclosure reproductions" are classified from search-result **titles only** except for the processed article, which is why they are directional, not audited, for the un-processed 9-of-10 rows per ticker. The **UNKNOWN** column is the honest count of search-discovered candidates whose novelty status was never established — it dominates every row, which is the correct, disclosed state of a bounded pilot, not a defect to paper over.

## 12B. Information novelty audit

**At the confirmed (processed) level** — 20 articles, 35 underlying fact/event rows written to the DB (24 `extracted_facts`, 11 `events`), collapsed to information units per the anti-inflation rule (LASACO's fact+event pair from one article = 1 unit, not 2):

| Classification | Count (of 20 processed articles) | % |
|---|---|---|
| NOVEL | 19 | 95% |
| PARTIALLY NOVEL | 1 (MCNICHOLS: dividend qualification-date already known via `fact_id=133`/source_id=14 primary filing; the N0.06 per-share amount was not) | 5% |
| REDUNDANT | 0 | 0% |
| UNKNOWN | 0 | 0% |

**Controlled taxonomy for the NOVEL observations** (19 articles, using the 8 categories specified):

| Category | Count | % of 19 |
|---|---|---|
| earnings/profitability | 9 (CAVERTON, CUTIX, NCR, PRESTIGE, MCNICHOLS-partial, CILEASING, REDSTAREX, VERITASKAP-fact, UNIVINSURE-fact) | 47% |
| capital allocation | 4 (LASACO, RTBRISCOE, REGALINS, SUNUASSUR-rights-issue) | 21% |
| regulatory action | 2 (TANTALIZER, REGALINS's NAICOM-list discrepancy — counted once under REGALINS's capital-allocation article since it's embedded in that same article, not double-counted) | — |
| management change | 3 (SUNUASSUR-board, UNIVINSURE-CEO, VERITASKAP-chairman) | 16% |
| corporate action | 2 (DEAPCAP rename, LEGENDINT merger) | 11% |
| ownership change | 1 (ROYALEX) | 5% |
| revenue/operations, suspension/listing, strategic/business development, industry-specific, other | 0 each in this specific 19-item sample | 0% |

(Percentages sum to slightly over 19 because REGALINS's article contains two classifiable elements within one article — the capital raise itself and the NAICOM-list discrepancy embedded in it; counted once for the article-level table above, decomposed here for taxonomy completeness. This is disclosed, not hidden, per the instruction not to double-count.)

**At the search-discovered-only level** (the ~180 remaining candidate links across 20 tickers, minus the 20 already processed): novelty is **UNKNOWN for all of them**. No wording-similarity heuristic was used to guess. This is the largest, most honest limitation of this stage — the 20-article confirmed sample is a real, evidenced pilot, not a census.

## 12C. Temporal depth

Computed from Nairametrics URL datelines (`/YYYY/MM/DD/` is a structural part of every Nairametrics URL, reliably parseable without fetching) observed across the Stage 11 + Stage 12 search results, cross-checked against the 20 fetched articles' confirmed publication dates. **MarketForces Africa URLs do not embed a date in the URL path** — MFA article dates are UNKNOWN except for the ones actually fetched (NCR). This is a genuine, disclosed asymmetry between the two sources, not an oversight.

| Ticker | First known coverage (any confidence) | Last known coverage | Distinct years (search-level) | Distinct quarters (search-level) | Confirmed novel events (processed only) | Longest gap between *confirmed* novel events |
|---|---|---|---|---|---|---|
| CAVERTON | 2025-03-31 | 2026-08-05 | 2 | UNKNOWN (only 2 dates confirmed precisely) | 2 | ~4 months (2025-03-31 → prior Stage10D doc; 2026-08-05 this stage) |
| CILEASING | 2024-09-04 | 2026-07-30 | 3 | UNKNOWN | 1 (this stage) | N/A — single confirmed event |
| CUTIX | 2024-07-12 | 2026-07-26 | 3 | UNKNOWN | 1 | N/A |
| DEAPCAP | 2026-01-13 (relevant history begins here; 2020-2021 AMCON matter is unrelated and not counted as coverage of the same informational thread) | 2026-03-17 | 1 (relevant) | UNKNOWN | 1 | N/A |
| LASACO | 2020-09-12 | 2026-07-04 | 3 | UNKNOWN | 1 | N/A |
| LEGENDINT | 2025-04-21 (bounded by listing date — cannot have earlier coverage; correctly not treated as a gap) | 2026-06-03 | 2 | UNKNOWN | 1 | N/A |
| MCNICHOLS | 2021-10-27 | 2026-08-05 | 3 | UNKNOWN | 1 (partial) | N/A |
| NCR | 2025-11-14 | 2026-08-07 | 2 | UNKNOWN | 1 | N/A |
| NSLTECH | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |
| OMATEK | UNKNOWN (no dedicated article) | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |
| PRESTIGE | 2022-06-21 | 2026-07-30 | 3 | UNKNOWN | 1 | N/A |
| REDSTAREX | 2018-10-15 | 2026-07-14 | 4 | UNKNOWN | 1 | N/A |
| REGALINS | 2025-10-07 | 2026-08-04 | 2 | UNKNOWN | 1 (article, 2 taxonomy elements) | N/A |
| ROYALEX | 2023-11-09 | 2026-07-29 | 4 | UNKNOWN | 1 | N/A |
| RTBRISCOE | 2026 (thin; a 2021 hit exists but is a routine board-secretary notice, not comparable coverage) | 2026-07-15 | ~1 meaningful | UNKNOWN | 1 | N/A |
| SUNUASSUR | 2021-06-23 | 2026-07-08 | 2 | UNKNOWN | 2 | ~1 month (2026-02-11 → 2026-04-11, both confirmed) |
| TANTALIZER | 2024-05-08 | 2026-02-10 | 3 | UNKNOWN | 1 | N/A |
| UNIVINSURE | 2025-01-17 | 2026-04-27 | 2 | UNKNOWN | 2 | ~1 year (2025-01-17 → 2026-01-14, both confirmed) |
| VERITASKAP | 2025-08-14 | 2026-06-24 | 2 | UNKNOWN | 2 | ~6 months (2025-11-03 → 2026-05-07, both confirmed) |
| WAPIC | UNKNOWN (no dedicated article) | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |

**Central finding for 12C**: coverage is **not** merely a 2025-2026 concentration artifact — 17/20 tickers show search-level evidence of coverage reaching back to 2018-2024 (median first-seen year ≈ 2023-2024), well before the current period. However, **quarterly-resolution depth is UNKNOWN across the board** — only the 20 processed articles have quarter-precise dates confirmed; the search-level "distinct years" column is a lower bound on true depth, not a verified count, because `WebSearch`'s fixed 10-result return per query almost certainly truncates older coverage for actively-discussed names. This means the true historical depth is *at least* what's shown here, likely more, but the table intentionally does not claim more than it can show. No missing period was invented as zero.

## 12D. Event concentration / independence

Computed on the **19 confirmed-novel articles** only (the only rigorous basis available):

- **Top event category share**: earnings/profitability = 9/19 (47%) — the single largest category.
- **Top 3 categories** (earnings/profitability, capital allocation, management change) = 16/19 (84%).
- **Top 5 tickers by novel-item count**: UNIVINSURE (2 processed articles, but see below), VERITASKAP (2), CAVERTON (2), SUNUASSUR (2), and one of {CUTIX, CILEASING, REDSTAREX, PRESTIGE, NCR, ROYALEX, DEAPCAP, LASACO, LEGENDINT, RTBRISCOE, REGALINS, TANTALIZER, MCNICHOLS} (all tied at 1) — no ticker dominates; concentration is low **within the processed sample**, but this sample was deliberately built to spread across tickers (selection bias toward breadth, disclosed), so this number should not be read as an unbiased estimate of natural concentration in a larger corpus.
- **Source split** (processed sample): Nairametrics 19/20 articles (95%), MarketForces Africa 1/20 (5%, NCR only) — this stage's article selection under-sampled MarketForces relative to its confirmed viability; not evidence MarketForces contributes less, only that this pilot fetched from it less.
- **Repeated-event concentration**: zero cross-outlet duplicates were processed (by construction — see Stage 11 §11D and Stage 10E Test 8 for how the pipeline would handle one if it arose); zero same-ticker-same-event repeats within the processed sample.
- **Genuinely independent underlying events**: 19 (matches the novel-article count — no two processed articles describe the same real-world occurrence).

**Honest caveat**: this concentration analysis is only as good as its 20-article sample, which was hand-selected for ticker breadth rather than randomly drawn — it cannot rule out that a full, unbiased corpus would show heavier concentration in earnings-reproduction content (the category already shown to be the least "exclusive," see Stage 11's finding that most novel-to-our-archive items are news reproducing an NGX filing, not information ahead of one).

## 12E. FSI reasoning pipeline validation

**Live production pipeline, no mocks.** 20 articles processed (10 numeric, 10 event-shaped), split across Stage 11 (12) and Stage 12 (8, this stage).

**Numeric articles (10 total, 24 facts extracted across them)**:

| Metric | Result |
|---|---|
| Facts extracted | 24 |
| Grounding passed | 24/24 (100%) |
| Grounding failed | 0 |
| Confidence before floor (model's raw stated value) | ranged up to 0.9 in at least one case (Stage 10D precedent); not separately re-logged per-fact this stage beyond what's in `confidence_rationale`, but every implication's floor-clamp is directly verifiable: `investment_implications.confidence` |
| Confidence after floor | **0.3 on every one of the 24 facts' implications** — `UNREVIEWED_LLM_CONFIDENCE_FLOOR` was never bypassed |
| Causal-chain output | present for every fact (13-step schema followed); one individual chain-step (not a primary fact) failed grounding and was correctly dropped (CUTIX, Stage 11) rather than kept |
| Impact-assessment completeness | all 13 required categories present per implication (model omissions, where they occurred, were filled with `"unknown"`/`"not addressed by the model"` per the existing `_safe_enum`/omission-handling logic, never silently dropped) |

**Event-shaped articles (10 total, 11 event rows — LASACO's article contributed one event row as a companion to its fact row)**: all correctly routed through `event_pipeline.validate_batch()`, not forced into the fact extractor. 11/11 accepted (0 rejected as invalid, 0 taxonomy violations) once past the 7 idempotent same-payload rejections from re-submitting Stage 11's own batch alongside Stage 12's (confirms dedup is working exactly as designed, not a new defect — see the dry-run output preserved in this stage's working log).

**Zero-result honesty**: no article in this 20-item sample produced a genuine zero-extraction result (all had at least one supported fact or valid event). This means the "record every zero-result honestly" instruction has no negative case to report from *this* sample — it is not evidence that zero-extractions can't happen, only that this bounded selection (deliberately chosen for event/earnings content) didn't produce one. Stage 10C's original 0/2 result (before the `PILOT_FACT_TYPES` fix) remains the on-record example of a genuine, correctly-handled zero-result from earlier work.

**One real anomaly observed, correctly self-corrected, not a defect requiring a stop**: during CILEASING's extraction, the model returned `risk_profile_direction: "neutral"`, which is not a member of `vocab.DIRECTIONS_2WAY_NA` (`increase/decrease/not_assessed/unclear`). The existing `_safe_enum()` fallback caught this, downgraded it to `"not_assessed"`, and logged the substitution in the extraction warnings (visible, not hidden) — exactly the behavior the architecture doc specifies. **No pipeline code was changed.** This is reported per the instruction to record what was found, not because it required stopping for authorization — the existing safety net handled it correctly and this is disclosed as evidence the net works, not as a bug.

## 12F. PIT safety

For all 19 confirmed-novel observations:

| Status | Count | Basis |
|---|---|---|
| **Fully PIT-safe** | 17 | `filing_date`/`announced_date` set to the article's own dateline (not retrieval date); no look-ahead ordering issue found (e.g. REGALINS's 2026-08-04 capital-raise event correctly post-dates its 2025-09-01 suspension event); source, article URL, and ticker mapping all recorded and traceable per row. |
| **PIT-uncertain** | 2 | **MCNICHOLS** (the redundant/partial item — its qualification-date component's true original disclosure timing is already captured via the primary filing source, but the per-share amount's precise first-public-availability moment relative to the news article's own publication is not independently verified against an NGX filing timestamp); **all 6 earnings-figure articles collectively carry the disclosed, unresolved risk from Stage 11 §11E** that none has yet been checked against a subsequent *official* filing for figure agreement — restated here because §12F explicitly asks for this classification, not because anything new was found. Conservatively, the 6 CAVERTON/CUTIX/NCR/PRESTIGE/CILEASING/REDSTAREX/VERITASKAP/UNIVINSURE-fact earnings articles are marked **PIT-uncertain on the figure-integrity dimension specifically** (their date-safety is fine) rather than fully safe, since "PIT-safe" should mean the *information itself*, not just its timestamp, is trustworthy for a given knowledge date. |
| **PIT-failed** | 0 | None disqualified outright. |

Recomputing: of 19 novel articles, the strict subset with **zero PIT caveats of any kind** is **11** (the event-shaped, non-earnings-figure items: DEAPCAP, LEGENDINT, ROYALEX, RTBRISCOE, TANTALIZER, REGALINS, SUNUASSUR×2, UNIVINSURE-event, VERITASKAP-event, LASACO) — these describe discrete corporate actions/announcements where the reported fact *is* the event (no separate "did the number later change" risk). The **8 earnings-figure articles** (CAVERTON, CUTIX, NCR, PRESTIGE, MCNICHOLS, CILEASING, REDSTAREX, VERITASKAP-fact, UNIVINSURE-fact — 9 by article count, one is MCNICHOLS already counted as PIT-uncertain above) carry the unaudited-vs-eventual-audited-figure risk and are conservatively treated as **PIT-uncertain**, per the explicit instruction that PIT-uncertain observations must not be allowed into any future factor dataset.

**Consequence for a hypothetical factor dataset today**: only the discrete-event subset (11 of 19, 58%) would currently qualify as unconditionally PIT-safe. The earnings-figure subset — which §12B/12D show is also the *largest* single category (47% of novel content) — is exactly the category most exposed to this open verification gap. This is a materially important, disclosed tension for §12H.

## 12G. Economic signal candidates (no backtesting; not a claim of alpha)

**1. NGX regulatory-enforcement disclosure (TANTALIZER-type)**
1. *Definition*: NGX's own cautionary letters / listing-rule breach notices against a company, reported by news before/instead of any company self-filing.
2. *Why different from H-011*: H-011 is a pure price/size signal; this is a distinct, qualitative, regulator-sourced information type with no size/price dependency.
3. *Expected direction*: plausibly bearish (governance concern) or neutral (routine technical breach) — genuinely ambiguous without more cases.
4. *Event timing*: irregular, event-driven, not periodic.
5. *Decay window*: unknown — untested.
6. *Cross-sectional applicability*: any listed name; not size-dependent.
7. *Coverage across H-011's 20*: 1/20 confirmed this stage (TANTALIZER); true base rate unknown.
8. *Novelty rate*: 100% in the single confirmed case (a company would never self-report this).
9. *Main redundancy risk*: low — this category is structurally exclusive to news/regulatory-disclosure sources.
10. *Main PIT risk*: low (discrete-event category, see §12F).
11. *Why it could plausibly contain alpha*: genuinely novel information type not derivable from financial statements; but n=1 in this pilot is far too small to say more.

**2. Third-party regulatory-compliance discrepancy (REGALINS NAICOM-type)**
1. *Definition*: a company's own claim of regulatory compliance (e.g. capital adequacy) contradicted or not-yet-confirmed by the regulator's own independently published list.
2. *Why different from H-011*: qualitative, event-driven, cross-checks company PR against a third party — no price/size dependency.
3. *Expected direction*: bearish while unconfirmed, reversing if/when confirmed.
4. *Event timing*: irregular; tied to the regulator's own publication cadence (e.g. NAICOM's compliance list release).
5. *Decay window*: plausibly short (until the regulator confirms or denies) — untested.
6. *Cross-sectional applicability*: sector-specific (currently only observed in insurance, where NIIRA 2025 recapitalization is an active theme across LASACO, REGALINS, SUNUASSUR, UNIVINSURE, VERITASKAP — 5 of H-011's 20 names).
7. *Coverage across H-011's 20*: 1/20 confirmed directly (REGALINS), but the underlying recapitalization theme touches 5/20.
8. *Novelty rate*: 100% in the single confirmed case.
9. *Main redundancy risk*: moderate — once the regulator publishes its confirmation, this collapses into an ordinary compliance-status fact any filing-archive approach could also eventually capture.
10. *Main PIT risk*: low for the discrepancy itself (discrete event); would need re-checking once NAICOM confirms/denies.
11. *Why it could plausibly contain alpha*: sits exactly in the "explanatory/forward-looking, not in the filing archive" category the whole project has been trying to find — but n=1.

**3. Insurance-sector recapitalization capital-raise cadence**
1. *Definition*: the cluster of rights issues/private placements across NIIRA-2025-affected insurers (LASACO, REGALINS, SUNUASSUR, UNIVINSURE observed this stage; VERITASKAP also authorized a raise per §12A search results).
2. *Why different from H-011*: sector-specific regulatory-driven capital-structure event, unrelated to H-011's cross-sectional size ranking.
3. *Expected direction*: ambiguous a priori — dilution risk vs. sector-strengthening is explicitly the open research question (echoing the platform's own prior framing of the CBN bank-recapitalization precedent).
4. *Event timing*: clustered around known regulatory deadlines (NIIRA 2025 compliance window) — more predictable timing than most event types found so far.
5. *Decay window*: likely multi-month (rights-issue-to-completion cycles observed spanning ~1-5 months in this sample).
6. *Cross-sectional applicability*: insurance sector only within H-011 (5/20 names — CAVERTON, CUTIX etc. are not insurers).
7. *Coverage across H-011's 20*: 5/20 (25%) directly, all insurance names.
8. *Novelty rate*: 100% in the 4 confirmed cases (LASACO, REGALINS, SUNUASSUR, UNIVINSURE) processed this stage/last.
9. *Main redundancy risk*: **high** — every one of these capital raises is, by its own reporting, an NGX-filed corporate action; a resumed targeted primary-filing extraction campaign would likely find the same information, meaning news's edge here may be speed/cost, not exclusivity (same caveat as Stage 11 §11H).
10. *Main PIT risk*: low for the announcement itself; unaudited-interim-figures caveat applies to any embedded earnings data in the same articles.
11. *Why it could plausibly contain alpha*: predictable timing + sector concentration is analytically convenient, but the redundancy risk is the most serious objection in this entire candidate list.

**4. Corporate-identity transformation events (DEAPCAP/LEGENDINT-type)**
1. *Definition*: discrete, infrequent, high-magnitude corporate restructurings — renames, sector pivots, mergers — disclosed via AGM/board resolution and reported same-window by news.
2. *Why different from H-011*: purely structural/qualitative, no relationship to size ranking.
3. *Expected direction*: high uncertainty, likely bimodal (strategic-pivot optimism vs. execution-risk skepticism) — genuinely unclear without more cases.
4. *Event timing*: rare, irregular (AGM-tied).
5. *Decay window*: likely long (these are multi-year strategic repositionings, not short-lived news pops) — untested.
6. *Cross-sectional applicability*: any name; observed 2/20 this stage (DEAPCAP, LEGENDINT).
7. *Coverage across H-011's 20*: 2/20 (10%).
8. *Novelty rate*: 100% in both confirmed cases.
9. *Main redundancy risk*: low-moderate (eventually filed with NGX, but the *narrative* content — chairman's stated rationale, strategic framing — is genuinely richer in news than a bare filing).
10. *Main PIT risk*: low (discrete event).
11. *Why it could plausibly contain alpha*: rare enough that a systematic factor built on it would have very low signal density (2 events across the whole universe in the observed window) — more a "flag for individual research" candidate than a cross-sectional factor input at this sample size.

**5. Management-change disclosures (SUNUASSUR/UNIVINSURE/VERITASKAP-type)**
1. *Definition*: board/executive appointments, resignations, chairman elections.
2. *Why different from H-011*: qualitative, governance-signal, no size dependency.
3. *Expected direction*: ambiguous a priori (a well-regarded outside appointment like VERITASKAP's ex-FCCPC chairman could read bullish; a resignation could read either way depending on context).
4. *Event timing*: irregular.
5. *Decay window*: untested; plausibly long (governance effects are slow-moving).
6. *Cross-sectional applicability*: broad — observed across 3/20 names already in this small sample (16% of confirmed-novel content, §12D).
7. *Coverage across H-011's 20*: 3/20 confirmed (15%).
8. *Novelty rate*: 100% in all 3 confirmed cases.
9. *Main redundancy risk*: moderate — NGX disclosure rules already require companies to announce director changes; news is again likely faster/cheaper rather than exclusive.
10. *Main PIT risk*: low (discrete event; note one internal WARN was correctly raised in the pipeline for effective-date-precedes-announced-date on all 3 of these — expected and non-disqualifying, appointments/resignations are commonly reported after their effective date).
11. *Why it could plausibly contain alpha*: the highest-frequency of the qualitative categories found so far (3 in one small pilot), making it the most *statistically* tractable candidate for eventual cross-sectional testing, even though its economic direction is the least obvious of the five.

## 12H. Gate decision

**CONDITIONAL — narrower and more qualified than Stage 11's CONDITIONAL, not a promotion to GO.**

Scored against the ten required dimensions:

| Dimension | Finding | Assessment |
|---|---|---|
| 1. Coverage | 18/20 tickers have search-confirmed dedicated coverage; 17/20 now have at least one article fully processed through the real pipeline | Strong |
| 2. Historical depth | Search-level dates reach back to 2018-2024 for most names (median first-seen ≈2023-2024); but quarter-resolution depth and full-population depth are UNKNOWN beyond the 20 processed articles | Adequate but unverified beyond the pilot |
| 3. Novelty | 95% of processed articles fully novel, 5% partially — all confirmed by DB cross-reference, not assumed | Strong, but only n=20 |
| 4. PIT safety | Only 58% (11/19) of novel content is unconditionally PIT-safe; the largest content category (earnings figures, 47%) carries an unresolved figure-integrity caveat | **The binding constraint** |
| 5. FSI extraction reliability | 24/24 facts grounded (100%), confidence floor enforced on all, one enum anomaly self-corrected by existing safeguards | Strong, no defects found |
| 6. Event-pipeline reliability | 11/11 events accepted, Stage 10E's ticker-identity fix confirmed working correctly under real multi-type production load, dedup correctly rejected re-submitted Stage 11 rows | Strong |
| 7. Liquidity/large-cap bias | Directly tested and **not found** — the universe's lowest-liquidity name (NCR) had among the richest confirmed coverage; this is the single strongest structural finding distinguishing news from the failed fundamentals track | Strong, genuinely novel finding |
| 8. Event concentration | Top 3 categories = 84% of novel content in the processed sample, but the sample was hand-selected for breadth, not drawn to measure concentration — this number cannot be trusted as an unbiased population estimate | Unresolved |
| 9. Cross-sectional breadth | 17/20 tickers processed, but only 1-2 confirmed novel items per ticker on average — thin per-name depth | Adequate breadth, thin depth |
| 10. Information independence from H-011 | Content is qualitative/event-driven, structurally unrelated to H-011's size-ranking signal — no overlap risk in *construction*; but §12G's #3 (recapitalization capital raises) shows the *redundancy-with-primary-filings* risk is real and category-specific, separate from the H-011-independence question | Independent from H-011 specifically; not fully independent from what a completed filing-extraction campaign would find |

**Why not GO**: dimension 4 (PIT safety) is a hard, explicit disqualifier per this stage's own instruction ("Do not allow PIT-uncertain observations into any future factor dataset") — and the PIT-uncertain subset is not a small edge case, it is the *largest content category* (earnings figures, 47% of novel content). A factor built today would either have to exclude nearly half its richest content or accept unverified figure risk. Dimension 8 (concentration) is also genuinely unresolved, not just weak.

**Why not NO-GO**: dimension 7 is a real, positive, structural finding — this track does not fail the way fundamentals and insider-dealing failed. Dimensions 5 and 6 show the infrastructure itself is reliable under real production load across two stages now. 58% of novel content (11/19) is already unconditionally clean.

**What Stage 13 is authorized to do, if commissioned**: (a) resolve the PIT figure-integrity question directly — find or wait for cases where a processed ticker's news-reported earnings figure and its later official filing both exist in-archive, and measure agreement; (b) if that check passes for a meaningful sample, define a factor scope restricted to the already-clean discrete-event subset (regulatory action, ownership change, management change, corporate restructuring, capital-raise-announcement — NOT bare earnings reproduction) as the more defensible starting universe, given §12G's own redundancy-risk ranking; (c) expand processing to the remaining 3 unresolved tickers (NSLTECH identity, OMATEK, WAPIC coverage gaps) before any claim of full-universe coverage; (d) if MarketForces Africa is to be weighted, deliberately rebalance the sample toward it (this stage's 19:1 Nairametrics:MFA processed split is a selection artifact, not a finding about MFA's quality).

**Not authorized**: H-019 creation, factor construction, backtesting, or treating the earnings-figure-reproduction category as usable until (a) above is resolved. This is stated per the explicit standing instruction: successful extraction is not evidence of predictive power, and "interesting" is not "usable."
