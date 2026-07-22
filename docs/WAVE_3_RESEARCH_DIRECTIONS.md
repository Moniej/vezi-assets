# Wave 3 Research Directions — Gap Analysis, Candidates, Prioritization

*2026-07-22. Continuation of `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`
(read that first — every judgment here is justified against evidence from
H-001 through H-009, not asserted fresh). Governance unchanged: no
threshold relaxed, no rerun of a rejected design, no p-hacking. This
document recommends a DIRECTION; it does not itself constitute a
pre-registration — each selected candidate still requires its own full
prereg before any run, per convention.*

---

## Phase 3 — Research Gap Analysis

Against the user's list, mapped to current platform state:

| area | status | evidence |
|---|---|---|
| Multi-factor ranking models | untouched | requires ≥2 validated factors first (0 exist) — premature |
| Event-driven strategies | partially explored | H-003 (sector catalyst, rejected/breadth), H-006 (PEAD ranking, rejected/methodology) — corporate-action-specific events (buybacks, rights issues) untested |
| Regime-aware investing | **untouched as a design paradigm** | strongly motivated by cross-cutting concentration pattern (Lessons §3/6) — highest-value gap |
| Portfolio construction | GATED | correctly deferred per charter (needs ≥2 validated factors) |
| Risk models | partial (per-experiment only) | portfolio-level risk engine correctly GATED |
| Liquidity-aware models | data ready, untouched | ADTV/capacity already measured per-experiment; a liquidity PREMIUM hypothesis never tested |
| Capacity-aware models | infrastructure exists | capacity reported every run; never itself the alpha source |
| Sector-neutral ranking | untouched (construction technique, not standalone) | could reduce the concentration problem in a future momentum retest; not a standalone family |
| Relative valuation (Value) | **untouched, data mostly blocked** | EPS/P.E. extraction failed validation (`reports/eps_pe_extraction_status.md`); a price-only value proxy is not credible without earnings/book data |
| Cross-sectional ML | untouched | premature — governance requires economic rationale before signal construction; ML without ≥1 validated linear factor as a baseline is a step backward, not forward, per "never optimize for backtests" |
| Network effects | untouched | no ownership/analyst/supply-chain data exists on this platform |
| Corporate action behavior | **data ready (97% archive), signal untested** | genuinely new mechanism, high readiness |
| Dividend effects | **partially ready** | payer-status buildable now; yield MAGNITUDE blocked on DPS extraction |
| Macro-conditioned factors | H-004/H-005 touched macro directly (rejected); macro as a CONDITIONING input (not a standalone signal) is untested | ties directly into regime-aware gap |
| Industry leadership models | untouched | would need sector classification depth beyond current IRU exclusion rules |
| Execution optimization | untouched, and premature | no validated factor exists to execute yet |

**Highest-value gaps, in order**: (1) regime-aware conditioning — no
hypothesis has tested it as a design paradigm despite two independent
pieces of evidence (H-004, H-008) pointing straight at it; (2) corporate
action behavior — data readiness just crossed the threshold this session
(archive 97% complete) and the mechanism is genuinely untested; (3) Size
via the market-cap panel — data sitting validated and unused; (4) dividend
payer-status — buildable today at low engineering cost; (5) the
statistically strongest LEAD in the entire program (H-009's near-miss) —
not a "gap" in the traditional sense, but the highest-confidence
improvement-per-unit-effort available.

---

## Phase 4 — Wave 3 Candidates (five, ranked by write-up order only —
prioritization is Phase 5)

### C1 — Pooled Overlapping-Cohort Momentum
- **Economic rationale**: identical to H-007/H-009 (slow information
  diffusion, thin analyst coverage, no-shorting asymmetry). NOT proposed
  as a fresh momentum bet — proposed because H-009 isolated turnover as
  the ONLY problem and left statistical power as a NEW, separately
  fixable problem.
- **Why this should exist**: it is the only wave-3 candidate that
  responds to a *positive*, plateau-clean, all-regime-positive result
  rather than an ambiguous or negative one. Per the user's own
  "avoid variations unless compelling reason" instruction — this is that
  reason.
- **Source of alpha**: same as H-007/H-009 — trend persistence in
  under-covered names.
- **Required datasets**: none new — same price panel, same IRU.
- **Statistical power estimate**: staggering formation dates (e.g. 4
  offset cohorts, each annual, entering a quarter apart) could raise
  independent decisions from ~9 to ~30-35 over the same window while
  keeping EACH cohort's own turnover near H-009's low level — the actual
  power gain depends on cohort correlation, which must be measured, not
  assumed, in the prereg's own power analysis.
