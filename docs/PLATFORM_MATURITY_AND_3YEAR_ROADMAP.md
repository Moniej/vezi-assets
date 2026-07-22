# Fund Alpha — Platform Maturity Assessment and 3-Year Roadmap

*2026-07-22. Produced per owner directive, BEFORE any H-010 work. Builds
on `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md` and
`docs/WAVE_3_RESEARCH_DIRECTIONS.md` — read those first; this document
treats their findings as inputs, not repeats them. Scope: architecture
classification, dependency mapping, maturity scoring, a 3-year alpha
roadmap, platform-impact-weighted research prioritization, and an
investment-firm-readiness assessment. No hypothesis is proposed or
pre-registered here.*

---

## Phase 1 — Architecture Review

Every implemented component, classified into exactly one of four
categories. "Implemented" means code or data that exists today, not
aspiration.

### Production Ready (evidence-grade, complete)

**Governance & orchestration**: `registry.py` (immutable, SQL-trigger
enforced, 160+ experiments), `ledger.py` (hypothesis ledger with
permanent freeze — H-001 frozen, 9 hypotheses resolved), `runner.py`
(config-driven execution, holdout guard, gate refusal — proven across
every hypothesis), `phase4.py` (validation orchestrator — stability map,
Holm/BH, placebo, walk-forward, IC memo — proven in BOTH sector and
cross-sectional variants).

**Validation primitives**: `stats.py` (Holm/BH/placebo p-value),
`metrics.py`, `failure_conditions.py` (signal-quality/scalability
separation — this distinction correctly prevented every capacity finding
from masquerading as a signal verdict across 9 hypotheses),
`confidence_rating.py`, `ic_report.py` (one bug found and fixed this
session — hardcoded H-001 text in every memo since H-003; quantitative
content was never affected).

**Data infrastructure**: `db.py` (bitemporal PIT reads — the single most
load-bearing module in the platform; every `*_asof` reader has been
exercised by 9 hypotheses plus the gate-remediation session without a
known defect), `coverage.py` (Coverage Gate v2 — PASSED 2026-07-21, 12
ready years, runner-enforced), `universe.py` (IRU v2 — stable across the
entire per-stock era), `diagnostics.py`, `staging.py`.

**Parsers** (each independently validated against a stated pass bar
before use — the platform's most consistently well-executed engineering
pattern): `pricelist_parser.py` (v2, glued-token repair, 99.3%+ row
confidence), `dol_price_parser.py` (99.4% vs known closes), `list2_parser.py`
(100%/99.9%), `gainers_parser.py`, `page_layout.py` (the char-level
foundation all of the above depend on).

