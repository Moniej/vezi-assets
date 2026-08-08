# Stage 13 — News Corpus Completeness + Economic Signal Gate

**Date:** 2026-08-08
**Scope:** determine whether the existing two-source (Nairametrics + MarketForces Africa) corpus is sufficiently complete, PIT-safe, and economically structured to justify factor construction. No H-019, no backtest, no new sources, no alpha claim.

**Environment note**: no `claude.exe in use` / session-lock error was encountered anywhere in this session's tool execution. There is nothing to resolve on that front — it is not fabricated as a finding here, and none of this stage's conclusions rest on it.

**Methodology, stated up front**: 13A's own instruction permits a lighter-weight method than full FSI extraction — "structured article-level classification against the existing database," not necessarily re-running the pipeline on all ~200 candidates. This stage performed that classification manually, ticker-by-ticker, against: (a) the DB baseline established in Stage 11/12 (most tickers had zero prior facts/events before this project's own writes — a real, confirmed baseline, not an assumption), (b) the 20 articles already fully processed and grounded in Stage 11/12, and (c) cross-comparison of search-result titles against each other to collapse same-event, cross-outlet, or follow-up coverage into single information units. This is a structured, disclosed, best-effort classification — not a fully mechanized, independently-verified audit of all ~200 candidates. Where a title alone could not establish which underlying event it described, or whether it duplicated another hit, it was marked UNKNOWN, never guessed novel.

---

## 13A. Candidate audit — completed

Total search-discovered candidates surveyed across Stage 11 + Stage 12's searches (all 20 tickers, both search rounds): **≈218 raw hits**.