- **Expected turnover**: per-cohort turnover ~H-009's (~0.65×/yr in
  rehearsal); aggregate portfolio turnover higher due to overlapping
  entries/exits — must be modeled explicitly before this prereg is
  written, not assumed low by analogy.
- **Capacity**: similar or better than H-009 (₦11.8m median leg capacity)
  — more, smaller, staggered trades typically raise capacity.
- **Engineering effort**: MODERATE — `backtest_xs.py` needs a
  multi-cohort target-blending extension; no new data.
- **Implementation difficulty**: moderate — the main risk is
  double-counting or unintentionally correlated cohorts inflating
  apparent decision count without truly adding independent information.
- **Main failure risks**: cohort correlation could be near 1.0 (offset
  formation dates might just be smoothed versions of the same signal,
  not independent bets) — this would reproduce H-009's power problem
  under a different name; must be tested directly, not assumed away.
- **Why different from H-001–H-009**: no prior hypothesis tested a
  multi-cohort construction; H-007/H-009 both used a single reconstitution
  calendar.

### C2 — Regime-Conditional Factor Gate
- **Economic rationale**: H-004's relationship reversed sign after the
  2023 float; H-008's low-vol mechanism needs a calm market NGX hasn't
  had. Both point at the same fix: measure a factor's exposure ONLY
  within a defined macro-stability regime, using data the platform
  already has (FX events, MPC decisions, the diagnostics-validated
  verified-market calendar).
- **Why this should exist**: it directly tests the cross-cutting finding
  from the retrospective (concentration is structural, not noise) as a
  DESIGN CHOICE rather than reporting it as a post-hoc caveat, as it was
  in every prior hypothesis's regime-attribution section.
- **Source of alpha**: not a new factor per se — a conditioning layer.
  First application: re-test the ALREADY-BUILT low-vol signal
  (`xs_vol`, validated engine) restricted to a defined "stable regime"
  (e.g., ex-ante: no FX devaluation event or MPC emergency action within
  the trailing 6 months) — this reuses H-008's exact signal construction,
  so it is a natural-experiment retest of a REJECTED hypothesis under a
  materially different, pre-declared condition, not a rerun.
- **Required datasets**: existing `macro_series`/`events` tables (already
  used in H-004/H-005); a regime-classification rule must be
  pre-registered BEFORE seeing any regime-conditional results (critical —
  the regime definition itself must not be chosen by looking at which
  windows perform well, or this becomes pure p-hacking dressed as
  methodology).
- **Statistical power estimate**: LOWER than the unconditional H-008 test
  by construction (a stable-regime subset is a strict subset of the full
  window) — this is the central risk, stated up front, not discovered
  after the fact.
- **Expected turnover**: same as H-008 base (quarterly, ~1.29×/yr
  observed) within active windows; effectively zero when regime-gated out
  (fully in benchmark).
- **Capacity**: similar to H-008.
- **Engineering effort**: LOW-MODERATE — a regime-gate wrapper around the
  existing `xs_vol` target construction (or applied to the benchmark
  sleeve logic already built for `xs_event`).
- **Implementation difficulty**: the regime-definition pre-registration
  discipline is the hard part, not the code.
- **Main failure risks**: reduced sample size could make ANY verdict
  underpowered (the same failure mode as H-009, compounded); regime
  definition could accidentally leak information if not fixed rigorously
  before any results are seen.
- **Why different from H-001–H-009**: no prior hypothesis conditioned a
  signal on a pre-declared macro regime; all nine were unconditional
  across their full windows.

### C3 — Corporate-Action Event Drift (buybacks, rights issues, bonus
issues)
- **Economic rationale**: corporate actions carry information about
  management's view of value (buybacks signal undervaluation; rights
  issues can signal capital need/dilution pressure) and mechanically
  alter float/ownership structure — a DIFFERENT information channel from
  PEAD's earnings-surprise mechanism, and untouched by H-006.
- **Why this should exist**: the corp-actions archive just crossed 97%
  completeness this session (11,187/11,546 PDFs) — the highest-readiness
  genuinely new-family dataset on the platform, and the ONLY event
  category the platform has invested heavily in archiving without ever
  testing.
