# Hypothesis Family Map — datasets → future research programs

*2026-07-15. This map is the audit trail for generativity scores in
`configs/dataset_priorities.toml`: a dataset may only claim a family listed
here, and a family may only be claimed if the dataset is genuinely in its
dependency set. Families are research PROGRAMS (each would spawn multiple
numbered hypotheses), not trade ideas. New families are added as the data
suggests them — that is the point of the program.*

Status vocabulary: `active` (hypothesis open in ledger) · `testable-now` ·
`blocked-on-data` · `speculative` (plausible, mechanism unproven anywhere).

| ID | Family | Mechanism sketch | Status | Dataset dependencies |
|----|--------|-----------------|--------|----------------------|
| F1 | Event-driven sector rotation | Slow-moving regulatory/macro catalysts reprice sectors with lag (thin coverage) | H-003 REJECTED 2026-07-16 (as tested; OOS uninformative) | pit_event_database, cbn_circulars, mpc_history, naicom_pencom, sec_directives, inflation_gdp, brent |

**F1 post-verdict generation review (H-003, 2026-07-16):**
- *Patterns deserving their own hypothesis:* monotonic improvement with the
  activity window (−7.8% at 6m → −2.3% at 12m → +3.2% at 18m net excess).
  Consistent with the H-005-derived slow-catalyst constraint taken further:
  if NGX catalysts act at all, they act over 18+ month horizons. A W≥18
  variant under this ID would be tuning-after-results; it is admissible only
  as a NEW hypothesis on materially expanded event data with forward OOS.
- *Unexpected relationship:* the entry-time impairment flag excluded Banking
  during the 2024–26 recapitalisation — which coincided with a strong
  banking market. The dilution-bearish mechanism may be wrong-signed for
  NGX recapitalisations (capital raises as strength signals in this market).
  Testing "recap = bullish" on 2024 data is pure hindsight; it is testable
  only on forward events or on the pre-2012 recap era (requires older price
  data). Recorded as a mechanism question, not a candidate.
