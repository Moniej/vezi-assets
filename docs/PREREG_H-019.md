# Pre-Registration — H-019: News-Event (GMC + CIR) (family: News-Event, new family)

*Drafted 2026-08-08, BEFORE any H-019 experiment or backtest run, and BEFORE
any return-series analysis of any kind. Executable specification:
`docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md` (frozen after 6
independent review rounds — see that document's §14K-§14N amendment logs).
Dataset artifact: `data/hypotheses/h019/h019_event_dataset_2026-08-08.csv`.
Changes after first results = new hypothesis ID, per this platform's
standing convention (see every prior PREREG_H-*.md).*

## Economic rationale and market intuition

Stages 1-9 established that fundamental-statement and insider-dealing data
cannot support a second, independent alpha layer on this platform — coverage
of H-011's actual small-cap holdings never exceeded 0% (fundamentals) or 15%
single-snapshot (insider dealing). Stages 10-13 established, through a
bounded but real pilot (20 real articles fully processed via the live
Gemini/FSI pipeline, 100% grounding pass rate; 51 independent novel events
identified and classified against the existing archive), that financial news
does not reproduce that coverage/liquidity bias — the platform's single
least-liquid H-011 name had among the richest confirmed news coverage found.
Two discrete-event families — governance/management-change disclosures and
corporate-identity restructurings — were found to be (a) genuinely novel
relative to the archive in every confirmed case, (b) fully PIT-safe (unlike
earnings-figure reproduction, which remains explicitly excluded pending an
unresolved figure-integrity question), and (c) structurally independent of
H-011's size-ranking input. The claim under test is narrow and specific: that
*discrete disclosure events of these two kinds*, not news in general and not
earnings content, carry information with a market-reaction footprint
distinguishable from noise. This is explicitly NOT a claim that "the market
underreacts to news" in general — it is scoped to exactly the two families
Stage 13/14 cleared, nothing more.

## Research question / hypotheses

Do GMC and CIR events, PIT-dated to their `knowledge_timestamp` and
classified by the frozen, non-LLM-sentiment direction rule (§14C), carry a
detectable, economically meaningful market-reaction signal for the affected
ticker, independent of H-011's existing size-ranking signal?

- H0: no detectable relationship between event occurrence/direction and
  subsequent returns, or any detected relationship is not independent of
  H-011.
- H1: a detectable, H-011-independent relationship exists.

**This pre-registration covers the event/signal-construction layer only.**
Portfolio construction (top_n, rebalance cadence, holding-period/decay
window, cost model, benchmark) is deliberately **not specified in this
document** — Stage 14 §14B explicitly declined to assume a holding period,
since fixing one now, with only 6 events in hand and zero return data
examined, would be indistinguishable from parameter selection. Portfolio
construction must be pre-registered in a **separate, explicitly authorized
follow-up** before any backtest is run, per the standing instruction not to
optimize this hypothesis against historical returns before independent
review of the dataset itself.

## Universe / data (frozen, per Stage 14)

- Universe: the 20 H-011 holdings, `data/reference/stage6_h011_universe_2026-08-08.json`
  (formation date 2026-06-30). Re-freeze required if H-011's universe changes
  at a future rebalance.
- Eligible sources: Nairametrics, MarketForces Africa. No other source.
- Eligible event types: `management_change` (GMC); `corporate_restructuring`,
  `merger`, `ownership_change` (CIR). No other `event_type`.
- Excluded explicitly: all earnings/profitability facts; `capital_raise`;
  `regulatory_action`; any event from an unapproved source; any event failing
  the §14A minimum-evidence requirement.
- Direction: derived **only** from the §14C rule tables applied to the
  structured `events` row's own fields — never from `investment_implications.direction`
  (the Gemini-derived, confidence-floor-capped subjective assessment).
- PIT rule: `knowledge_timestamp` = the article's own publication/announced
  date; `eligible_from` = the next NGX trading session (`index_levels.trade_date`,
  `confidence >= 0.5`) strictly after that date — never the same session. No
  PIT-uncertain observation is eligible.
- Deduplication: the existing, Stage-10E-fixed `event_pipeline.validate_batch()`
  natural key for within-source handling; cross-outlet linkage via the §14D
  outlet-domain-normalization procedure (ticker + event_type + ±3-day window +
  identity-content agreement + different, non-UNKNOWN outlet), fail-closed to
  `candidate_corroboration_unconfirmed` on any ambiguity.

## Current dataset (as constructed, frozen at 6 events — see audit for verification)

| ticker | event_type | direction | event_date | knowledge_date | eligible_from | PIT_status | duplicate_status | canonical_event_id |
|---|---|---|---|---|---|---|---|---|
| DEAPCAP | corporate_restructuring | positive | 2026-03-17 | 2026-03-17 | 2026-03-18 | PIT-SAFE | primary | news_nairametrics_2026-03-17_deapcap_rename |
| LEGENDINT | merger | positive | 2026-03-24 | 2026-03-24 | 2026-03-25 | PIT-SAFE | primary | news_nairametrics_2026-03-24_legendint_spectranet |
| ROYALEX | ownership_change | neutral | 2025-09-21 | 2025-09-21 | 2025-09-22 | PIT-SAFE | primary | news_nairametrics_2025-09-21_royalex_nexamont |
| SUNUASSUR | management_change | neutral | 2026-04-01 | 2026-04-11 | 2026-04-13 | PIT-SAFE | primary | news_nairametrics_2026-04-11_sunuassur_board |
| UNIVINSURE | management_change | neutral | 2025-01-10 | 2025-01-17 | 2025-01-20 | PIT-SAFE | primary | news_nairametrics_2025-01-17_univinsure_ceo |
| VERITASKAP | management_change | neutral | 2025-10-31 | 2025-11-03 | 2025-11-04 | PIT-SAFE | primary | news_nairametrics_2025-11-03_veritaskap_chairman |

**Directional composition, disclosed plainly, not smoothed over**: 2 of 6
`positive`, 0 `negative`, 4 of 6 `neutral`. All 4 GMC events resolve to
`neutral` under the objective rule — this was disclosed in Stage 14 §14C as a
property of the rule applied to real data, not a defect. **A dataset this
small, with zero realized `negative` observations, cannot support a
directional backtest with any statistical meaning yet.** This is stated here
as a pre-declared limitation, not discovered after the fact.

## Known limitations (pre-declared)

L1. **n=6.** This is not a rejection of the hypothesis — Stage 13's fuller
audit found 51 independent novel events across the corpus, of which only 6
currently sit in the two cleared, fully-processed families in the live
database; the rest require further, not-yet-authorized processing (expanding
beyond the bounded pilot). A meaningful backtest requires more observations
than currently exist — this pre-registration freezes the *method*, not a
claim that today's 6-row dataset is sufficient to test anything yet.
L2. Zero realized `negative` direction observations in the current dataset —
see above.
L3. All 6 events are single-outlet (Nairametrics); the cross-outlet
reconciliation procedure (§14D) has never yet been exercised against a real
duplicate pair, only traced by hand against synthetic/hypothetical cases.
L4. The ±3-calendar-day cross-outlet window (§14D) remains provisional,
unfitted against any real duplicate pair.
L5. The H-011 size/distress common-cause confound (§14G, §14J item 10) has
not yet been run. Per that section's explicit rule, **no H-019 result may be
described as independent of H-011 until it is** — this is a precondition on
*interpretation*, not on dataset construction, and does not block this
pre-registration or the dataset build, but does block any future claim of
clean independence.
L6. Portfolio construction is explicitly undefined in this document — see
Research Question section above.

## Next steps (not authorized by this document alone)

1. Independent audit of this dataset (coverage, event counts, PIT compliance,
   duplicate/corroboration handling, H-011 independence, leakage, earnings
   contamination) — commissioned separately, see
   `docs/H019_INDEPENDENT_AUDIT_2026-08-08.md`.
2. If the audit passes: a separate, explicitly authorized portfolio-
   construction pre-registration (matching the rigor of `docs/PREREG_H-011.md`'s
   Portfolio construction / Benchmark / Validation plan / Confirmation-requires
   sections), written **before** any return data is examined.
3. Only after both of the above: backtest execution, under
   `runner.py`/`phase4.py`, per this platform's standard validation gauntlet.

No step beyond (1) is authorized by this pre-registration alone.
