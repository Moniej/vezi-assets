# Institutional Research Committee Audit — 2026-08-02

*Requested as an adversarial, non-flattering audit. Every factual claim
below was checked against `data/registry.sqlite`, `src/ngxrot/*.py`, and
`docs/*` on 2026-08-02, not restated from the request. Where the request's
own figures were wrong, they are corrected, not silently repeated — an
institutional research committee that let a founder's mis-stated headline
number pass unchallenged would itself have failed its job.*

## Correction to the brief before anything else

The brief states "8 hypotheses tested, 1 confirmed, 7 rejected." The real
ledger (`data/registry.sqlite.hypotheses`, queried directly):

| status | count | IDs |
|---|---|---|
| confirmed | 1 | H-011 (Size) |
| rejected | 10 | H-001, H-003, H-004, H-005, H-006, H-007, H-008, H-009, H-010, H-012 |
| untested | 1 | H-002 (blocked on data, never run) |
| **total registered** | **12** | |

11 hypotheses have actually been *run and resolved*; 1 remains registered
but never executed. This is a **37% undercount** of rejected hypotheses in
the brief. Flagging this first is itself Section-3 material: **a research
program's own headline summary drifting from its ledger is exactly the kind
of small, compounding inaccuracy that turns into a bigger credibility
problem later** — the fix is to generate the summary number
programmatically from the ledger every time it's quoted, never type it by
hand. The rest of this audit uses the verified 12/1/10/1 figures throughout.

The other headline figures in the brief (116 commits — brief said "over
112," both true but 116 is current; 41 tags; 38 regression test files;
511+ assertions; 11,533 documents; 143 corporate-action facts; 137
hand-verified financial-statement facts; 267 mechanically-derived
reasoning conclusions; 10 NGX companies with statement coverage) were
independently re-verified and are accurate.

---

## SECTION 1 — Methodology comparison