- **Source of alpha**: post-announcement drift following a classified
  corporate-action TYPE (not reaction-ranked — H-006 already proved
  ranking-by-magnitude fails; this tests EVENT-TYPE membership, the
  lesson directly carried over).
- **Required datasets**: `corporate_actions_calendar_classified.csv`
  (11,546 filings, TYPE-classified) — usable for event TIMING and
  CLASSIFICATION today; the amount-level fields (DPS, rights terms)
  remain thin (~397 rows extracted, unvalidated) and should NOT be relied
  on — the hypothesis must be designed around event TYPE and TIMING only.
- **Statistical power estimate**: depends heavily on how many
  buyback/rights/bonus events are classified with reliable dates — needs
  a scoping pass (count events by type) BEFORE pre-registration; likely
  fewer events than PEAD's 8,685 Financial Statements filings, since
  buybacks/rights issues are rarer corporate actions than quarterly
  results.
- **Expected turnover**: event-driven, similar structural risk to H-006
  (capped-book turnover was badly underestimated there) — this prereg
  must model turnover explicitly, informed by H-006's specific error.
- **Capacity**: unknown until the event set is scoped.
- **Engineering effort**: MODERATE — reuses `backtest_xs.py`'s
  `xs_event` machinery (built for H-006) with a different event source
  and TYPE-based (not reaction-ranked) selection; classification logic
  needs validation against a few known anchors before trusting it.
- **Implementation difficulty**: moderate-high — the corp-actions
  classification pipeline itself was never promoted to evidence grade;
  this candidate implicitly asks that work to be validated first.
- **Main failure risks**: same failure mode as H-006 (turnover
  under-estimation) if the event-book construction is reused carelessly;
  event classification errors could silently corrupt the event set.
- **Why different from H-001–H-009**: entirely new information channel
  (ownership/capital-structure signal vs price-trend or earnings-surprise
  signal); first use of the corp-actions archive as a research input
  rather than a data-quality tool.

### C4 — Size (market-cap panel)
- **Economic rationale**: small/illiquid names may carry a structural
  premium for bearing the very capacity constraints this platform's
  capacity reports have documented in EVERY prior hypothesis (every IC
  memo shows 90%+ of trade legs rejected at ₦1bn AUM) — if a premium
  exists, it is compensation for exactly that friction.
- **Why this should exist**: the market-cap panel (328,023 rows,
  validated 2026-07-22, 0.39% implausible-jump rate) is the single
  highest-readiness, fully-validated, completely UNUSED dataset on the
  platform.
- **Source of alpha**: cross-sectional size rank within the IRU (full-
  issue cap, NOT float-adjusted — shares-outstanding data doesn't exist
  yet, a stated limitation, not a blocker).
- **Required datasets**: `data/reference/market_cap_panel.csv` (ready) +
  existing price panel.
- **Statistical power estimate**: same breadth as H-007/H-008 (~100-name
  IRU, quarterly) — comparable decision count to H-007 (35), i.e. the
  program's BEST-POWERED per-stock design pattern, not the worst.
- **Expected turnover**: size ranks are sticky (similar argument to
  H-008's vol-rank stickiness claim — which did NOT hold up as strongly
  as expected in that case; this must be measured, not assumed, exactly
  as H-008 taught us to be honest about upfront).
- **Capacity**: WORSE than any prior hypothesis by construction — a size
  factor deliberately selects the most capacity-constrained names. This
  should be reported prominently and honestly, not softened; it may be
  the platform's first hypothesis where a validated signal is
  immediately flagged scalability-limited rather than signal-rejected.
- **Engineering effort**: LOW — `backtest_xs.py`'s `xs_rank`/`xs_vol`
  pattern generalizes directly to a size score; the market-cap panel
  needs a small loader analogous to `load_panel`.
- **Implementation difficulty**: low, mechanically; the interpretation
  difficulty (capacity vs signal separation) is where care is needed.
- **Main failure risks**: full-issue (not float-adjusted) cap could
  proxy for something else (e.g., cross-holding structure) rather than
  genuine tradeable float scarcity — a real construct-validity risk
  worth stating in the prereg.
- **Why different from H-001–H-009**: entirely new family; first
  hypothesis built on the market-cap panel; first hypothesis to expect
  (not discover after the fact) severe capacity constraints as part of
  its own economic story.

