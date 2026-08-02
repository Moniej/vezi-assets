# Phase 28 — Quant Engine Audit

*2026-08-02, per the owner's Phase 28 instruction. Full audit of every
hypothesis this platform has ever tested, verified directly against
`docs/FACTOR_REGISTRY.md` and `data/registry.sqlite` (not restated from
memory).*

## Confirmed factors

| ID | Family | Status | Note |
|---|---|---|---|
| H-011 | Size | **CONFIRMED** (2026-07-22) | The platform's only validated factor. Placebo p=0.0099, positive net excess in dev AND untouched OOS, 6/6 plateau. Central caveat: capacity is the worst of any hypothesis tested (median leg ₦694k) — a real, valid, but small-AUM strategy, not broadly scalable. |

## Rejected factors, categorized by failure type

| ID | Hypothesis | Failure category | Why |
|---|---|---|---|
| H-001 | Sector momentum | **Universal / structural** | Sector-level breadth (~8 bets/yr) cannot host detectable alpha regardless of regime — a breadth ceiling, not a timing problem. |
| H-003 | Event catalyst rotation | **Universal / structural** | ~10 events total; underpowered by construction, no regime could fix this. |
| H-004 | Macro (oil→sector) | **Regime-dependent** | Sign reversed after the 2023 float — the SAME relationship behaved differently pre- and post-float. This is the first of two pieces of evidence motivating H-012. |
| H-005 | Macro/Event (MPC windows) | **Universal / structural** | Gross window effect ≈ 0; ~4%/round-trip costs dominate every sub-monthly design regardless of when it's run. |
| H-006 | PEAD (reaction-rank) | **Improperly conditioned** | The underlying event-membership effect is real and large (gross +16.69%/yr, corrected p=0.000) — the RANKING added nothing. This was a mis-specified test (tested magnitude-ranking when the real question was membership), not a universal or regime failure. |
| H-007 | Cross-sectional momentum | **Universal / structural** | Gross effect real but ~3× smaller than its own transaction-cost bill at any point in the sample — a cost-structure ceiling. |
| H-008 | Low volatility | **Regime-dependent (candidate)** | Robust rejection across three violent NGX regime transitions (2016 FX crisis, 2020 COVID, 2023 float) — the platform's OWN memo attributes this to operating exclusively through shock periods. Second piece of evidence motivating H-012. |
| H-009 | Turnover-budgeted momentum | **Universal / structural (power)** | Near-miss (p=0.069) but only ~9 independent decisions in 9 years — a statistical-power ceiling, not a regime or cost problem (the cost problem WAS fixed here, per its own memo). |
| H-010 | Pooled overlapping-cohort momentum | **Improperly conditioned** | Designed to fix H-009's power problem by pooling cohorts — but real cohort correlation (~0.75) showed the "independent bets" premise was false; a methodology flaw (correlated cohorts), not evidence the underlying momentum effect fails in every regime. |
| **H-012** | **Regime-Conditional Low-Vol Gate** | **Tested this session — see below** | |

**Which failures were universal**: H-001, H-003, H-005, H-007, H-009 — five
of nine, each hitting a structural ceiling (breadth, cost, or power) that
no amount of regime-conditioning or re-specification would fix. These are
correctly closed; do not retest without a materially different signal.

**Which failures may depend on regime**: H-004 and H-008 — the only two
with direct evidence of regime-sensitivity (a sign reversal; a memo's own
attribution to shock periods). These are the two hypotheses this
platform's own prior research (`docs/WAVE_3_RESEARCH_DIRECTIONS.md`)
flagged as motivating a regime-conditioning methodology.

**Which lacked proper conditioning (test the wrong thing)**: H-006 (tested
ranking when the real question was membership) and H-010 (tested pooling
when the real question was independence) — both are mis-specified-test
failures, a distinct category from both "universal" and "regime-dependent."

## Phase 28 conclusion

The evidence supported exactly one immediately actionable next step:
**test whether H-008's regime-sensitivity is real**, via a pre-declared,
look-ahead-audited regime gate — H-012. See
`docs/PHASE29_REGIME_FRAMEWORK_2026-08-02.md` for the full result.