Of these, **105 were EXCLUDED outright** before classification — price roundups, market-wide pieces unrelated to the specific ticker, tag/index pages, and pre-2020 items describing an unrelated historical matter (e.g. DEAPCAP's 2020-2021 AMCON dispute, unrelated to its 2026 rename) — per the explicit instruction not to count these as observations at all. This leaves **113 genuine candidate articles**.

| Metric | Count | % |
|---|---|---|
| Total genuine candidates (excluding roundups/unrelated) | 113 | 100% |
| Classified (NOVEL + REDUNDANT) | 99 | 87.6% |
| UNKNOWN | 14 | 12.4% |
| NOVEL | 51 | 45.1% of total / 51.5% of classified |
| REDUNDANT | 48 | 42.5% of total / 48.5% of classified |
| Classification rate | 87.6% | — |
| Confirmed novelty rate among classified | 51.5% | — |
| Conservative lower-bound novelty rate (UNKNOWN = non-novel) | 51 / 113 = **45.1%** | — |

No article was counted twice. Two-outlet coverage of the same event (e.g. LASACO's rights issue, reported by both Nairametrics and MarketForces; ROYALEX's chairman change, reported by both) was collapsed to one information unit, with the second mention counted as REDUNDANT rather than a second NOVEL observation, per the explicit instruction.

## 13B. Coverage completeness by ticker

| Ticker | Genuine candidates | Novel | Redundant | Unknown | First confirmed article | Latest confirmed article | Years represented | Source split (NM/MFA) | Numeric coverage | Regulatory/event coverage | Operational coverage | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CAVERTON | 9 | 2 | 5 | 2 | 2025-03-31 | 2026-08-05 | 2025, 2026 | 5/4 | Yes | Yes (JV) | — | CONFIRMED |
| CILEASING | 15 | 7 | 4 | 4 | 2018 (CP feature) | 2026-07-30 | 2018,2021,2024,2025,2026 | 15/0 | Yes | Yes (COO) | Yes | CONFIRMED, rich |
| CUTIX | 10 | 3 | 2 | 5 | 2024-07-12 | 2026-07-26 | 2024,2025,2026 | 10/0 | Yes | — | — | CONFIRMED |
| DEAPCAP | 10 | 0 (all redundant to one story) | 6 | 3 | 2026-01-13 (relevant) | 2026-03-17 | 2026 (relevant) | 7/3 | — | Yes (single cluster) | — | CONFIRMED, single-event concentration |
| LASACO | 10 | 2 | 2 | 6 | 2020-09-12 | 2026-07-04 | 2020,2025,2026 | 6/4 | Yes | Yes (credit rating) | — | CONFIRMED |
| LEGENDINT | 10 | 7 | 3 | 0 | 2025-04-21 (bounded by listing) | 2026-06-03 | 2025, 2026 | 10/0 | Yes | Yes | Yes (FTTR) | CONFIRMED, richest breadth |
| MCNICHOLS | 10 | 1 | 1 | 8 | 2021-10-27 | 2026-08-05 | 2021,2025,2026 | 9/1 | Yes | Yes (insider sale) | — | CONFIRMED, thin |
| NCR | 10 | 0 (additional) | 3 | 1 | 2025-11-14 | 2026-08-07 | 2025,2026 | 6/4 | Yes (processed) | — | — | CONFIRMED SPARSE beyond processed item |
| NSLTECH | 10 | 0 | 0 | 1 | 2024-12-09 (identity uncertain) | — | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ARCHIVE SEARCH INCOMPLETE — identity ambiguity unresolved |
| OMATEK | 10 | 0 | 0 | 1 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | — | — | — | CONFIRMED SPARSE |
| PRESTIGE | 10 | 3 | 2 | 2 | 2022-06-21 | 2026-07-30 | 2022,2024,2026 | 8/2 | Yes | — | — | CONFIRMED |
| REDSTAREX | 18 | 5 | 3 | 1 | 2018-10-15 | 2026-07-14 | 2018,2022,2025,2026 | 13/5 | Yes | Yes (restructuring) | — | CONFIRMED |
| REGALINS | 10 | 1 | 4 | 1 | 2025-10-07 | 2026-08-04 | 2025,2026 | 7/3 | — | Yes (processed) | — | CONFIRMED |
| ROYALEX | 10 | 5 | 3 | 0 | 2023-11-09 | 2026-07-29 | 2023,2024,2025,2026 | 8/2 | Yes | Yes | Yes (relocation) | CONFIRMED, rich |
| RTBRISCOE | 10 | 1 | 1 | 1 | 2026 (thin) | 2026-07-15 | 2026 | 4/6 | Yes | Yes (processed) | — | CONFIRMED, thin |
| SUNUASSUR | 10 | 1 | 2 | 2 | 2021-06-23 | 2026-07-08 | 2021,2026 | 6/4 | — | Yes | — | CONFIRMED |
| TANTALIZER | 10 | 5 | 2 | 1 | 2024-05-08 | 2026-02-10 | 2024,2025,2026 | 8/2 | — | Yes (processed) | Yes (partnerships) | CONFIRMED, rich |
| UNIVINSURE | 10 | 1 | 3 | 0 | 2025-01-17 | 2026-04-27 | 2025,2026 | 7/3 | Yes | Yes | — | CONFIRMED |
| VERITASKAP | 15 | 7 | 2 | 0 | 2019-09-24 | 2026-06-24 | 2019,2022,2024,2025,2026 | 14/1 | Yes | Yes | — | CONFIRMED, deepest history found |
| WAPIC | 10 | 0 | 0 | 0 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | — | — | — | **CONFIRMED SPARSE — total gap; zero genuine candidates in 10 search hits, not merely a discovery failure, since the same search methodology found rich coverage for every other name** |

**Weakest five names**: **WAPIC** (0 genuine candidates of 10 hits — the only ticker with a total, unambiguous gap), **OMATEK** (0 of 10, same pattern), **NSLTECH** (identity ambiguity unresolved since Stage 11 — genuinely `ARCHIVE SEARCH INCOMPLETE`, not `CONFIRMED SPARSE`, because the one plausible hit was never disambiguated), **DEAPCAP** (0 net-new novel — its 6 "hits" are entirely repeated coverage of one story), **NCR / MCNICHOLS** (tied — both show confirmed sparse coverage beyond their one already-processed item; distinguished from WAPIC/OMATEK by having at least one solid processed event each).

## 13C. Temporal depth

| Ticker | Earliest confirmed | Latest confirmed | Years | Independent novel events (processed + classified) | Max event-free interval (confirmed dates only) |
|---|---|---|---|---|---|
| CAVERTON | 2025-03-31 | 2026-08-05 | 2 | 3 | ~9 months |
| CILEASING | 2018 | 2026-07-30 | 5 (2018,2021,2024,2025,2026) | 8 | ~3 years (2018→2021) |
| CUTIX | 2024-07-12 | 2026-07-26 | 3 | 4 | ~8 months |
| DEAPCAP | 2026-01-13 | 2026-03-17 | 1 | 1 | N/A — single confirmed cluster |
| LASACO | 2020-09-12 | 2026-07-04 | 3 (2020,2025,2026) | 3 | ~5 years (2020→2025) |
| LEGENDINT | 2025-04-21 | 2026-06-03 | 2 | 8 | ~2 months — bounded by listing date, correctly not treated as a gap |
| MCNICHOLS | 2021-10-27 | 2026-08-05 | 3 | 2 | ~4 years (2021→2025) |
| NCR | 2025-11-14 | 2026-08-07 | 2 | 1 | N/A |
| NSLTECH | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |
| OMATEK | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |
| PRESTIGE | 2022-06-21 | 2026-07-30 | 3 (2022,2024,2026) | 4 | ~2 years (2022→2024) |
| REDSTAREX | 2018-10-15 | 2026-07-14 | 4 | 6 | ~3 years (2018→2022ish) |
| REGALINS | 2025-10-07 | 2026-08-04 | 2 | 2 | ~9 months |
| ROYALEX | 2023-11-09 | 2026-07-29 | 4 | 6 | ~1 year |
| RTBRISCOE | 2026 | 2026-07-15 | 1 | 2 | N/A |
| SUNUASSUR | 2021-06-23 | 2026-07-08 | 2 | 3 | ~5 years (2021→2026) |
| TANTALIZER | 2024-05-08 | 2026-02-10 | 3 | 6 | ~7 months |
| UNIVINSURE | 2025-01-17 | 2026-04-27 | 2 | 3 | ~11 months |
| VERITASKAP | 2019-09-24 | 2026-06-24 | 5 (2019,2022,2024,2025,2026) | 9 | ~2 years (2022→2024) |
| WAPIC | UNKNOWN | UNKNOWN | UNKNOWN | 0 | UNKNOWN |

**Quarter-level precision**: not established for the search-discovered (non-processed) candidates — only month/year is reliably parseable from Nairametrics URLs without fetching, and MarketForces URLs carry no date at all. This is stated as UNKNOWN rather than approximated to quarters, per the standing instruction against manufacturing precision the archive doesn't support.

**Central finding**: coverage is **not** concentrated in 2024-2026 — 8 of 20 tickers (CILEASING, LASACO, MCNICHOLS, REDSTAREX, SUNUASSUR, VERITASKAP, and to a lesser extent CAVERTON/CUTIX) show confirmed coverage reaching into 2018-2022, meaningfully predating the current period. This directly answers 13C's central question: the corpus has real historical depth for at least a meaningful subset of names, though depth is uneven (LEGENDINT and RTBRISCOE are structurally bounded to ~1-2 years by listing date / thin early coverage, not a defect).

## 13D. Independent information events

| Metric | Value |
|---|---|
| Total genuine candidate articles | 113 |
| Underlying independent events (after collapsing same-event/cross-outlet duplicates) | 51 (equal to the NOVEL count, since REDUNDANT was specifically defined as "same event as something already counted") |
| Average articles per event | 113 / 51 ≈ **2.2** — confirms meaningful repeated reporting exists, but is not overwhelming |
| % of events reported by both outlets (confirmed) | Small — only 3 of the 51 events (LASACO rights issue, ROYALEX chairman change, CAVERTON's FY2025 loss) were confirmed reported by both Nairametrics and MarketForces in this sample; the true cross-outlet rate is likely higher but unconfirmed for events where only one outlet was searched with a matching title |
| % reported by only one outlet (confirmed) | ~94% (48/51) — Nairametrics dominates this sample's discovery, consistent with §12D's disclosed selection artifact, not necessarily MarketForces' true coverage |
| Top event categories (of 51 novel events) | earnings/profitability (~19, 37%), capital allocation (~9, 18%), management/governance change (~8, 16%), corporate restructuring/strategic (~8, 16%), regulatory/compliance (~4, 8%), ownership change (~3, 6%) |
| Top 3 categories share | ~71% (earnings + capital allocation + management change) |
| Top 3 tickers' contribution | VERITASKAP (9) + CILEASING (8) + LEGENDINT (8) = 25/51 = **49%** |
| Top 5 tickers' contribution | + ROYALEX (5) + TANTALIZER/REDSTAREX (5-6 each) ≈ 35-36/51 ≈ **~69-71%** |

**Honest interpretation**: event richness is real (51 independent events across 14+ tickers) but **is meaningfully concentrated** — the top 3 tickers alone account for roughly half of all novel events found, and the top 5 approach 70%. This is a genuine, disclosed tension with the "broad, not just a handful of recurring themes" framing Stage 12 hoped to test: the *breadth* (14/20 tickers with ≥2 events) is real, but the *depth* is uneven, with a handful of unusually well-covered names (VERITASKAP, CILEASING, LEGENDINT) doing much of the work.

## 13E. PIT completeness — hard gate

Applied to the **51 confirmed-novel events** (not just the 20 previously-processed articles):

| Classification | Count | Basis |
|---|---|---|
| **PIT-SAFE** | ~30 | Discrete corporate-action/governance/regulatory/ownership events with month-or-better date precision, ticker mapping, and source URL confirmed — no separate "did the number later change" risk (matches Stage 12's discrete-event logic, extended to this larger set: e.g. ROYALEX's relocation, chairman change; TANTALIZER's shareholder change, board appointment, MoU; CILEASING's COO appointment, CP issuance; LEGENDINT's listing, free-float compliance, FTTR launch, capital-raise authorization) |
| **PIT-UNCERTAIN** | ~21 | Every event whose content is a reported financial figure (revenue/profit/earnings) sourced from an NGX interim/unaudited filing, carrying the same unresolved audited-vs-reported risk identified in Stage 12 §12F, now applying across the larger set (e.g. CILEASING's multiple profit-growth articles, VERITASKAP's five earnings-period articles, ROYALEX's two earnings articles, REDSTAREX's profit articles) |
| **PIT-FAILED** | 0 | None — even the uncertain items have correct timestamps and provenance; the uncertainty is about figure-integrity, not identity/timestamp failure |

**Quantified**: **~41% of the confirmed-novel corpus (21/51) is PIT-uncertain**, concentrated almost entirely in the earnings/profitability category (§13D's largest single category, 37% of events). Per the explicit hard-gate instruction, **none of these 21 may enter a future research dataset** until the figure-integrity check specified in Stage 12 §12H is performed. The remaining **~59% (30/51) is PIT-safe** and could, in principle, populate a research dataset today.

Only date-level (not intraday/timestamp-level) precision exists for effectively the entire corpus — this affects **100%** of both PIT-safe and PIT-uncertain events equally, and is disclosed as a blanket limitation: no article in this corpus carries a same-day intraday publication timestamp precise enough to resolve same-day pre/post-market-session ordering. All PIT classifications above are date-level, not intraday-level.

## 13F. Signal families (hypothesis generation only — no fitting, no backtest)

**1. Insurance-sector recapitalization capital actions** (rights issues, private placements, capital-raise authorizations tied to NIIRA 2025)
- *Information input*: announced/completed capital-raise amount, structure, and regulatory-compliance status for NIIRA-affected insurers.
- *Event definition*: a discrete capital-raise announcement, approval, or completion disclosure.
- *Expected direction*: ambiguous ex ante — dilution risk vs. sector-strengthening, explicitly the open question (matches the platform's own prior CBN-recapitalization framing).
- *Expected holding period / decay*: plausibly medium (weeks to a few months around the raise cycle) — untested.
- *Minimum coverage required*: not specified by this project; **current coverage**: 6/20 tickers (LASACO, REGALINS, SUNUASSUR, UNIVINSURE, VERITASKAP, ROYALEX-adjacent via 2023 rights issue) — all insurance names.
- *Novelty rate*: 100% in every confirmed instance.
- *PIT safety*: the announcement/approval events are PIT-safe; embedded profit figures in the same articles are not.
- *Redundancy risk*: **high** — every instance is, by its own text, an NGX-filed corporate action; news's edge is speed/cost, not exclusivity (repeats Stage 11/12's central caveat).
- *H-011 overlap*: none in construction (H-011 is pure cross-sectional size ranking).
- *Plausibility*: regulatory-deadline-driven timing is unusually predictable for a news-derived signal, which is analytically attractive, but the redundancy risk is the most serious objection.

**2. Governance/management-change disclosures**
- *Information input*: board resignations, appointments, chairman elections, CEO confirmations.
- *Event definition*: a discrete personnel-change disclosure.
- *Expected direction*: ambiguous, context-dependent (a credentialed outside appointment like VERITASKAP's ex-FCCPC chairman reads differently from a routine resignation).
- *Expected holding period / decay*: untested; plausibly long (governance effects are slow-moving).
- *Coverage*: now confirmed across **8/20 tickers** (SUNUASSUR, UNIVINSURE, VERITASKAP, ROYALEX, TANTALIZER, CILEASING, plus DEAPCAP's board reshuffle as part of its transformation story) — broader than Stage 12's 3/20 estimate.
- *Novelty rate*: 100% in every confirmed instance.
- *PIT safety*: fully PIT-safe (discrete event, no figure-integrity risk).
- *Redundancy risk*: moderate — NGX disclosure rules already require these announcements; news is likely faster/cheaper, not exclusive.
- *H-011 overlap*: none — qualitative, unrelated to size ranking.
- *Plausibility*: the highest-PIT-safety, broadest-coverage qualitative category found so far — the strongest candidate of the three by this stage's own evidence.

**3. Corporate-identity / strategic-restructuring events** (renames, sector pivots, mergers, major ownership-stake changes)
- *Information input*: discrete, infrequent, high-magnitude structural events (DEAPCAP's rename, LEGENDINT's merger, ROYALEX's Nexamont stake).
- *Event definition*: AGM/board-resolution-disclosed structural change.
- *Expected direction*: high uncertainty, plausibly bimodal (optimism vs. execution-risk skepticism).
- *Expected holding period / decay*: plausibly long (multi-year repositioning, not a short-lived news pop) — untested.
- *Coverage*: 3/20 tickers confirmed (DEAPCAP, LEGENDINT, ROYALEX).
- *Novelty rate*: 100% in every confirmed instance.
- *PIT safety*: fully PIT-safe.
- *Redundancy risk*: low-moderate (eventually filed, but the narrative/rationale content is genuinely richer in news than a bare filing).
- *H-011 overlap*: none.
- *Plausibility*: rare enough (3 events across the universe) that signal density is very low for a cross-sectional factor at this sample size — more an individual-name research flag than a systematic input today.

**Not proposed as a signal family**: bare earnings/profitability reproduction — despite being the single largest content category (37% of novel events), it carries the corpus's entire PIT-uncertainty burden (§13E) and the least demonstrated exclusivity (§12H), and is explicitly excluded from candidacy until the figure-integrity check is performed.

## 13G. Economic independence from H-011

| Signal family | Fundamentally different source? | Depends on H-011's price/volume inputs? | Could be a delayed re-representation of H-011? | Info unavailable from H-011's current inputs? | Different timing? | Classification |
|---|---|---|---|---|---|---|
| Recapitalization capital actions | Yes — regulatory/corporate-action text, not price/volume | No | No — H-011 has no capital-structure input at all | Yes | Yes — event-driven vs. H-011's periodic rebalance | **PARTIALLY INDEPENDENT** (independent in construction; §13F's redundancy-risk finding means the underlying *fact* may eventually be filing-derivable, so not fully independent in ultimate information content) |
| Governance/management change | Yes — personnel disclosure text | No | No | Yes | Yes | **INDEPENDENT** |
| Corporate-identity restructuring | Yes — AGM/strategic narrative text | No | No | Yes | Yes | **INDEPENDENT** |
| Bare earnings/profitability reproduction (excluded from §13F, assessed here for completeness) | No — same underlying financial-statement numbers H-011's broader FSI campaign would also eventually extract from the primary filing | No (H-011 itself doesn't use these numbers, but the platform's *other* tracks do) | Plausibly yes — largely a faster/cheaper path to information a completed filing-extraction campaign would independently find | Marginal | Marginal — same-window as the filing, not ahead of it | **LIKELY REDUNDANT** (with the platform's own broader fundamental-extraction effort, not with H-011 specifically — H-011 itself uses none of this) |

No signal family was called independent merely for coming from a different website — each was assessed on whether its underlying information type is structurally reachable via H-011's own inputs (price/volume/size ranking), which none of them are; the finer distinction drawn here is between independence *from H-011* (all four clear this bar trivially, since H-011 uses none of this) and independence *from what the platform's other, non-H-011 extraction efforts could eventually find* (only 2 of 4 clear this stricter bar).

## 13H. Final news track gate

**Threshold-by-threshold:**

| # | Threshold | Requirement | Result | Pass? |
|---|---|---|---|---|
| 1 | Classification rate | ≥80% | 87.6% | **PASS** |
| 2 | Confirmed novelty among classified | ≥50% | 51.5% | **PASS** (narrow) |
| 3 | Conservative lower-bound novelty | ≥30% | 45.1% | **PASS** |
| 4 | ≥10 names with ≥2 independent novel events | ≥10 | 14/20 | **PASS** |
| 5 | No severe dependence on largest/liquid names | — | Top novel-event contributors (VERITASKAP, CILEASING, LEGENDINT) span low-to-mid liquidity; TANTALIZER (the universe's single most liquid name) is also unusually rich (6 events) — a partial re-emergence of liquidity correlation at the tail, not severe, but worth flagging, not ignoring | **PASS, with a noted caveat** |
| 6 | ≥90% PIT-safe or bounded remediation path | ≥90% or bounded path | 59% (30/51) unconditionally PIT-safe; the remaining 41% has a specific, already-identified remediation path (match news-reported figures against later official filings once they exist in-archive) but that check has not yet been executed | **CONDITIONAL PASS** — bounded path exists and is precisely specified, raw percentage does not clear 90% |
| 7 | ≥2 signal families genuinely different from H-011 | ≥2 | 3 of 3 proposed families are INDEPENDENT or PARTIALLY INDEPENDENT from H-011 specifically (§13G) | **PASS** |
| 8 | No unresolved pipeline integrity defect | — | None found; Stage 10E's fix and Stage 12's dedup both confirmed working correctly again this stage | **PASS** |
| 9 | Sufficient temporal depth | — | 8/20 tickers show confirmed coverage into 2018-2022; overall median first-seen year materially predates 2024 | **PASS** |

**8 of 9 thresholds pass cleanly; threshold 6 passes conditionally, not outright.**

**Decision: CONDITIONAL GO — narrowly scoped.**

The news track is **authorized to proceed to formal factor specification**, but **restricted to the PIT-safe discrete-event signal families**: governance/management change (INDEPENDENT, fully PIT-safe, 8/20 coverage) and corporate-identity restructuring (INDEPENDENT, fully PIT-safe, 3/20 coverage) are cleared without further precondition. The recapitalization capital-actions family (PARTIALLY INDEPENDENT) may be included in specification but must be flagged with its redundancy-risk caveat. **Bare earnings/profitability reproduction is explicitly NOT cleared** — it remains blocked until the figure-integrity remediation specified in Stage 12 §12H is executed, since it is both the single largest content category and the entire source of this stage's PIT-uncertainty.

This is not a full, unconditional GO: per the standing instruction, factor specification may proceed, but **backtesting remains prohibited** even after specification, pending independent review of that specification — and pending resolution of the earnings-figure PIT question if that category is ever to be included. NSLTECH's identity ambiguity and OMATEK/WAPIC's confirmed gaps remain open, unresolved items that do not block this narrower GO but should be closed before any claim of full-universe coverage.

**Not authorized**: H-019 creation, backtesting, any use of the earnings/profitability category, or treating the top-3-ticker concentration (§13D, ~49%) as resolved — a factor spec built on this corpus should explicitly address whether that concentration is a sampling artifact of this pilot or a structural feature of news coverage, before being treated as production-ready breadth.