- *Dataset combination:* the binding constraint was 10 sector-scoped events
  over 8.5 years — the strategy sat in the ASI fallback roughly half the
  sample. Any F1 successor needs an order-of-magnitude more events:
  earnings/dividend calendars (acquisition core #4) and granular circular
  curation are prerequisites, not enhancements.
- *Different mechanism, not dead end?* Activity (attention/repricing flows)
  was tested; direction-informed positioning was not (no non-hindsight
  direction source exists yet). A forward-looking direction source —
  e.g., analyst/press tone at announcement time (F10-adjacent) — would be a
  genuinely different mechanism requiring new data.
| F2 | Total-return momentum & dividend effects | Price-only indices mis-measure momentum in a high-yield market | blocked-on-data (H-002) | dividend_earnings_calendar, index_membership_pit, pricelists (fwd+backfill) |
| F3 | Index-rebalance / flow anticipation | Semi-annual review adds/drops force flows in a thin market; announced→effective window is tradeable | blocked-on-data | index_membership_pit, ngx_daily_pricelist_forward, pricelist_wayback_backfill |
| F4 | Liquidity premia & microstructure | Illiquidity premium, thin-market reversal, zero-volume stretches as information | blocked-on-data | ngx_daily_pricelist_forward, pricelist_wayback_backfill |
| F5 | Post-earnings announcement drift | PEAD plausibly extreme under thin analyst coverage | blocked-on-data | dividend_earnings_calendar, xissuer_disclosure_archive, pricelists |
| F6 | Dividend capture / ex-date effects | Qualification-date mechanics + retail clienteles → predictable ex-date behavior | blocked-on-data | dividend_earnings_calendar, ngx_daily_pricelist_forward |
| F7 | FX-regime conditional allocation | Sector sensitivity to official/parallel spread & regime shifts (2023 proved the magnitude) | blocked-on-data | fx_parallel_market_history, pit_event_database, cbn_circulars |
| F8 | Execution & capacity alpha | Impact modeling from real volume/deals data; cost reduction is alpha at NGX cost levels | blocked-on-data | ngx_daily_pricelist_forward, pricelist_wayback_backfill |
| F9 | Governance-event effects | Board/CEO/auditor changes move thin names; no one systematically tracks | blocked-on-data | agm_governance_events, xissuer_disclosure_archive |
| F10 | Coverage-initiation effects | First analyst coverage of an ignored name re-rates it | speculative | broker_research_archive |
| F11 | Macro-release timing | Return/vol patterns around MPC & CPI release windows | H-005 REJECTED 2026-07-16 (return windows, as tested) | mpc_history, inflation_gdp, pit_event_database |

**F11 post-verdict generation review (H-005, 2026-07-16):**
- *Patterns deserving their own hypothesis:* none from returns — gross
  post-MPC window effect ≈ 0 in NGXBNK vs ASI across ~47 events. What
  remains genuinely untested in F11: VOLATILITY patterns around
  announcements (position-sizing value even without direction), and
  pre-announcement drift.
- *Unexpected relationship:* the cleanest cost-arithmetic result yet — any
  NGX overlay strategy pays ~4% per full-NAV round trip, so an event class
  must plausibly move a sector by MULTIPLES of that per event to be worth
  testing as a switching strategy. At ~11 switches/yr this hypothesis needed
  ~40%/yr gross alpha just to break even.
- *Cross-program implication (feeds H-003 design):* short-window event
  strategies on NGX are cost-doomed as full-switch overlays. H-003's
  catalyst rotation should therefore target SLOW catalysts (recapitalisation
  cycles, multi-month directives) where positions persist across quarters —
  which is also its original mechanism claim. Evidence now constrains the
  design space before H-003 testing begins: its prereg should exclude
  sub-monthly holding periods.
- *Different mechanism, not dead end?* The rejected mechanism was
  "days-scale repricing"; the slow-repricing mechanism remains open and is
  precisely H-003's territory. No new hypothesis registered — the finding
  sharpens an existing queued one instead.
| F12 | Cross-asset lead-lag | Oil → NGXOILGAS (and FX) transmission with investable lag | H-004 REJECTED 2026-07-16 (as tested) | brent, fx_parallel_market_history |

**F12 post-verdict generation review (H-004, 2026-07-16)** — the four
standing questions, answered in writing:
- *Patterns during validation deserving their own hypothesis:* quarterly
  cells uniformly positive in development (+3.2% to +6.6%) while monthly
  cells uniformly negative — the third consecutive demonstration (H-001
  synthetic, H-001 real, H-004) that rebalance-frequency cost drag dominates
  weak signals on NGX. Candidate idea: cost-aware signal gating (act only
  above a signal-strength threshold) — a refinement class applicable to ANY
  future model, worth a hypothesis once one signal survives placebo.
- *Unexpected relationships:* placebo p=0.079 — much nearer the threshold
  than H-001's 0.55. Not evidence of an edge; recorded only as a measured
  fact about this sample.
- *Dataset combinations suggesting new programs:* Brent × FX
  parallel-spread × OILGAS — transmission may be state-dependent on the FX
  regime. Requires F7 data (parallel FX history, ethics gate pending).
- *Different mechanism rather than dead end?* Development-period transmission
  with final-OOS failure (2025–26) is *consistent with* a mechanism change
  after subsidy removal/downstream deregulation (sector earnings decoupling
  from crude). A state-conditioned variant is admissible as a NEW hypothesis
  only after F7 data exists — deliberately NOT registered today to avoid
  multiplying weak ideas without new evidence.

## Keystone analysis (datasets by number of families served)

| Dataset | Families | Count |
|---|---|---|
| ngx_daily_pricelist_forward | F2 F3 F4 F5 F6 F8 | **6** |
| pricelist_wayback_backfill | F2 F3 F4 F5 F8 | **5** |
| dividend_earnings_calendar | F2 F5 F6 | 3 (+enables TR benchmarks everywhere) |
| pit_event_database | F1 F7 F11 | 3 (+context layer for all) |
| index_membership_pit | F2 F3 | 2 (+correctness precondition for F4-F6, F8) |
| xissuer_disclosure_archive | F5 F9 | 2 (+raw substrate for future NLP families) |
| fx_parallel_market_history | F7 F12 | 2 |
| others | 1–2 each | |

**Reading:** the per-stock price list (forward + backfill) is the keystone —
six families are unbuildable without it, and it is also the time-gated one.
Membership PIT is a *correctness precondition* masquerading as a two-family
dataset: without it, every constituent-level family inherits survivorship
bias. These two plus the dividend calendar form the acquisition core.

## Rules

1. A generativity score without named families here is invalid.
2. When a new family is conceived, it is added here with status and
   dependencies BEFORE any signal work — the map is also the idea ledger's
   front door (families graduate into numbered hypotheses in the ledger).
3. Families marked `speculative` justify cheap optionality purchases only,
   never expensive acquisitions on their own.