### C5 — Dividend Payer-Status Tilt
- **Economic rationale**: in a retail-dominated, low-institutional-
  coverage market, a track record of paying dividends may function as a
  quality/stability signal distinct from any price-based measure — not a
  yield-magnitude claim (that data isn't ready), a PAYER-vs-NON-PAYER
  classification claim.
- **Why this should exist**: the ex-div closure calendar (1,044 events,
  217 symbols, validated 2026-07-22) makes this buildable TODAY without
  waiting on the stalled EPS/dividend-amount parser
  (`reports/eps_pe_extraction_status.md`) — the lowest-engineering-cost
  candidate in this wave.
- **Source of alpha**: quality/stability premium proxied by payer
  consistency (e.g., paid in ≥N of the trailing M years), not yield size.
- **Required datasets**: `data/reference/exdiv_closure_calendar.csv`
  (ready) + price panel.
- **Statistical power estimate**: 217 symbols have closure events at some
  point 2016-2026, but the ACTIVE-PAYER subset at any given formation
  date will be smaller and needs scoping before prereg — likely
  comparable to or somewhat below H-007's breadth.
- **Expected turnover**: LOW — payer status changes rarely (a company
  doesn't start/stop paying dividends often); this is the strongest
  genuine low-turnover candidate in the wave, though H-008 taught us not
  to assert this without measuring it.
- **Capacity**: likely favorable — established dividend payers on NGX
  tend to be larger, more liquid names (banks, consumer staples) — a
  directly testable, not assumed, comparison per H-008's own precedent.
- **Engineering effort**: LOW — simplest data-loading task of the five
  candidates; reuses `xs_rank`-style eligibility machinery with a payer
  flag instead of a continuous score.
- **Implementation difficulty**: low, but the ECONOMIC framing is
  intentionally narrow (payer status, not yield) — care is needed not to
  overclaim what a binary flag can support.
- **Main failure risks**: could simply proxy for size/liquidity (large,
  established firms both pay dividends AND are less volatile) rather than
  carrying independent information — an orthogonality check against
  size (C4, if run) and low-vol (H-008, already rejected) would be
  needed before over-interpreting any positive result.
- **Why different from H-001–H-009**: entirely new family; first
  hypothesis to use the dividend/closure data as a RESEARCH input rather
  than a data-quality/gate-remediation tool.

---

## Phase 5 — Prioritization

Scored 1 (low) – 5 (high) on ten dimensions. "Expected research value" =
information gained per unit of program risk, not expected P&L.

| dimension | C1 Pooled Momentum | C2 Regime-Gate | C3 Corp-Action Drift | C4 Size | C5 Dividend Payer |
|---|---|---|---|---|---|
| Expected research value | 5 | 5 | 3 | 4 | 3 |
| Novelty vs H-001–009 | 2 | 5 | 4 | 5 | 4 |
| Statistical power (ex-ante) | 3 | 2 | 2 | 4 | 3 |
| Engineering effort (5=low effort) | 4 | 4 | 2 | 4 | 5 |
| Data availability (5=ready now) | 5 | 4 | 3 | 5 | 5 |
| Economic plausibility | 4 | 4 | 3 | 4 | 3 |
| Capacity outlook | 3 | 3 | 3 | 1 | 4 |
| Expected robustness (placebo survival prior) | 3 | 2 | 2 | 3 | 2 |
| Portfolio usefulness if validated | 4 | 3 | 3 | 3 | 3 |
| Long-term platform contribution | 4 | 5 | 3 | 4 | 3 |
| **Total (/50)** | **37** | **37** | **28** | **37** | **35** |

### Score justifications (why, not just what)

- **C1 (Pooled Momentum) — 37.** Highest research-value and robustness
  scores in the field: this is the only candidate built directly on a
  positive, plateau-clean, all-regime-consistent result (H-009), so the
  prior probability of a real effect is objectively higher than for any
  untested family. Novelty scored LOW (2) deliberately — it is a
  momentum variant, and the framework should not let strong priors
  disguise that fact; the user's "compelling reason" bar is met on
  evidence, not on novelty.
- **C2 (Regime-Conditional Gate) — 37.** Highest novelty AND highest
  long-term platform contribution: this is a REUSABLE METHODOLOGY, not a
  single-use factor — every future hypothesis could eventually be
  offered a regime-conditional variant once this is built and validated.
  Statistical power scored LOW (2) honestly: conditioning on a regime
  subset directly shrinks the sample versus the already-marginal
  H-008 test it's built on. This is the highest-effort-to-verify,
  highest-ceiling candidate in the set.
  Its total is tied because it maximizes long-term value while accepting
  the same
  power risk that has now bitten the program twice.
- **C3 (Corporate-Action Drift) — 28, lowest score.** Genuinely novel and
  data-ready in the narrow sense (archive complete), but scored down
  hard on engineering effort (the classification pipeline was never
  validated to evidence grade — this candidate quietly asks for that
  work too) and on robustness prior (H-006 already showed this exact
  event-book construction pattern underestimates turnover badly; C3
  inherits that risk without yet inheriting the fix). Recommended for a
  LATER wave, once its event set is scoped and the classification
  pipeline is validated as its own deliverable.
- **C4 (Size) — 37, tied for highest.** Best data availability (fully
  validated, zero new engineering for the base signal) and best novelty
  given the mechanism (structural liquidity compensation, unlike
  anything tested so far) — but capacity scored the WORST of any
  candidate (1/5) by the factor's own economic logic: it deliberately
  selects the most illiquid names in the universe. This is disclosed
  as a first-class scoring dimension, not a footnote, per H-008's lesson
  about honest upfront disclosure.
- **C5 (Dividend Payer) — 35.** Lowest engineering effort of the five
  (5/5) and best data readiness tied with C4, but capped by a real
  construct-validity concern (may just be a size/quality proxy, not
  independent information) and by deliberately narrow economic framing
  (payer status, not yield magnitude) that limits its ceiling even if it
  validates.

### Recommendation

**C1 (Pooled Momentum) and C4 (Size)** are the strongest immediate pair:
C1 carries the program's best evidentiary prior of any candidate; C4 is
fully data-ready with zero new engineering and opens a genuinely
untested family. Between C1 and C2 (tied scores), C1 is recommended to
go first because its engineering path is more contained (extending an
existing signal's cohort structure vs. building and pre-registering a
NEW regime-classification methodology that must itself avoid look-ahead
bias in its own definition) — C2 is the stronger LONG-TERM bet and should
be the next wave after C1/C4, once a regime-definition methodology can be
pre-registered with full rigor rather than rushed alongside two other
candidates.

C3 should wait for its own scoping/validation pass before entering a
pre-registration wave. C5 is a good LOW-COST parallel candidate if
program bandwidth allows a third concurrent research thread — but the
platform's own ≤2-active-hypotheses rule caps this wave at two regardless.

---

## Phase 6 — Investment Platform Perspective

Evaluating each candidate by what it adds to the platform, not only
whether it might validate:

- **C1 (Pooled Momentum)**: if validated, becomes the Validated Alpha
  Library's first entry AND the Continuous Research Engine's first
  concrete example of iterating on a near-miss rather than abandoning it
  — a reusable PROCESS precedent, not just a factor.
- **C2 (Regime-Conditional Gate)**: strengthens the platform
  architecturally regardless of any single factor's outcome — a
  validated regime-classification methodology becomes a permanent
  Feature Engineering Layer component available to every future
  hypothesis (Company Intelligence Engine's eventual "macro sensitivity"
  field depends on exactly this kind of infrastructure).
  This is the candidate most aligned with "building a platform, not
  finding one strategy."
- **C3 (Corporate-Action Drift)**: if it eventually validates, it
  directly feeds a future Corporate Events module of the Company
  Intelligence Engine — but its immediate contribution is lower until
  the classification pipeline itself is validated as reusable
  infrastructure (a prerequisite more than a factor).
- **C4 (Size)**: essential for an eventual Risk Engine (size is a
  standard risk-model factor even independent of whether it earns a
  premium) and for realistic Portfolio Construction (capacity-aware
  sizing needs exactly this data) — high platform value even if the
  ALPHA claim itself is eventually rejected, because the risk-model use
  case survives either verdict.
- **C5 (Dividend Payer)**: modest platform contribution beyond its own
  verdict — useful mainly as an input feature for a future
  multi-factor Quality composite once ≥2 factors exist to combine.

**Overall platform-level judgment**: C1 and C4 offer the best combination
of near-term evidentiary strength (C1) and durable, verdict-independent
platform infrastructure value (C4 — a Risk Engine input either way).
C2 is the single highest long-term-architecture bet in the entire
candidate set and deserves a dedicated future wave rather than being
folded in under time pressure alongside two others.

---

*Per governance: this document recommends a direction. Full
pre-registrations for the selected wave-3 candidate(s) — including
exact universe, cost model, validation plan, and Expected Interaction
section — are drafted separately and shown to the owner before any run,
per established convention. No hypothesis ID has been created by this
document.*
