# Data Gap Report — ranked by expected research value for H-003

*2026-07-15. Rank = (catalyst relevance to the H-003 mechanism) ×
(history depth × event count = statistical power) × (acquisition feasibility)
÷ (effort). Reuse value for other hypotheses noted — the database must
outlive H-003.*

| # | Dataset | Why it ranks here | Effort | Reuse beyond H-003 |
|---|---|---|---|---|
| 1 | **CBN MPC decision history (2012→)** | Most systematic catalyst class: ~85 dated, numbered primary documents; market-scope; enables the first properly-powered event study. Without it H-003 has no statistical backbone. | Medium (HTML+PDF parse, probed reachable) | Rate-regime definitions for ALL future hypotheses |
| 2 | **CBN banking circulars incl. recapitalisation timeline** | Banking is NGX's dispersion engine and the founding example of the catalyst premise; recap 2024–26 + the 2010s forbearance/dividend directives give repeated sector-scoped events. | Medium (crawl + manual triage) | Banking-sector anything |
| 3 | **NGX notices: index reviews, suspensions, listings/delistings** | Dual value: catalyst class AND fixes `index_membership.announced_date` — the survivorship defense constituent-level work requires. | Medium-high (REST endpoint discovery, else HTML) | Unblocks ALL constituent-level research |
| 4 | **Dividend/earnings calendar for top-20 constituents** | Corporate catalyst class for H-003 **and the entire blocker for H-002**; dividend fields feed total-return construction. Highest cross-hypothesis value per row. | High (portal crawl per ticker) | H-002 wholesale; TR benchmarks |
| 5 | **Brent daily series (+ derived shock events)** | Oil & Gas was the top contributor in the rejected H-001 attribution — commodity catalysts are the obvious candidate mechanism. Near-zero effort. | Trivial (CSV) | Macro covariate everywhere |
| 6 | **Inflation release dates + surprises (2016→)** | Monthly cadence adds event count; surprise construction needs consensus estimates which may not exist for Nigeria — flag: may degrade to release-day-only events. | Medium | Macro regime work |
| 7 | **Daily official/NAFEM FX series** | Regime covariate + derived FX-shock events; June 2023 already proved this class moves sectors. | Low-medium | fx_rates table feeds everything |
| 8 | **NAICOM insurance recap saga (2019–21)** | Natural experiment: announced, litigated, suspended — rich announced-vs-effective structure; but single episode, low power. | Low (manual, ~20 events) | Insurance sector work |
| 9 | **SEC directives** | Real but diffuse; price-sensitivity per directive is low on average. | Medium | Market-structure studies |
| 10 | **PenCom reforms; fiscal/tax events** | Sparse, hard-to-date, weakest documented sector linkage. Acquire opportunistically. | Low each | Pension/consumer studies |
| 11 | **GDP releases** | Quarterly, heavily anticipated, weak sector differentiation. | Low | Context only |

## Sequencing recommendation

**Sprint 1 (before any H-003 signal work):** #1 MPC + #5 Brent + #2 recap
timeline. This yields one high-count systematic class, one continuous
covariate, and the flagship sector catalyst — the minimum on which an honest
event study can run. **Sprint 2:** #3 NGX notices + #7 FX daily.
**Sprint 3:** #4 dividends/earnings (larger effort; consider whether H-002
co-funding justifies pulling it forward).

## Known unknowns to resolve during Sprint 1

- NGX doclib REST endpoint names for notices/disclosures (probe returned 404
  on guessed paths; discover via browser network inspection).
- NBS historical *release-date* availability pre-2016.
- Whether any Nigerian consensus-estimate series exists for inflation
  surprises (if not, "surprise" events are unbuildable and must be dropped
  from the taxonomy's testable set — recorded, not fudged).
- FRED connectivity from this environment (timed out once; retry or EIA).

## Standing statistical warning

Even at full acquisition, catalyst classes other than MPC (~85 events) and
corporate actions (hundreds) will have **single- or low-double-digit event
counts**. Per-class event studies will be underpowered; H-003's design must
pool across classes with pre-registered groupings, or the per-class findings
will be Inconclusive by construction. This warning is to be quoted in the
H-003 design document before any signal is built.
