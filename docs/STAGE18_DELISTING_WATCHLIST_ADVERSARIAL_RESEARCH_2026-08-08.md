# Stage 18 — Delisting-Watchlist Distress Mispricing: Adversarial Research

**Date:** 2026-08-08
**Status: RESEARCH DISCOVERY ONLY.** No hypothesis registered, no factor built, no backtest run, no return-dependent event selection. H-011 and H-019 confirmed untouched (file timestamps unchanged: `configs/h011_size.toml` 2026-07-22, `docs/PREREG_H-011.md` 2026-07-22, `docs/PREREG_H-019.md` unchanged since its last legitimate edit; ledger unchanged beyond what already existed). The one price/volume check performed in §8 is diagnostic evidence for the adversarial analysis explicitly requested, not signal construction or event selection.

---

## §1. Research objective

Determine whether NGX's own first-party listing-status/regulatory-compliance records (Delisting Watch List, Delisting-in-Process, regulatory suspensions) contain a genuinely distinct, persistent, PIT-safe information mechanism — and specifically, to try as hard as possible to disprove that the DEAPCAP finding from Stage 17 supports this thesis, before recommending anything.

## §2. Source universe and acquisition

- **`ngxgroup.com`** (NGX Group's own site): `robots.txt` checked live — `Disallow: /wp-admin/` only, everything else permitted. Sitemap disclosed.
- **`doclib.ngxgroup.com`** (NGX's document library subdomain): no `robots.txt` exists (confirmed via direct fetch — returns a SharePoint 404 page, not a robots policy). Absence of a `robots.txt` is treated as no stated restriction, per standard convention — the same treatment this platform has applied to every other source it has checked.
- Two X-Compliance Report PDFs fetched directly (single, bounded fetches, not bulk crawling): one found via public search at a static `doclib.ngxgroup.com` URL, the other from the live `ngxgroup.com/ngx-download/x-compliance-report/` weekly-refresh endpoint.
- **A genuine acquisition surprise, disclosed rather than hidden**: the first PDF fetched, at a URL search results implied was "the" X-Compliance report, turned out to carry an internal **`REPORT DATE: 09-APR-2021`** — a five-year-old snapshot, despite nothing in the URL suggesting staleness. This was caught by reading the document's own stated date, not assumed current. It is now used deliberately as a historical comparison point (§3), not discarded, but it was never treated as "today's" watchlist.
- The second PDF, fetched from the correct current-report endpoint, carries **`REPORT DATE: 7 August 2026`** — one day before this stage — genuinely current, first-party data.
- New source registered: `ngx_xcompliance_regco` (`source_id=17`, `kind='regulator'`, `base_confidence=0.9`), following the exact precedent of `cbn_decisions_page` (`source_id=10`) for a first-party regulator, not the `web_archive` placeholder used for news. Both PDFs registered as `documents` rows (`doc_id=11561`, `11562`) **before** any event was ingested, learning directly from the Stage 14 Round 4 provenance gap.

## §3. Historical corpus

8 events ingested via the standard, unmodified `event_pipeline.validate_batch()`/`ingest_events()` path, in a dedicated batch directory (`data/events_regulatory/`, isolated from unrelated prior batches after an initial dry-run correctly caught the isolation mistake — see the working log; fixed before any write). All 8 accepted, 0 rejected, 0 issues.

| event_id | ticker | event_type | announced_date | Finding |
|---|---|---|---|---|
| 187 | DEAPCAP | regulatory_action | 2021-04-09 | **Already** on Delisting Watchlist at the earliest report this project has observed — true origin date unknown, disclosed as such, not guessed |
| 188 | DEAPCAP | regulatory_action | 2026-08-07 | Still on Delisting Watchlist, now under its post-rename name "Critical Minerals Financing Corp Plc" — confirms the DWL status spans H-019's entire corporate_restructuring event (2026-03-17) on both sides |
| 189 | OMATEK | regulatory_action | 2021-04-09 | On DWL in 2021; **confirmed absent** from the 2026-08-07 report (apparent exit) — exact exit date genuinely unknown, no event fabricated for it |
| 190 | UNIONDICON | regulatory_action | 2024-11-01 | Exact board-meeting date from the source; was on lighter "restructuring" status in 2021, a real, dated state progression |
| 191 | STACO | regulatory_action | 2025-02-14 | Exact board-meeting date |
| 192 | EKOCORP | regulatory_action | 2026-03-27 | A distinct state: an *already-approved* delisting process placed on **hold** for litigation reasons — not a watchlist placement, not a suspension |
| 193 | REGALINS | resumption | 2025-09-08 | **New finding, not previously in this database**: complements the existing suspension (event_id=168) — the suspension lasted only 7 days |
| 194 | UNIVINSURE | resumption | 2025-09-03 | Complements existing suspension (event_id=169) — lasted only 2 days |

**Coverage limitation disclosed, not smoothed over**: "Fortis Global Insurance Plc," named in the current report as a third DWL member, was **not** registered as an event — the only plausible ticker match found in `securities` (`FORTISMFB`) is, on its face, "Fortis Microfinance Bank," a different entity, and this platform's own standing discipline (reinforced repeatedly since Stage 10E) is to never guess an identity match. Left as an unresolved ticker-mapping gap, not silently forced. "Multi-Trex Integrated Foods Plc" is confirmed on DWL currently but its exact placement date was not visible in the excerpted text reviewed — also not fabricated, also left as a gap (§14).

## §4. Regulatory-state taxonomy

Built from what was actually observed, not designed in advance:

| State | Meaning | Observed examples |
|---|---|---|
| Compliant / no flag | No filing/free-float/other deficiency currently disclosed | Most listed companies |
| Restructuring (BMR/MRS/RST codes) | A lighter compliance status, subject to quarterly reporting | Union Dicon Salt (2021), Multi-Trex (2021), several others |
| Delisting Watchlist (DWL) | A formal, board-approved, time-bounded monitoring status ahead of possible delisting | DEAPCAP, OMATEK (2021), Union Dicon Salt, STACO (current) |
| Delisting In Process (DIP) | Board has approved proceeding with delisting | Historically Evans Medical, Tourist Company, others (2021); Ekocorp (approved, then paused) |
| DIP, paused for litigation | A genuinely distinct sub-state: delisting approved but held pending a court outcome | Ekocorp (2026) |
| Regulatory suspension | Trading halted pursuant to Rule 3.1/7.0 for filing default or other cause | REGALINS, UNIVINSURE, International Energy Insurance, Thomas Wyatt, Zichis Agro-Allied, Golden Guinea, Aluminium Extrusion |
| Resumption | Suspension lifted, trading restored | REGALINS (7 days), UNIVINSURE (2 days), International Energy Insurance (31 days), Thomas Wyatt (~8 months), Zichis Agro-Allied (~1 month) |

**Progressions observed as real, dated transitions** (not assumed): Union Dicon Salt moved Restructuring (2021) → DWL (2024-11-01) — a genuine worsening over 3+ years. Multi-Trex moved the same direction. This confirms the taxonomy has real, non-trivial state transitions worth modeling, not just a static label.

## §5. Novelty/incremental-information audit

Per the five-way classification requested:

1. **Genuinely new regulatory information**: the two resumption events (193, 194) — never previously captured on this platform, and not derivable from anything already in the archive (the existing suspension rows have no lift date at all).
2. **Formal confirmation of information already public**: DEAPCAP's and OMATEK's 2021 DWL status — by the time this project observed it (2021-04-09 report), the underlying placement had already happened and was presumably already reflected in whatever price reaction it caused; this project's *observation* of it in 2026 is not new information to the market, only new to this database.
3. **Administrative/no-economic-information events**: arguably Ekocorp's litigation-pause — a procedural continuation of an already-known process, not a fresh disclosure of new facts about the company's economics.
4. **Corroboration of an existing event**: the 2026-08-07 DEAPCAP DWL confirmation (event 188) corroborates, not adds to, the 2021 observation (event 187) — both preserved, not collapsed into one, per the platform's append-only convention, but explicitly not counted as two independent pieces of information.
5. **Ambiguous cases**: OMATEK's apparent exit — genuinely ambiguous whether this reflects a real compliance improvement (positive information) or simply that OMATEK aged out of monitoring for a procedural reason; marked UNKNOWN, not guessed.

**Bottom line for this audit**: of the 8 events registered, only the **2 resumption events** are unambiguously NOVEL in the sense of "information this platform did not already have access to and that had a knowable, specific knowledge timestamp." The DWL placements are, at best, PARTIAL — real regulatory facts, newly captured *by this database*, but not demonstrably novel *to the market* at the timestamps this project can assign them (see §6).

## §6. PIT/provenance audit

- All 8 events: document-linked (verified independently via direct query and via the widened `scripts/test_event_document_provenance.py`, now covering `kind='regulator'` sources in addition to the two news outlets — 26/26 ticker-scoped news/regulator events checked, 0 orphans).
- **A hard, honestly-stated PIT limitation**: for DEAPCAP and OMATEK, this project's earliest observation (2021-04-09) is **not** the true knowledge date of their DWL placement — it is only the earliest date this project has *confirmed* the status existed. The true placement date is almost certainly earlier and is marked as such in the event's own `notes` field, never backdated or guessed. **Any research process using these two specific rows must not treat 2021-04-09 as `knowledge_timestamp` for a market-reaction study** — it would be a real, avoidable PIT violation if someone later assumes the market first learned of DEAPCAP's distress status in April 2021.
- For UNIONDICON, STACO, and EKOCORP, the announced_date is a genuine board-meeting date **stated by the source document itself** — a materially stronger PIT position than DEAPCAP/OMATEK's rows.
- The two resumption events (193, 194) carry an `effective_date` equal to `announced_date` (the resumption date, as reported) — clean.
- **No `eligible_from`/next-trading-session computation was performed in this stage** — that is deliberately deferred to a future factor-specification stage (per the "no factor construction" constraint), consistent with how H-020 kept dataset construction and portfolio construction as separate, sequential steps.

## §7. H-011/H-019 independence audit

- **DEAPCAP and OMATEK are both current H-011 holdings.** This is not incidental — H-011 selects the smallest-cap names in the IRU, and this stage's own regulatory-distress findings concentrate in exactly that tier. This is the same structural overlap Stage 17 already flagged for other tracks (§9 there) and it recurs here: **a distress-flag signal built on H-011's own universe risks being partly a re-expression of "small, distressed, illiquid" — the same underlying company characteristic H-011 itself selects on** — not a mechanically shared input (DWL status is not a `size_scores()` input), but a plausible common-cause confound, exactly like the one Stage 14 §14G already flagged and never resolved for H-019.
- **REGALINS and UNIVINSURE are both current H-011 holdings** and both already carry H-019 events (management_change for UNIVINSURE; the regulatory_action suspension itself predates and is excluded from H-019's scope for both). The new resumption events (193, 194) are a **genuinely new event_type** (`resumption`) not present in H-019's dataset at all — mechanically independent of H-019's `management_change`/`corporate_restructuring`/`merger`/`ownership_change` scope.
- **Not redundant with H-019's excluded `capital_raise` family**: DWL/suspension/resumption events describe compliance/listing status, not capital-raising transactions — a different economic mechanism, even where the same ticker (UNIVINSURE) happens to carry both.
- **Classification: PARTIALLY INDEPENDENT.** Mechanically independent of both H-011's inputs and H-019's event scope; economically entangled with the same small-cap/distress characteristic H-011 selects on, in a way that has not been tested (exactly the outstanding §14G confound check, still unrun).

## §8. Adversarial failure analysis — the DEAPCAP case, stress-tested directly

This section follows the explicit instruction to try hardest to disprove the thesis, using DEAPCAP (the specific case that motivated this stage) as the test subject.

- **Was the information already public elsewhere?** Yes, unambiguously — DEAPCAP's DWL status has been public, first-party, NGX-disclosed information since at least 2021, over five years before its H-019 event. Whatever the market does with this information, it has had years to do it.
- **Was the watchlist merely confirming an existing distress state?** Yes — nothing in this stage's evidence suggests a *change* in DEAPCAP's regulatory state around its 2026-03-17 event; the DWL status appears continuous across the entire observed window (2021 through August 2026).
- **Did price/volume move before the formal event?** This is the most damaging finding of this stage. A direct query of DEAPCAP's actual price series (not a backtest — a diagnostic check, as explicitly authorized by this instruction) shows: DEAPCAP traded at **₦2.09 on 2026-01-02** and ran to a peak of **₦10.43 on 2026-01-29** — roughly a **400% run-up, entirely before** the 2026-03-17 rename/capital-injection event H-019 classified as the informational trigger. By the event date itself (2026-03-17, close ₦6.90), the stock had **already fallen ~34% from its January peak**. H-019's entry (2026-03-18, per the frozen PIT rule) bought into a stock already in a post-peak decline from an earlier, unrelated speculative run — consistent with Stage 11's own separate finding that a January 2026 MoU announcement (not the March capital-injection event) was the actual price-moving catalyst. **This directly undermines any clean "the market underreacted to the March disclosure" story** — the evidence points to the opposite: the market had already reacted, heavily, to something else, and by the time H-019's classified event occurred, was arguably correcting an overreaction, not underreacting to new information.
- **Are events clustered around companies already in severe distress?** Yes — DEAPCAP and OMATEK's DWL tenure spans essentially this entire project's data history; this is not a track of "companies that occasionally enter distress," it risks being a track of "the same handful of chronically distressed names," which caps how many genuinely independent observations this mechanism can ever produce (§14).
- **Is the apparent signal simply a proxy for size/illiquidity?** Plausible and unresolved — see §7's independence audit; both confirmed distressed H-011 names are also H-011's own smallest/most illiquid holdings.
- **Is it simply another representation of H-011?** No, not mechanically — but see the confound risk above.
- **Is it redundant with H-019 capital-action events?** No — different event types, different economic content, confirmed in §7.
- **Survivorship/delisting bias?** A real, structural risk specific to this track alone among the five surveyed in Stage 17: a company that actually gets delisted disappears from every price panel this platform uses (`equity_prices`, `index_levels`) at the point of delisting — meaning any future backtest of this mechanism risks silently excluding exactly the cases where the "distress" thesis played out most completely (full delisting), biasing toward the milder, survived cases. This must be designed around explicitly before any factor specification, not discovered afterward.
- **Are companies entering the watchlist already effectively uninvestable?** A fair question, not yet answerable from data on this platform — this project doesn't currently track free-float/liquidity-eligibility screens tightly enough to say whether DWL names are excludable from a realistic investable universe *before* considering any signal.
- **Does the signal disappear after controlling for the broader regulatory state?** Cannot be tested with n=1 clean case (DEAPCAP is confounded, per above) — this is exactly why §15 does not recommend proceeding on DEAPCAP's evidence alone.

**Counter-check, for balance**: REGALINS's price around its own suspension/resumption (2025-09-01 to 09-08) shows the opposite pattern — price actually **rose** from ₦1.30 (pre-suspension) to ₦1.82 by mid-September, a positive post-resumption drift, not a decline. Two cases, two opposite directions — this is disclosed explicitly as evidence *against* any simple, universal "distress event → predictable direction" story, not cherry-picked to support one.

## §9. Mechanism analysis (no LLM sentiment, no directional label assumed)

No objective, frozen directional rule is proposed in this stage — per the explicit instruction, one must be defined and frozen *before* returns are examined, and this stage's own adversarial price checks (§8) were necessarily done *after* looking at DEAPCAP's returns (unavoidable, since the whole point was to stress-test that specific case) — meaning **no directional rule should be written today** without first disclosing that this stage's authors have already seen DEAPCAP's and REGALINS's realized price paths, which would taint any rule "discovered" now. This is stated explicitly as a process constraint on the *next* stage, not evaded.

What can be said about the mechanism structurally: DWL/suspension events plausibly create (a) **forced-selling/liquidity effects** for a genuine trading suspension (holders cannot exit during the halt, a real, mechanical friction, distinct from ordinary illiquidity), and (b) **persistent uncertainty** for a DWL placement (the company remains listed but under a multi-year compliance shadow) — but whether either translates into a *predictable, tradable* price pattern is exactly what §8 could not confirm and partially disconfirmed for the one case available.

## §10. Delisting-watchlist feasibility verdict

**CONDITIONAL, materially downgraded from Stage 17's framing.** The source is genuinely excellent (first-party, NGX RegCo, robots-clear, dateable board-meeting decisions for 3 of 8 events). But the flagship case (DEAPCAP) that motivated escalating this track **does not survive adversarial scrutiny** — its price action is dominated by an earlier, unrelated speculative catalyst, and its distress status is not new information by any reasonable definition. The mechanism remains structurally plausible (§9) but is currently supported by a very small, confounded evidence base (8 events, spanning as few as 6-7 genuinely independent underlying situations once DEAPCAP's two observations are collapsed), with a real, unresolved H-011 common-cause confound and a real, structural survivorship-bias risk unique to this track. **Not NO-GO** — the resumption events (193, 194) are genuinely novel, clean, and interesting on their own, and the source itself deserves further, broader extraction (§14). **Not GO** — the specific evidence that prompted escalation does not hold up, and this must be stated plainly rather than downplayed.

## §11. Recapitalization-dilution feasibility verdict (discovery-level only, per instruction)

Reconfirms Stage 17 §D/§H item 2 without new data collection this stage: coverage exists (4 `capital_raise` events, H-011 universe), the *aggregate* recap trade is dead (both bank and insurance deadlines concluded before this stage), and the *relative* (dilution-magnitude, winners-vs-losers) reframing remains untested and would require fresh, bounded extraction of realized dilution figures from NAICOM's/CBN's own published compliance data — not attempted this stage, correctly out of scope per the instruction to evaluate this track "at the discovery/feasibility level only."

## §12. NGX-specific PEAD feasibility verdict (discovery-level only, per instruction)

Reconfirms Stage 16 §H-A's finding directly: **this remains, economically, the same hypothesis H-006 already tested and rejected**, now on a different data channel (news-derived facts vs. filing dates) — the instruction's own explicit rule ("if it is economically the same hypothesis, kill it rather than relabeling it") applies. Distinguishing factor from H-019: H-019 is discrete-event/qualitative (governance, restructuring), never touching earnings figures; PEAD by definition requires an earnings-surprise construct, which is a different informational input than anything in H-019's dataset — so it is *not* redundant with H-019 in content, but *is* redundant with H-006 in economic substance. **Verdict: NO-GO, confirmed, not merely repeated** — the coverage blocker (≥2 comparable-period observations needed, 0/20 H-011 names currently qualify) is unchanged since Stage 16, and no new data was gathered this stage to challenge that finding.

## §13. Comparative ranking

| Criterion | Delisting-Watchlist | Recap Dilution | NGX PEAD |
|---|---|---|---|
| 1. Information novelty | Medium (2/8 events clean; rest partial/confirmatory) | Low (redundant with primary filings, previously flagged) | None (same hypothesis as H-006) |
| 2. Historical coverage | Thin (6-7 independent situations, longitudinal to 2021) | Thin (4 events, one window) | Near-zero (0/20 comparable-period pairs) |
| 3. PIT integrity | Mixed — strong for 5/8 rows (exact board dates), weak for 2/8 (DEAPCAP/OMATEK observation-not-origin dates), clean for 2/8 (resumptions) | Not reassessed this stage | Unresolved (same audited-vs-unaudited risk as H-019's exclusion) |
| 4. Independence from H-011/H-019 | Partially independent; real, unresolved common-cause confound with H-011 | Weak (inherits H-019's own redundancy exclusion) | Weak (same claim as rejected H-006) |
| 5. Objective event definition | Not yet written (deliberately deferred, §9) | Not yet written | N/A — hypothesis already dead |
| 6. Likely persistence mechanism | Plausible (forced-selling during suspension; multi-year uncertainty for DWL) but unconfirmed | Plausible (dilution mispricing) but untested | Contradicted by this platform's own H-006 result |
| 7. Data quality | High for source; low for volume | Medium | Low (coverage gap) |
| 8. Susceptibility to look-ahead/survivorship bias | **High and structural** — real delisting removes names from every price panel (§8) | Low | Low |
| 9. Ability to scale | Unclear — may be a persistently small-n track (chronic-distress-name concentration, §8) | Bounded by the now-closed recap window | Blocked entirely on data |
| 10. Adversarial robustness | **Failed on its own flagship case** (DEAPCAP); one counter-example (REGALINS) shows the opposite direction | Not stress-tested this stage | N/A |

## §14. Exact remaining data gaps

- Multi-Trex's and Fortis Global Insurance's exact DWL entry dates (Multi-Trex: status confirmed, date not visible in reviewed text; Fortis: ticker identity itself unresolved).
- DEAPCAP's and OMATEK's *true* original DWL placement dates (both predate this project's earliest observation, 2021-04-09) — potentially findable in an even older X-Compliance report or NGX's own historical bulletin archive, not attempted this stage.
- OMATEK's exact DWL exit date (confirmed present 2021, confirmed absent 2026, nothing in between examined).
- No intermediate (2022–2025) X-Compliance snapshots were fetched — the historical corpus currently has exactly two points (2021, 2026), not a continuous series; NGX's weekly-Friday cadence implies a large number of intermediate reports may exist in some archived form, unconfirmed.
- Fuller Schedule 9 (suspensions) history beyond what was excerpted in the two fetched reports — additional suspension/resumption pairs almost certainly exist for non-H-011 names, unexamined.
- No free-float/investability screen has been applied to any DWL-flagged name to assess whether it would already be excluded from a realistic tradable universe.

## §15. GO / CONDITIONAL GO / NO-GO

**Delisting-Watchlist Distress Mispricing: CONDITIONAL GO — narrower and more cautious than Stage 17's framing, explicitly not on the strength of the DEAPCAP case.**

The source and mechanism remain worth pursuing *only* if the next step is: (a) extend the historical corpus with intermediate X-Compliance snapshots to build a genuinely larger, less DEAPCAP-dependent sample; (b) resolve the survivorship-bias question structurally before any signal work (confirm whether this platform's price panels retain delisted-name history at all); (c) run the still-outstanding H-011 size/distress confound check (§14G, never executed) specifically using this stage's own regulatory-state data, since it is now the most direct evidence available for that exact question; (d) do **not** use DEAPCAP as a supporting example in any future proposal — this stage found it does not hold up.

**Recapitalization Dilution: CONDITIONAL, unchanged from Stage 17** — worth a bounded extraction pass on realized dilution figures, not attempted here.

**NGX-specific PEAD: NO-GO, confirmed** — economically identical to H-006, already rejected; no new evidence this stage changes that.

**This document does not claim alpha, profitability, Sharpe, statistical significance, or predictive power for any of the three tracks.** It answers only whether a real information mechanism exists worth specifying further — and for the primary track, the honest answer is: a real, first-party, previously-unused data source exists and produced two genuinely novel findings (the resumption events), but the specific case that motivated escalating this track does not survive adversarial testing, and the track should proceed, if at all, on a broader and more skeptical footing than it started with.