**Engines**: `backtest_xs.py` (cross-sectional, rank/vol/event modes —
built and rehearsed 2026-07-22, used for 4 of the 9 hypotheses without an
engine defect being found); `backtest_lite.py`/`engine_full.py`
(sector-level — engineering is production-grade, PROVEN across H-001/003/
004/005, but the RESEARCH FAMILY it serves is closed per the per-stock
pivot; keep the classification separate from the family's relevance).

**Data assets**: `equity_prices` (3 validated sources, gate-passed),
earnings calendar (10,690 filings), ex-div closure calendar (1,044
events), gainers transitions, official prev-close, market-cap panel
(328,023 rows, validated 2026-07-22), MPC decisions (80), cost schedule.

### Research Ready (functional, awaiting validated alpha)

**`alpha_engine.py`** — the textbook example of this category. Fully
built, tested, and CORRECT: with zero confirmed hypotheses it emits an
honest `no_position` recommendation with full pipeline transparency
rather than fabricating a signal. Nothing needs to change here except
wiring an adapter the day a hypothesis is confirmed — the architecture
was right from day one.

**`signal.py`** score builders (momentum, event_window,
catalyst_activity, macro_gate) — functional, all four have been exercised
by at least one hypothesis (all rejected). They remain available
building blocks, not validated factors.

### Experimental (active or paused research, unproven)

**`backtest_xs.py`'s event-book construction pattern** — the engine
mechanics are validated (rehearsed correctly), but H-006 showed the
DESIGN PATTERN (capped-slot competitive book) turns over ~10× a naive
estimate. The pattern itself needs a redesign before reuse, not just a
different event source (relevant directly to Wave-3 candidate C3).

**`dol_eps_parser.py`** — built, tested at scale, and NEGATIVELY
resolved: two extraction heuristics both failed the pre-declared 95%
validation bar (58%, then 34%). Kept in the tree as a documented dead end
(`reports/eps_pe_extraction_status.md`), not deleted, per the platform's
"never fabricate, unknown stays unknown" discipline — but it is not
usable today.

**Corp-actions structured extraction** (`build_corp_actions_db.py`,
`corporate_actions_extracted.csv`) — ~397 rows, most fields unpopulated,
never promoted to evidence grade. The RAW ARCHIVE behind it (11,546 PDFs,
97% downloaded) is Production Ready; the STRUCTURED extraction from it is
not.

### Future Infrastructure (intentionally deferred)

**Company Intelligence Engine, Ranking Engine, Portfolio Construction
Engine, portfolio-level Risk Engine, Performance Attribution** — zero
code exists for any of these. Correctly deferred: building them against
zero validated factors would itself violate "never invent alpha." (Per-
experiment risk measurement — drawdown, capacity, concentration — IS
Production Ready; it is the PORTFOLIO-level aggregation across multiple
factors that doesn't exist yet, because no portfolio exists yet.)

**Continuous Learning / decay-monitoring operations** — a design exists
(`docs/HYPOTHESIS_DISCOVERY_DESIGN.md`) but nothing is built; correctly
gated behind having a factor to monitor in the first place.

**Regime-classification methodology, multi-cohort momentum pooling** —
proposed in Wave 3 candidates C1/C2, zero code today.

**Total-return / dividend-magnitude infrastructure** — blocked on the
EPS/dividend parser's unresolved status (Experimental, above).

**Shares outstanding / float-adjusted size, financial statements /
fundamentals, analyst estimates, news, alternative data, OCR pipeline for
scanned filings** — not acquired; several are explicitly user-gated
(OCR), others simply not yet prioritized.

---

## Phase 2 — Dependency Map

```
Data Layer  (Production Ready)
    |  gates on: Coverage Gate v2 (PASSED)
    v
Research Layer  (Production Ready — the gauntlet itself)
    |  gates on: nothing structural; throughput gated by researcher time
    |  and by how many genuinely new, well-motivated hypotheses exist
    v
Validated Alpha Library  ***CURRENT BLOCKING STAGE — 0 entries***
    |  gates on: at least ONE hypothesis reaching `confirmed`.
    |  9 tested, 9 rejected. This is not a broken stage — it is a stage
    |  doing its job (see Lessons Learned: 2 near-misses, both diagnosed
    |  precisely, both with a credible fix identified). But it IS, right
    |  now, the single hard gate blocking every stage below it.
    v
Company Intelligence  ***BLOCKED*** by: zero validated factors (nothing
    |  to compute an exposure FROM). No code exists. Unblocks the instant
    |  factor #1 validates — schema/refresh-cadence design can start
    |  the moment that happens, not before (a profile built on zero
    |  factors is either empty or fabricated).
    v
Ranking Engine  ***BLOCKED*** by: Company Intelligence (above) AND by
    |  needing an expected-alpha INTERVAL from walk-forward evidence
    |  (ranking on an unvalidated score is indistinguishable from ranking
    |  on noise — this is not a process formality, it's the difference
    |  between the platform's stated purpose and its opposite).
    v
Portfolio Construction  ***BLOCKED*** by: charter milestone — needs >=2
    |  validated, INDEPENDENT factors (independence is what the Expected
    |  Interaction prereg section exists to establish in advance). At 0
    |  validated factors, this is two milestones away, not one.
    v
Risk Engine (portfolio-level)  ***BLOCKED*** by: Portfolio Construction
    |  (nothing to measure risk ON). Per-experiment risk metrics already
    |  exist and are NOT blocked — this is specifically the cross-factor,
    |  cross-position aggregation layer.
    v
Performance Attribution  ***BLOCKED*** by: Portfolio Construction (same
    |  as Risk Engine — decomposes a live portfolio's realized return,
    |  which does not exist).
    v
Institutional Reports  ***PARTIALLY BLOCKED***. IC memos (research-grade
       reports) are Production Ready today. INVESTMENT reports (grade,
       thesis, portfolio fit, expected alpha per the user's Output
       Philosophy) are blocked transitively by every stage above.
```

**The single highest-leverage unblock in the entire dependency chain is
the Validated Alpha Library reaching its first entry.** Everything below
it is either zero-code-deferred or partially built and waiting. This is
not a call to lower the bar to get there faster — the Lessons Learned
retrospective is explicit that false positives are more costly than
continued honest rejection.

---

## Phase 3 — Platform Maturity Assessment

Scored 1 (absent/poor) – 5 (excellent) on four dimensions per module.

| module | completeness | evidence quality | engineering quality | production readiness |
|---|---|---|---|---|
| PIT database (`db.py`) | 5 | 5 | 5 | 5 |
| Registry / Ledger / Governance | 5 | 5 | 5 | 5 |
| Coverage Gate | 5 | 5 | 5 | 5 |
| Validation gauntlet (`phase4.py`, `stats.py`, `failure_conditions.py`) | 5 | 5 | 4 | 5 |
| Cross-sectional engine (`backtest_xs.py`) | 4 | 4 | 4 | 4 |
| Sector engine (`backtest_lite`/`engine_full`) | 5 | 4 | 4 | 3 *(family closed)* |
| Parsers (pricelist/DOL/LIST2/gainers) | 5 | 5 | 4 | 5 |
| Corp-actions structured extraction | 2 | 1 | 3 | 1 |
| EPS/dividend parser | 2 | 1 | 3 | 1 *(known dead end)* |
| Validated Factor Library (content) | 0 | n/a | n/a | 0 |
| `alpha_engine.py` (shell) | 5 | 5 | 5 | 5 *(for what it currently does)* |
| Company Intelligence Engine | 0 | 0 | 0 | 0 |
| Ranking Engine | 0 | 0 | 0 | 0 |
| Portfolio Construction | 0 | 0 | 0 | 0 |
| Risk Engine — per-experiment | 4 | 4 | 4 | 4 |
| Risk Engine — portfolio-level | 0 | 0 | 0 | 0 |
| Performance Attribution | 0 | 0 | 0 | 0 |
| IC memo / reporting generator | 5 | 5 | 4 *(one bug found+fixed)* | 5 |

### Highest-value bottlenecks

1. **The Validated Alpha Library has zero entries.** This is a research
   outcome, not an engineering defect (see Phase 2) — but it is
   nonetheless the fact with the single largest downstream effect on
   platform maturity. Two near-misses (H-004 p=0.079, H-009 p=0.069) are
   the strongest available signal that this gate is close to opening, not
   structurally stuck.
2. **Corp-actions structured extraction and the EPS/dividend parser are
   the two lowest-scoring PIECES OF CODE in the platform** (evidence
   quality 1/5 each) — both represent real engineering effort that has
   not yet produced usable data. Neither blocks the current highest
   priority (closing the alpha gap), but both block entire future
   families (Value, Dividend Yield, Corporate-Action events) and are
   worth a dedicated, scoped effort rather than incidental attempts.
3. **No infrastructure exists yet for MULTI-hypothesis or MULTI-cohort
   research designs** (pooled momentum, regime-conditioning) — every
   piece of the gauntlet was built and proven for SINGLE, independent
   hypotheses. If Wave 3 pursues C1 or C2 (the two highest-scored
   candidates), this is new engineering, not a reuse of existing capacity.

---

## Phase 4 — Three-Year Alpha Roadmap

Sequenced by what CAPABILITY each year should add to the platform, not by
a hypothesis list. Each year's entry point is gated on the previous
year's exit condition — this roadmap can run faster or slower than
calendar time; the gates are what matter.

### Year 1 — Close the alpha gap; stand up Company Intelligence v0

- Pursue the two highest-scored Wave 3 candidates (C1 Pooled Momentum, C4
  Size) as the next pre-registered wave, per `WAVE_3_RESEARCH_DIRECTIONS.md`.
- Build the regime-classification methodology (C2) as INFRASTRUCTURE in
  parallel — its own dedicated validation (does the regime definition
  itself leak information?) before it is used to gate any factor.
- Exit condition: **≥1 validated, independent factor.**
- On exit: Company Intelligence Engine v0 begins — schema design for a
  per-company profile keyed on whatever factor(s) validated, refreshed on
  the same cadence as the data layer. `alpha_engine.py` gets its first
  wired `ModelAdapter`.

### Year 2 — Reach factor independence; begin Portfolio Construction

- With ≥1 factor validated, pursue factor families explicitly chosen for
  LOW expected correlation to what already validated (the Expected
  Interaction prereg discipline, now with a real factor to compare
  against instead of only priors) — Value/Dividend and Corporate-Action
  families become viable once (a) the EPS/dividend parser gets a proper
  scoped retry with per-era calibration, or (b) the corp-actions
  classification pipeline is validated to evidence grade.
- Total-return infrastructure matures (dividend amounts, not just
  closure dates) — unlocks a total-return retest across the ENTIRE
  per-stock hypothesis family, not just new ones (H-002's original
  question, finally answerable).
- Exit condition: **≥2 validated, independent factors** (charter
  milestone).
- On exit: Portfolio Construction Engine begins (equal-weight, then
  risk-based constructions per the user's stated support list);
  portfolio-level Risk Engine begins in parallel (it needs a portfolio to
  measure).

### Year 3 — Ranking, Attribution, and institutional reporting

- Ranking Engine: expected-alpha intervals from walk-forward evidence,
  explainability report per company (factor contribution breakdown).
- Performance Attribution: factor return / sector allocation / selection
  / timing / cost decomposition on the constructed portfolio(s).
- Institutional Report Generator: the user's stated output philosophy
  (Grade, Confidence, Thesis, Factor Breakdown, Risk Summary, Portfolio
  Fit, Expected Alpha, Implementation Notes, Evidence, Validation
  History) becomes producible because every input it needs now exists
  and is evidence-backed.
- Continuous Learning goes operational: per-factor decay monitoring
  (rolling IC vs validation-era IC) activates for every library entry,
  generating research PROPOSALS on drift — never auto-adjusting weights,
  per standing instruction.
- Exit condition for calling the platform "institutional-grade" in
  practice (not just in architecture): a live multi-factor portfolio with
  full attribution and monitoring, reproducible end to end from the PIT
  database through to a generated report.

**What this roadmap deliberately does NOT contain**: a promise that Year
1 succeeds. Nine rejections is the base rate this program has actually
observed; the roadmap's gates are conditional, not scheduled. If Year 1
closes with 0 validated factors again, the correct response is another
retrospective of the same rigor as this one — not an acceleration of
Year 2 work against an empty Factor Library.

---

## Phase 5 — Research Prioritization (platform-impact framing)

Extending `WAVE_3_RESEARCH_DIRECTIONS.md`'s Phase 5 table with the
dimensions this document's brief specifically requests. Scored 1–5.

| candidate | platform impact | engineering effort (5=low) | research value | implementation difficulty (5=low) | new-dataset dependence (5=none needed) | time to completion (5=fast) |
|---|---|---|---|---|---|---|
| C1 Pooled Momentum | 3 | 4 | 5 | 3 | 5 | 4 |
| C2 Regime-Conditional Gate | 5 | 3 | 4 | 2 | 4 | 2 |
| C3 Corp-Action Drift | 3 | 2 | 3 | 2 | 3 | 2 |
| C4 Size | 4 | 5 | 3 | 5 | 5 | 5 |
| C5 Dividend Payer | 2 | 5 | 2 | 5 | 5 | 5 |

**Platform impact** is the new lens this phase adds versus the prior
document's "long-term platform contribution" column: C2 scores highest
here specifically because a validated regime-classification methodology
is REUSABLE across every future hypothesis (Company Intelligence's
eventual macro-sensitivity field depends on exactly this), independent
of whether any single factor gated by it validates. C1 scores lower on
platform impact than research value — it is likely to produce the
program's next verdict fastest, but as infrastructure it is a narrower,
single-purpose extension (multi-cohort blending) rather than a reusable
platform capability. C4 (Size) is the best-balanced candidate: high
impact (feeds a future Risk Engine regardless of alpha verdict), lowest
effort, fastest completion, zero new datasets needed.

This table does not override Wave 3's recommendation (C1 + C4 first,
C2 as its own dedicated future wave) — it explains, in the platform-value
terms this document was asked to use, WHY that sequencing (fast,
evidence-strong wins first; the higher-ceiling, higher-effort
methodology bet held for a dedicated wave) is the right one rather than
running C2 immediately.

---

## Phase 6 — Investment Firm Readiness

*Assessment only, per instruction — nothing below is built by this
document.*

### Already meets institutional standards

- **Pre-registration discipline**: criteria fixed before any run, no
  discretionary post-hoc changes — matches or exceeds standard practice
  at systematic funds; this is the platform's strongest existing control.
- **Immutable audit trail for research**: every experiment's config, code
  fingerprint, seed, and metrics are permanently recorded
  (`data/registry.sqlite`, SQL-trigger-enforced against UPDATE/DELETE).
  This is a genuine audit trail for the RESEARCH process specifically.
- **Point-in-time data discipline**: bitemporal reads with vintage
  pinning is a real institutional-grade control against look-ahead bias.
- **Multiple-testing correction and placebo testing as HARD gates**,
  not advisory — matches best practice, exceeded it in practice this
  session (the H-006 ranking-specific placebo catching a flaw that raw
  significance alone would have missed).
- **Reproducibility**: bit-identical reruns verified via seed registry.

### Does not yet meet institutional standards

- **Version control.** This repository is NOT a git repository. For a
  research process this rigorous about data provenance, the absence of
  code version history is a genuine, currently-live gap — not a future
  one. (Distinct from the DATA layer's own bitemporal versioning, which
  is excellent; this is about the CODE that produces results.)
- **Formal model governance beyond the ledger.** The ledger tracks
  hypothesis status and freezes rejected ones — strong for a
  single-researcher process. It does not yet have a periodic
  REVALIDATION cadence for anything CONFIRMED (moot today at 0
  validated factors, but will matter the day factor #1 validates: does
  it get re-checked against fresh data on a schedule, and by whom?).
- **Independent research approval.** Currently "show the owner before
  running" — appropriate and sufficient at current scale (one
  researcher, one reviewer). A firm with multiple researchers or
  external capital would need a documented approval workflow, not a
  single approve/reject exchange.
- **Compliance function.** Does not exist and is not yet needed — there
  is no live capital, no client money, no regulatory filing obligation
  triggered by research alone.
- **Live monitoring / alerting.** Nothing is live, so nothing is
  monitored; not a gap yet, becomes one at first deployment.
- **Explainability beyond IC memos.** IC memos are strong qualitative
  explainability for a SINGLE hypothesis's verdict. A systematic,
  per-company, per-factor explainability engine (the Ranking Engine's
  eventual output) does not exist because Ranking itself doesn't exist.
- **Portfolio-level risk controls** (position limits, pre-trade checks).
  Not needed without a live portfolio; will be needed the moment
  Portfolio Construction produces one.

### When each becomes necessary (not before)

| control | trigger |
|---|---|
| Version control (git) | Now — this is a present-tense gap, not a future one; recommend addressing independent of the alpha roadmap. |
| Revalidation cadence for confirmed factors | The day factor #1 reaches `confirmed` status. |
| Formal multi-person research approval | The day a second researcher (human or otherwise) joins the process, or external capital is involved. |
| Portfolio-level risk controls | The day Portfolio Construction produces its first live-eligible portfolio (Year 2 roadmap gate). |
| Live monitoring/alerting | The day any output leaves the research environment for live or paper trading. |
| Compliance function | The day the platform manages, advises on, or reports to external capital. |
| Systematic explainability engine | Coincides with the Ranking Engine build (Year 3 roadmap gate). |

---

*Cross-references: `docs/PLATFORM_ARCHITECTURE.md` (module layer map,
now superseded in detail by this document — kept as the short-form
summary), `docs/FACTOR_REGISTRY.md` (permanent per-hypothesis evidence),
`docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`,
`docs/WAVE_3_RESEARCH_DIRECTIONS.md`. No H-010 or any new hypothesis ID
was created by this document.*