**AQR / Cliff Asness's research team.** Real alignment: hypothesis-driven,
economically-motivated factor testing rather than pure data-mining; explicit
placebo/permutation testing before accepting a result (AQR's public
research, e.g. Asness, Frazzini, Israel & Moskowitz's replication-focused
papers, consistently stress-test signals against simple nulls before
publishing). Real gap: AQR's published methodology routinely reports
**Newey-West or Fama-MacBeth standard errors** to handle serial correlation
in overlapping-window returns. This platform's `stats.py::excess_ttest`
computes a **plain i.i.d. t-test on daily net excess returns** with no
HAC/autocorrelation adjustment — its own docstring admits this ("understates
fat-tail risk — treat as the OPTIMISTIC bound") and correctly demotes it to
a secondary check behind the placebo test. That is honest design, but it is
not AQR-grade statistical inference; it is a known-weak test kept around
because a better one (placebo) exists alongside it.

**Fama-French / Carhart.** Real alignment: portfolio-sort methodology
(rank on a characteristic, form top/bottom baskets, measure spread) is
structurally identical to the Fama-French sorting tradition, and the
platform's per-hypothesis stability grid (varying lookback/top_n) mirrors
the standard robustness-to-specification check every asset-pricing paper
since Fama-French (1992) runs. Real gap: F-F sorts on CRSP's full universe
(thousands of names) with NYSE breakpoints to avoid microcap contamination;
this platform's largest universe is **100 names** (IRU v2). This is not a
methodology gap, it's a **breadth gap** — see Grinold's Fundamental Law
below, Section 3.

**BlackRock Systematic / MSCI.** No public evidence of BlackRock Systematic's
internal implementation exists; this audit will not speculate about it. MSCI
does publish factor-index methodology (MSCI Barra risk models, e.g. Barra
USE4). Real gap, stated plainly: **there is no risk model** in this
platform — no factor covariance matrix, no idiosyncratic-risk decomposition,
no ex-ante tracking-error estimate. Every result reported here is realized
(ex-post) return and volatility from a single backtest path, not a
Barra-style risk forecast. This is a structural absence, not a quality
issue with what exists.

**Research Affiliates / Dimensional.** Real alignment: both are academically
literal in construction (Research Affiliates' "fundamental indexation," and
Dimensional's founding premise of implementing peer-reviewed factor research
directly, e.g. Fama & French's own involvement with DFA) — this platform's
pre-registration-before-running discipline is closer in spirit to
Dimensional's academically-grounded process than to a discretionary shop.
Real gap: both DFA and RA operate at global multi-thousand-security breadth
with decades of data; this platform has ~10 years of NGX data and a 100-name
ceiling, so the *process* rhymes but the *statistical power* it can achieve
does not.

**Two Sigma / Renaissance Technologies.** No public methodology exists for
either firm beyond generic statements about statistical/ML-driven trading
at scale; this audit will not fabricate a comparison. What can be said with
confidence: this platform is **not** attempting anything resembling
high-frequency statistical arbitrage, ML-driven signal discovery at scale,
or alternative-data ingestion — it is a low-frequency, monthly/quarterly
fundamental-and-price factor research program. Any claim of methodological
similarity to Renaissance specifically would be unfounded.

**Robeco.** Robeco publishes extensively on factor investing (e.g. multi-factor
combination research, factor timing skepticism). Real alignment: Robeco's
public research is skeptical of factor timing and regime-switching without
strong evidence — this platform's own H-012 result (regime-gating did not
rescue H-008, and if anything made the negative excess worse) is directly
consistent with that skepticism, and the platform correctly reported the
negative result rather than reframing it. That consistency is a genuine
point in this platform's favor, not a coincidence to be waved away — it
means the platform's null results are not obviously spurious; they land
where the broader factor-investing literature would predict.

**Andrew Ang (factor investing / factor risk premia).** Ang's framework
treats factors as risk exposures requiring an economic risk-based story, not
just a statistical pattern. This platform's guardrail against activating any
factor without "economic rationale" and "why hasn't arbitrage removed it"
(per the Wave 2 directive's own Institutional Validation section) mirrors
Ang's insistence on economic justification. Real gap: Ang's work also
emphasizes factor-timing and multi-factor portfolio construction once
several factors are validated — this platform has exactly one validated
factor (H-011, capacity-constrained), so it is not yet at the stage Ang's
later-chapter material addresses.

**Marcos López de Prado (AFML / financial ML methodology).** This is the
sharpest, most concrete gap. López de Prado's specific, checkable
methodological contributions and their status here:

| López de Prado technique | Present? | Evidence |
|---|---|---|
| Purged / embargoed cross-validation | **No** | Walk-forward uses three fixed, named calendar regimes (`pre_float`/`float_shock`/`oos_2025_26`), not k-fold CV with purging |
| Combinatorial Purged CV (CPCV) | **No** | Not implemented anywhere in `backtest_xs.py`/`phase4.py` |
| Deflated Sharpe Ratio (accounts for total number of trials/hypotheses) | **No** | `stats.py` has no DSR function; the placebo test controls for *within-hypothesis* multiplicity (parameter grid) but not *across-hypothesis* multiplicity (12 ideas tested against the same NGX return history) |
| Probability of Backtest Overfitting (PBO) | **No** | Not computed |
| Triple-barrier labeling / meta-labeling | **Not applicable** | This is a cross-sectional factor-sort framework, not an ML classification pipeline — not testing this against AFML is fair, since the platform never claimed to do ML |
| Fractional differentiation for stationarity | **No** | Not used; not obviously needed at monthly/quarterly rebalance frequency |

This is a real, actionable gap, not a nitpick: with 12 hypotheses tested
against one ~10-year NGX history, **Harvey, Liu & Zhu (2016, "…and the
Cross-Section of Expected Returns," Review of Financial Studies)** argue the
appropriate significance bar rises substantially (they suggest t > 3.0)
precisely because of the "factor zoo" multiple-testing problem — testing
many ideas against the same data inflates the chance any one clears a
naive p<0.05 bar by chance. This platform's placebo test and per-hypothesis
Holm/BH correction are good practice, but neither corrects for the fact
that **this is roughly the 12th independent test run against the same
underlying return series.** A Deflated Sharpe Ratio computed against the
running trial count (as López de Prado & Bailey 2014 specify) would be the
correct fix and does not yet exist here.

**Institutional buy-side research generally.** The strongest alignment: the
platform's insistence that a rejected hypothesis is a permanent, frozen,
disclosed research output (never deleted, never silently rerun) is a real
institutional practice — serious buy-side research desks maintain exactly
this kind of "graveyard" to prevent re-testing the same dead idea after
memory fades. The weakest alignment: institutional desks typically have a
**risk committee sign-off tied to capital allocation**, not just a
statistical confirmation bar. This platform has no portfolio-construction
or risk-budgeting step downstream of "confirmed" — H-011 has been confirmed
since 2026-07-22 with zero capital-allocation follow-through, which is
correct under the current guardrails (no valuation/recommendation outputs
authorized) but means the research pipeline currently terminates in a
document, not a decision.

---

## SECTION 2 — Frontier vs. Emerging vs. Developed technique classification

**Verdict: hybrid, and the hybrid is uneven — frontier-market adaptations in
the DATA layer, developed-market-academic technique in the STATISTICAL
layer, with no emerging/frontier-specific statistical adjustments at all.**

**Frontier-specific parts:**
- The entire cost model (`costs.py`) is NGX-specific: brokerage, CSCS fee,
  stamp duty, SEC/NGX statutory fees, VAT-on-subset-of-fees — this is a
  frontier-market necessity (developed-market US equity research rarely
  models stamp duty; UK research does, for a different reason). Correctly
  built as frontier-specific.
- The regime-classification variable in H-012 (macro/banking/commodity
  shock proximity, MPC monetary events) is calibrated to NGX's actual
  historical shock catalogue (2016 FX crisis, 2020 COVID, 2023 float) —
  genuinely NGX-specific, not a generic volatility-regime filter borrowed
  from developed-market research.
- The Investable Research Universe (IRU) construction is explicitly
  NGX-listing-rule-aware (per `configs/iru.toml`) rather than a generic
  liquidity screen — appropriate for a market this thin.
- The capacity/AUM ceiling reporting (H-011's ₦694k median leg capacity) is
  a frontier-market-necessary disclosure; developed-market research rarely
  needs to report capacity in absolute local-currency terms this explicitly
  because liquidity is rarely the binding constraint.

**Generic (i.e., borrowed wholesale from developed-market academic
practice, not adapted):**
- The statistical test battery (t-test, Holm, Benjamini-Hochberg, placebo
  permutation) is standard cross-market academic methodology with **zero
  frontier-specific adjustment**. This matters because frontier markets have
  known statistical peculiarities — e.g. thin trading creates
  non-synchronous-trading-induced autocorrelation (the classic
  Scholes-Williams / Dimson beta-adjustment problem), and NGX's own
  documented characteristics (many stocks with sparse trading days) would be
  expected to produce exactly this artifact. There is no evidence in
  `stats.py` or `backtest_xs.py` of any non-synchronous-trading correction.
- The factor-sort construction (quintile/decile-style top-N baskets) is the
  generic Fama-French recipe, unmodified for NGX's extreme breadth
  constraint (100 names, sometimes fewer per era) beyond simply using
  smaller N.
- The regime-classification's underlying *statistical machinery* (a boolean
  gate) is generic; only the *calibration* (which categories/severities
  trigger it) is NGX-specific.

**What should change if the platform expands beyond NGX:**
1. **Statistical layer must gain HAC/Newey-West standard errors and a
   cross-hypothesis Deflated Sharpe Ratio before adding more markets** —
   right now the "generic" layer is the weakest link, and expansion would
   only multiply the number of untreated multiple-testing/autocorrelation
   problems, not fix them.
2. **A market-specific cost model per new market is mandatory, not
   optional** — the NGX cost model's specificity (stamp duty, CSCS, VAT
   treatment) cannot be reused verbatim for e.g. a Kenyan or Ghanaian
   exchange; this is real, non-generic engineering work each time.
3. **The regime-classification calibration (event catalogue, severity
   thresholds) is NGX-specific and must be re-derived per market**, not
   copy-pasted — the mechanism (a look-ahead-safe boolean gate keyed to
   `announced_date`) is reusable; the *calibration* is not.
4. **The IRU construction logic is closest to being portable** — a
   rule-based, listing-rule-aware universe filter is a sound pattern for
   any frontier/emerging market, provided the underlying listing-rule
   config is redone per market.
5. A genuinely important frontier-market question this platform has not
   yet asked: **cross-market pooling.** If the platform expands to
   multiple African frontier markets, the single biggest research-value
   question becomes whether a factor confirmed in one market (e.g. NGX
   Size) replicates in others — this is a materially different research
   design (panel data across markets, not just more NGX history) and
   nothing in the current architecture anticipates it.

---

## SECTION 3 — Research-decision review

**Good decisions:**
- Freezing rejected hypotheses permanently and disallowing silent reruns
  (enforced by SQL triggers and the `frozen` flag in `ledger.py`/`registry.sql`,
  not just a convention) — this is a real, mechanically-enforced guardrail
  against exactly the kind of file-drawer problem (Rosenthal 1979) that
  invalidates most published factor research nobody can audit.
- Making the placebo test (nonparametric, persistence-preserving
  ticker-relabeling) the *primary* criterion and demoting the parametric
  t-test to a documented "optimistic bound" — a mature, self-aware design
  choice given the daily-return autocorrelation problem described above.
- The look-ahead audit for H-012 being run as an **independent, separate
  re-derivation** (not just re-reading the same code path) — this is a real
  adversarial-verification step, not a rubber stamp.
- Categorizing failures by mechanism (universal/structural,
  regime-dependent, improperly-conditioned) in the Phase 28 audit — this
  turns a pile of "rejected" results into an actual research finding about
  *why* NGX factor premia are hard to harvest (breadth and cost ceilings
  dominate), which is itself a publishable-shape observation.

**Weak decisions:**
- No cross-hypothesis multiple-testing correction (Section 1). Twelve tests
  against one history, each cleared on its own terms, is not the same
  statistical claim as "the program-wide false-discovery rate is
  controlled." H-011's own p=0.0099 should be read as "0.0099 conditional on
  ignoring the other 11 tests run against the same data" — still a real
  signal, but the headline number overstates confidence measured against
  the whole program.
- The parametric t-test's use of **daily** returns for a
  monthly/quarterly-rebalanced strategy inflates `n_obs` into the thousands
  while the actual number of independent rebalance decisions is a few dozen
  at most (H-009's own memo explicitly notes "~9 independent decisions in 9
  years" — the platform already knows this distinction matters for *power*,
  but the t-test implementation does not reflect it for *inference*).
- No explicit non-synchronous-trading (thin-trading) correction, which
  frontier-market microstructure research (e.g. Bekaert, Harvey & Lundblad
  on emerging-market liquidity, and the broader Scholes-Williams tradition)
  would flag as necessary given NGX's known thin-trading names.

**Missing decisions:**
- No documented, pre-committed **program-level stopping rule for the
  overall factor hunt** beyond "stop when no data-supported hypothesis
  remains" — there is no pre-registered cap on *total number of hypotheses
  the program will test* before the multiple-testing problem is treated as
  requiring a structural fix (e.g., "after N hypotheses, switch to a
  Deflated Sharpe framework"). Right now that threshold is implicit and has
  already been crossed (12 tests run).
- No documented survivorship-bias check on the IRU construction. This audit
  did not find evidence either way (this is a gap in *this audit*, not a
  claim the bias exists) — whether IRU membership as of a historical date
  includes since-delisted/suspended NGX names, or only names currently
  listed, was not verified in this pass and should be explicitly confirmed
  and documented, since survivorship bias is one of the most common
  silent killers of backtested "premia" in exactly this kind of thin market.

**Incorrect assumptions caught and corrected (within this session's own
audit trail, a good sign about the platform's self-correction ability, but
worth restating plainly as assumptions that WERE wrong until checked):**
- The Wave 2 directive itself assumed Financial Strength was "buildable
  using existing FSI" — false; same 10-ticker ceiling as everything else.
- An earlier working assumption that Share Issuance data was broadly usable
  because the raw filing archive spans 260 symbols — false; the `doc_class`
  field is not real event-type classification.

**Research blind spots:**
- No point-in-time universe reconstruction audit has been produced as a
  standalone deliverable (only referenced implicitly through IRU version
  history). An institutional committee would want a dedicated PIT-universe
  reconciliation report, not just trust in the rule engine.
- No sensitivity analysis of results to the *cost-schedule assumption
  itself* — `costs.py`'s own docstring flags "VAT base assumption (marked
  'assumed')... confirm against a contract note" as an open item; every
  hypothesis's net-of-cost verdict inherits this unresolved assumption
  silently.

**Survivorship bias**: not verified either way in this audit (see above) —
flagged as an open item requiring direct confirmation before the platform's
next expansion phase, not asserted as present or absent.

**Selection bias**: real risk, partially mitigated. The Wave-3 research
document's own pre-scoring of candidates (C1-C5) before running them is
good practice (reduces post-hoc cherry-picking of which ideas to test), but
the fact that H-012 was chosen specifically *because* H-004 and H-008 showed
regime-sensitivity is itself a form of *conditional* hypothesis selection —
defensible (it is economically motivated, not p-hacked), but it does mean
H-012's prior probability of success was elevated by construction, which
its own placebo p=0.97 shows was not enough to rescue it anyway. Worth
noting for intellectual honesty, not as a flaw in H-012's conduct.

**Look-ahead risk**: the strongest area of the platform. H-012's independent
audit (0/36 mismatches) and the broader `announced_date`-only discipline is
real, checked evidence, not a claim taken on faith.

**Publication bias**: actively and structurally guarded against (permanent
rejection registry) — this is the platform's standout strength relative to
almost any comparison in Section 1.

**Overfitting / data-mining risk**: the single largest open risk in the
entire program, understated by the current tooling (no DSR, no PBO, no
cross-hypothesis correction) despite good hygiene at the single-hypothesis
level (placebo, stability grid, OOS window).

**Structural risk**: the 100-name IRU ceiling is a hard structural bound on
statistical power per Grinold's Fundamental Law of Active Management,
IR ≈ IC × √(breadth) — with breadth this low, even a genuinely real IC
requires either an implausibly large IC or many independent rebalance
periods to produce a detectable IR, which is precisely why five of ten
rejected hypotheses were categorized "universal/structural" in the
platform's own Phase 28 audit. This is correctly diagnosed already; it is
restated here because it is the single most important structural fact about
this entire research program and should govern expectations for every
future hypothesis, not just be a line in one document.

**Operational risk**: `data/registry.sqlite` is explicitly not
git-tracked — the *evidence* (JSON exports under `experiments/`) is
preserved in git, but the live, queryable ledger is a single local SQLite
file with no evidence of off-machine backup or replication in this audit
pass. A disk failure would not lose the historical experiment record (it's
in git) but would lose the operational ledger's convenient queryability and
require rebuilding it from the JSON exports — worth a documented recovery
procedure, which does not appear to exist yet.

---

## SECTION 4 — Factor research program evaluation

Given: 1 confirmed (capacity-constrained), 10 rejected, Interaction Factors
next, Liquidity and Dividend available, Value/Quality/etc. blocked —

**Would an institutional quant shop continue exactly like this? No — not
because the process is wrong, but because the marginal value of another
single-factor test on this same 100-name universe is now low relative to
three other moves:**

1. **Fix the measurement layer before testing more factors.** Running
   Interaction Factors next (as this platform's own audit recommended) with
   the *same* i.i.d. daily t-test and no cross-hypothesis DSR simply adds a
   13th test to an already-uncorrected multiple-testing problem. An
   institutional shop would insert a Deflated-Sharpe/PBO step **before**
   H-013, not after several more hypotheses accumulate.
2. **Interaction Factors is the right next single-factor test, but for a
   more specific reason than "it's available."** Testing Size×Volatility
   and Size×Momentum is valuable specifically *because* it can explain
   *why* H-011 works and H-007/H-008 don't — i.e., it's confirmatory
   forensics on the one real result, not merely "another available
   candidate." An institutional shop would frame it exactly this way
   (a diagnostic extension of H-011), not as a peer of H-001-H-012.
3. **An institutional shop would treat the FSI 10-ticker ceiling as the
   single highest-value non-research investment right now** — not a
   "future phase," but the actual bottleneck standing between this program
   and eleven of sixteen requested factor families. Continuing to run
   available-but-marginal factors (Liquidity, Dividend payer-status) while
   the real prize (Value, Quality, Profitability) sits behind a
   labor-bounded extraction problem is a reasonable use of time but should
   not be mistaken for the program's main constraint being solved.

**Direction change recommended**: yes, in priority ordering, not in method.
Sequence: (a) implement Deflated Sharpe Ratio / cross-program multiple
testing correction as new, additive statistical infrastructure (this
directly "blocks research" per the Wave 2 directive's own infrastructure
exception — a correct interpretation, not scope creep); (b) run Interaction
Factors framed as H-011 forensics; (c) run Liquidity and Dividend
payer-status as genuinely new, independent factor tests; (d) treat FSI
breadth expansion as a standing, tracked owner-decision item, not something
to revisit only "when a new phase is proposed."

---

## SECTION 5 — Hypothesis methodology evaluation

**Keep, unconditionally**: pre-registration before viewing performance data;
placebo/permutation testing as the primary criterion; permanent rejection
registry with no silent reruns; out-of-sample window that is genuinely
untouched until final evaluation; the per-hypothesis stability grid.

None of these should change — each is doing real work and each is standard
or better-than-standard institutional practice per Section 1.

**Should change**:
1. **Multiple-testing correction must move from per-hypothesis to
   program-level.** Concretely: track a running trial count in the ledger
   (already has the data — 12 rows) and report a Deflated Sharpe Ratio
   alongside every future confirmation, computed against that count
   (Bailey & López de Prado 2014). This is an *addition*, not a removal —
   consistent with "additive-only" extension convention already used for
   every prior `backtest_xs.py` change.
2. **The parametric t-test should be computed on non-overlapping
   rebalance-period returns, or HAC-adjusted, not on raw daily returns.**
   Currently it silently overstates `n_obs` and understates the true
   standard error for anything but the placebo test. Given the docstring
   already flags this as an "optimistic bound," this is a low-risk,
   well-scoped fix: add a second, corrected inference path rather than
   remove the existing one.
3. **A pre-committed total-hypothesis-count checkpoint** (e.g., "after
   every 5 hypotheses, produce a program-level overfitting review before
   continuing") would formalize what should have already triggered around
   hypothesis #10.

**Should NOT change**: stability grids, negative-result publication,
permanent registry — these are working exactly as intended and are the
platform's strongest asset. Do not weaken them to "move faster."

---

## SECTION 6 — Architecture critique

**Quant Engine** (`backtest_xs.py`, `phase4.py`, `runner.py`): well-factored
additive-extension discipline (H-010's pooled-cohort machinery and H-012's
regime-gate machinery both added as new functions, zero modification of
existing ones) is genuinely good engineering hygiene — it makes historical
experiment reproducibility structurally hard to break by accident. Weakness:
`stats.py` is only 67 lines and carries the entire statistical-inference
burden for every hypothesis; it is under-built relative to the
sophistication of the experiment orchestration around it (Section 1/5).

**AI Intelligence Layer / 14-step reasoning pipeline**: not directly
re-inspected in this audit pass (out of scope for the factor-research
questions this session has focused on); no comment offered beyond noting
this is a real gap in *this specific audit's* coverage, not a claim the
layer is fine or flawed.

**Financial Reasoning Engine / Knowledge Graph / Research CLI / Portfolio
Research / Research Dossiers**: not directly re-inspected in this audit
pass either. Flagging this explicitly rather than commenting without
having checked: an aggressive audit that speculates about subsystems it
did not open is exactly the kind of unearned confidence this report is
supposed to avoid.

**Validation harness / regression methodology**: 38 dedicated regression
files, 511+ assertions, with a documented instance of the harness itself
catching a real historical defect (`docs/PROJECT_MILESTONES.md` line 213
area) — this is genuine, demonstrated value, not a claimed capability.
The 12-check rehearsal suite (R1-R12) being re-run before every new
`backtest_xs.py` addition is a real regression-safety practice matching
production-engineering norms, applied to a research codebase where many
academic-adjacent projects skip it entirely.

**Versioning / git discipline**: 116 commits, 41 tags, an annotated `v1.0`
tag correctly dereferenced to the commit (the nested-tag mistake earlier in
this project's history was caught and fixed, not left in place) — solid.
One real gap: tag *density* relative to commit count (41 tags / 116
commits ≈ one tag per 2.8 commits) suggests tagging is happening at nearly
every milestone, which is good for auditability but should be checked
against whether tag *messages* consistently distinguish "safe to roll back
to" checkpoints from "just a milestone marker" — not verified in this pass.

**Documentation quality**: strong in a specific way — every research
artifact (prereg, IC memo, implementation log, final report) exists as a
separate, addressable file, which is closer to institutional research-note
discipline than most software projects achieve. Real gap: no single
**index/table of contents** tying prereg → implementation log → IC memo →
registry entry together per hypothesis was found in this audit; a reader
has to know the naming convention to assemble a hypothesis's full paper
trail. A per-hypothesis manifest (even a generated one) would meaningfully
improve auditability at near-zero cost.

**What institutional engineering teams would improve first**: the
statistical-inference layer (Section 1/5), a program-level trial-count
tracker, and a per-hypothesis document index. Notably, none of these
require new data or owner decisions — they are pure engineering additions
that directly serve the Wave 2 directive's own "infrastructure only if it
directly blocks research" exception, since uncorrected multiple-testing
genuinely does block trustworthy research from this point forward.

---

## SECTION 7 — Missing research directions (institutional-grade, data-available, guardrail-respecting only)

Ranked by expected research value:

1. **Interaction Factors as H-011 forensics (Size×Volatility,
   Size×Momentum, Size×Liquidity).** Highest value: uses zero new data,
   directly interrogates the platform's only confirmed result, and could
   either strengthen H-011's economic story (if the size premium
   concentrates in a particular sub-population) or reveal it is a proxy for
   something else (if the "true" effect is really, say,
   small-and-illiquid rather than small per se — a well-documented
   confound in the size-premium literature, e.g. size effects historically
   shown sensitive to liquidity/illiquidity controls). This is a real,
   citable statistical concern (the size effect's documented sensitivity to
   liquidity controls), not a generic "test more things" suggestion.
2. **Liquidity premium as an independent factor (Amihud-style
   illiquidity sort).** Full IRU breadth, zero new data, genuinely
   untested, and economically distinct from anything tried so far
   (H-001-H-012 never isolated a pure trading-liquidity sort).
3. **Deflated Sharpe Ratio / program-level overfitting control as
   research infrastructure.** Not a factor test, but the single highest-
   value non-factor research investment: without it, every subsequent
   confirmation (including H-011's existing one) is reported at a
   confidence level that ignores the total number of trials already run.
4. **Dividend payer-status tilt (binary).** Available, low-cost, distinct
   economic story (maturity/cash-generation risk tilt) from anything
   tested. Lower priority than #1-3 because it is a *weaker* economic prior
   than the interaction-factor forensics and does not address the
   measurement-layer gap.
5. **Thin-trading / non-synchronous-trading correction as a
   methodology upgrade.** Uses existing price/volume data only (no new
   source); directly addresses a specific, named frontier-market
   econometric concern (Scholes-Williams-type bias) that the current
   statistical layer has never tested for. Lower-ranked only because its
   payoff is a *robustness check* on existing results rather than new
   discovery.

Explicitly NOT recommended, despite "available" data: composite factors
(still transitively blocked, correctly identified in the prior audit —
needs ≥2 validated components and there is only 1).

---

## SECTION 8 — Maturity ratings by subsystem (no overall score, per instruction)

| Subsystem | Maturity level | Basis |
|---|---|---|
| Quant Engine (hypothesis lifecycle, pre-reg → placebo → OOS → registry) | **Production Research** | Real, permanent, mechanically-enforced registry; 12 real experiments; demonstrated regression safety across additive changes |
| Statistical inference layer (`stats.py`) | **Research Prototype** | Functionally adequate parametric+nonparametric pair, but missing HAC correction, DSR, PBO — a research team would not publish external claims on this layer as-is |
| Transaction cost model | **Institutional Prototype** | Real, itemized, regulatory-fee-accurate; missing a market-impact/slippage function, so it is realistic for the fee side and absent on the impact side |
| Coverage Gate / data-quality gating | **Production Research** | Mechanical refusal to run per-stock hypotheses on stale/failing data, independently verified this session |
| Universe construction (IRU) | **Institutional Prototype** | Rule-based, listing-rule-aware; survivorship-bias status not independently verified in this audit, which caps the rating until confirmed |
| Financial Statement Intelligence (FSI) extraction | **Research Prototype** | Real, hand-verified facts, but 10-ticker breadth is far below what any production factor research desk would consider usable coverage |
| AI Intelligence Layer (14-step reasoning) | **Not rated** | Out of scope for this audit pass; not independently re-inspected |
| Financial Reasoning Engine / Knowledge Graph / Research CLI | **Not rated** | Out of scope for this audit pass; not independently re-inspected |
| Documentation / research-note discipline | **Institutional Prototype** | Strong per-artifact discipline; missing a per-hypothesis index/manifest |
| Git/versioning discipline | **Production Research** | Clean tagging, correct annotated-tag semantics, high commit granularity |
| Portfolio construction / risk model | **Experimental** (in the sense of "does not yet exist") | No covariance/risk model, no multi-factor blending, appropriately gated behind "no valuation outputs authorized" |
| Execution / market-impact modeling | **Experimental** (does not yet exist) | Cost model covers fees only, not size-dependent slippage |

---

## SECTION 9 — Gap analysis vs. named firms/labs

*Renaissance, Two Sigma, Citadel, Bridgewater: no public methodology exists
for any of these firms' internal research process. Gaps against them are
stated only where they follow from PUBLIC information (e.g., known scale of
data/compute, publicly reported AUM implying execution infrastructure) —
not from any claim about their proprietary methods.*

| Dimension | Gap |
|---|---|
| **Data** | This platform: one market, ~10 years, 100-name breadth ceiling, 10-ticker fundamental-statement coverage. Any large systematic shop (public knowledge: scale of data licensing at firms like BlackRock/MSCI/WorldQuant) operates on multi-market, multi-decade, alternative-data-augmented datasets. This is the platform's single largest, most honestly-disclosed gap already (FSI ceiling, IRU size). |
| **Research** | Process discipline (pre-reg, placebo, permanent registry) is genuinely comparable to serious academic/institutional practice. Volume of validated output (1 confirmed factor) is nowhere near WorldQuant's publicly-stated scale of factor ("alpha") generation, though WorldQuant's own public claims about volume should not be taken as a benchmark for *quality* — volume and validated quality are different axes. |
| **Engineering** | Additive-extension discipline and regression-suite rigor are real strengths, arguably above the median for a research-stage codebase of this size. Gap: no CI/CD pipeline evidence found in this audit (not confirmed either way — flagged as unverified, not asserted absent). |
| **Statistics** | The clearest, most fixable gap (Section 1/5): no HAC correction, no DSR, no PBO, no cross-hypothesis multiple-testing control. Jane Street's and HRT's public engineering-blog content (to the extent it is public) consistently emphasizes rigorous statistical control over exactly this class of problem — this is the platform's most citable, concrete shortfall. |
| **Validation** | Placebo testing and independent look-ahead re-derivation are strong. Missing: PBO, DSR, non-synchronous-trading correction. |
| **Automation** | Phase4 orchestration (`run_phase4_xs`) genuinely automates the full stability-grid → correction → placebo → walk-forward → confidence-rating → IC-memo pipeline end to end — a real, demonstrated capability, not aspirational. |
| **Portfolio construction** | Does not exist (by design/guardrail, not oversight) — single-factor top-N baskets only, no blending, no optimizer, no risk budget. This is the platform's largest gap versus any actual asset manager (BlackRock Systematic, Bridgewater, Robeco, Dimensional all ultimately build portfolios, not just factor tests). |
| **Execution** | Fee-accurate cost model, no market-impact/slippage model, no live or paper trading, no broker connectivity. A production investment platform requires all of these; this platform requires none of them yet under its own current scope (research only). |
| **Risk** | No risk model (Section 1) — no factor covariance, no scenario/stress framework beyond the historical regime windows already used as OOS splits. |
| **Infrastructure** | SQLite-based registry, git-tracked experiment JSON exports, no evidence of distributed compute, cloud infrastructure, or multi-user access controls — appropriate for a single-researcher research program, a real gap versus any firm operating at institutional scale. |

---

## SECTION 10 — Three-year roadmap (guardrail-respecting, evidence-justified, no phase inflation)

Each phase below is justified by a specific gap identified above, not
invented for its own sake.

**Phase R1 — Statistical infrastructure hardening** *(justified by Section
1/5/9's statistics gap — the single most concrete, cited weakness found in
this audit)*
- Add: Deflated Sharpe Ratio (Bailey & López de Prado 2014) computed against
  the running ledger trial count; HAC/Newey-West-corrected inference path
  as an addition alongside the existing t-test; a non-synchronous-trading
  diagnostic check.
- Prerequisites: none — pure additive code against existing data.
- Dependencies: none.
- Research value: high — changes how every past AND future confirmation
  should be interpreted; directly serves "research quality over phase
  count."
- Risk: low (additive, no existing function modified, matches established
  convention).
- Expected scientific contribution: converts H-011's confidence rating from
  "confirmed under per-hypothesis correction" to "confirmed under
  program-wide overfitting control" — a materially stronger claim, or an
  honest downgrade if it doesn't survive, either of which is real
  information gained.

**Phase R2 — H-011 interaction forensics (Size×Volatility, Size×Momentum,
Size×Liquidity)** *(justified by Section 4/7 — diagnostic extension of the
only confirmed result, zero new data)*
- Prerequisites: R1 complete (so its results are read under corrected
  inference, not the old uncorrected t-test).
- Dependencies: none (all three inputs already exist at full IRU breadth).
- Research value: high — could either strengthen or meaningfully qualify
  the platform's only validated finding.
- Risk: low.
- Expected scientific contribution: clarifies whether NGX's size premium is
  a pure size effect or a liquidity/volatility-confounded proxy — a
  genuine, citable finding either way.

**Phase R3 — Liquidity and Dividend-payer-status as independent factor
tests** *(justified by Section 7, ranked below R1/R2 because they are new
discovery, not confirmatory forensics on existing evidence)*
- Prerequisites: R1 complete.
- Dependencies: none.
- Research value: medium-high — two genuinely untested, economically
  distinct factor families at full data availability.
- Risk: low.
- Expected scientific contribution: two more resolved (confirmed or
  rejected) entries in the permanent registry, each independently
  informative regardless of outcome.

**Phase R4 — FSI coverage expansion decision package** *(justified by
Section 3/4/9 — the single largest data gap, currently a standing,
unscoped backlog item)*
- Prerequisites: none technically, but requires an owner decision on labor/
  OCR investment — this phase is a **decision package**, not code: quantify
  the labor-hours or OCR-vendor cost to expand from 10 to ~100 tickers,
  present it as a scoped owner decision.
- Dependencies: owner approval of a labor or vendor budget; possibly an
  OCR-engine choice (already a known open item).
- Research value: very high if approved — unlocks 11 of 16 named factor
  families in one move; the report itself has value even if declined, since
  it converts a vague "blocked" status into a concrete cost/benefit number.
- Risk: none to the research program (a decision document, not code); real
  cost/time risk if approved, to be scoped honestly rather than
  underestimated.
- Expected scientific contribution: none directly (it's an unlock, not a
  finding) — but it is the highest-leverage single decision available to
  the entire program.

**Phase R5 — Survivorship-bias and point-in-time universe reconciliation
audit** *(justified by Section 3 — an identified, unresolved blind spot)*
- Prerequisites: none.
- Dependencies: none — uses existing IRU construction code and historical
  listing records already in the database.
- Research value: high as a validity check — if survivorship bias is found,
  it would require re-evaluating every hypothesis tested to date; if not
  found, it removes the single largest unverified assumption underlying
  every result so far.
- Risk: low to execute; potentially high-impact findings (which is exactly
  why it should be done deliberately rather than left implicit).
- Expected scientific contribution: either a clean bill of health
  (strengthening confidence in H-001-H-012 as reported) or a material
  correction to the record — both are genuine research value.

**Phase R6 — Share-Issuance event-type classification pass** *(justified by
Section on data-partial candidates — a scoped, bounded internal task, not a
new data source)*
- Prerequisites: none.
- Dependencies: internal labor to classify `submission_type`/filing text
  into real corporate-action types; no vendor needed.
- Research value: medium — unlocks one additional factor family (Share
  Issuance / dilution effects, Loughran & Ritter 1995-style).
- Risk: low.
- Expected scientific contribution: one more testable, economically
  distinct hypothesis family, contingent on classification accuracy being
  validated before use (not just assumed).

**Explicitly deferred, not scheduled, and why:**
- **Portfolio construction / risk model / multi-factor blending**: correctly
  gated behind having ≥2-3 validated, independent factors first (currently
  1). Building this now would be building infrastructure for research that
  does not yet exist — exactly the "phase inflation" this roadmap is
  instructed to avoid.
- **Execution / market-impact modeling, live or paper trading**: no
  justification exists yet — this platform has never been authorized to
  activate any valuation or recommendation output, so an execution layer
  has no consumer. Would require a prior owner decision changing platform
  scope, per the existing guardrails.
- **Cross-market expansion (broader African frontier markets)**: correctly
  identified in Section 2 as requiring per-market cost-model and
  regime-calibration rework; not scheduled until NGX's own statistical
  layer (R1) and data ceiling (R4) are addressed, since replicating an
  under-corrected methodology across more markets would compound the
  multiple-testing problem rather than diversify it away.

**No AI-buzzword phases are proposed.** Every phase above is either a
statistical-methodology fix already named in the finance literature (López
de Prado, Harvey-Liu-Zhu), a diagnostic extension of an existing real
result, a bounded data-classification task, or an owner-facing decision
package — not a speculative capability.
