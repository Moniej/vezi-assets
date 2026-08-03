# Pre-Registration — H-016: Liquidity (family: Liquidity, new family)

*Drafted 2026-08-03, BEFORE any H-016 experiment run. Follows
`docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`'s Rank-1 recommendation.
No experiment has been executed, no signal-construction code has been
written, and no config has been frozen as of this document — per explicit
instruction, this is pre-registration only. Implementation is a separate,
later step in the standing methodology (Pre-registration → Owner Review →
Implementation → Validation), not bundled into this document. Changes
after first results = new hypothesis ID, per unbroken platform convention.*

---

## 0. What kind of investigation this is (stated up front)

**This is a genuinely new, standalone factor hypothesis — not an
extension, refinement, or forensic decomposition of H-011 (Size).**
H-013 already asked "does the Size premium survive controlling for
Liquidity" (answer: no, it is concentrated in the liquid half) — a
question about SIZE. H-016 asks a different question entirely: **does
Liquidity itself, evaluated on its own terms against the whole-universe
benchmark, carry a return premium in either direction?** A confirmed or
rejected H-016 does not alter H-011's own ledger entry or Validated
status in any way; it is evaluated entirely on its own pre-registered
criteria, exactly as H-013/014/015 did not alter H-011's status regardless
of their own outcome.

The motivation for testing this now, rather than at some other time, is
concrete and disclosed rather than arbitrary: Phase R2 (completed
2026-08-03, one day before this document) left a specific, unresolved
empirical tension on the permanent record — H-011's own capacity report
found its historically strongest per-regime contributors were thin/
illiquid names, while H-013's bucket-level double sort of the *whole*
universe found the Size premium concentrated in the *liquid* half, with
the illiquid half a clean statistical null. Both facts are true and both
remain on record, explicitly not reconciled by assumption
(`docs/PHASE_R2_SIZE_INTERACTIONS_REPORT_2026-08-03.md`, "Outstanding
Observation"). H-016 is designed to investigate Liquidity as an
independent object of study, which may or may not resolve that tension —
it is not designed to force a resolution in either direction.

---

## 1. Audit of all existing evidence relevant to Liquidity

Checked directly, not recalled, before drafting this section:

- **`backtest_xs.py::liquidity_scores()`** already exists (built
  2026-08-03 for Phase R2's double-sort machinery) and is already
  unit-tested (`scripts/rehearse_xs_size_interaction.py`, checks I1-I5).
  Its own docstring states explicitly: *"NOT wired into
  scores_for_method/xs_rank et al — this is a new dimension consumed only
  by xs_size_interaction below, not a standalone tradeable Liquidity
  factor method (that remains a separate, not-yet-run candidate)."* This
  is the platform's own code-level confirmation that H-016 has never been
  run, in any form, as a standalone test.
- **H-013 (Size × Liquidity, rejected 2026-08-03)** is the only prior
  experiment to touch Liquidity data at all. Its evidence: high-liquidity
  bucket Sharpe 2.27 (placebo p=0.0099), low-liquidity bucket Sharpe 0.57
  (placebo p=0.70, a clean null, real Sharpe below its own placebo mean).
  **This evidence is about whether SIZE survives inside each liquidity
  bucket — it says nothing directly about whether Liquidity itself, sorted
  on its own terms without a Size pre-filter, carries a premium.** It is
  cited here as motivation and as a source of prior expectation to be
  falsified or confirmed, not as a substitute for the test itself.
- **H-011's capacity reports** (every cross-sectional hypothesis run to
  date) document ADTV/capacity as a friction that binds severely at the
  small-cap end of the universe — consistent evidence that liquidity
  varies enormously across the IRU, a precondition for this hypothesis to
  even be testable with reasonable cross-sectional dispersion, but again
  not evidence of a premium's existence or direction.
- **`docs/FACTOR_CANDIDATE_REGISTRY.md §A1`** (2026-08-02): named
  Liquidity as "Available now, zero new data required" months before
  Phase R2 built any of the scoring machinery — the data-readiness
  finding predates and is independent of Phase R2's own results.
- No other hypothesis on this platform (H-001 through H-015) uses ADTV or
  any liquidity measure as its own primary score.

## 2. Literature review — the liquidity premium, with emphasis on frontier markets

- **Amihud & Mendelson (1986, *Journal of Financial Economics*)**: the
  founding result — investors demand a return premium for holding
  less-liquid assets, compensating for higher effective bid-ask spread
  and transaction cost. Developed-market origin, US equities.
- **Amihud (2002, *Journal of Financial Markets*)**: operationalizes
  illiquidity as `ILLIQ = |return| / value_traded`, a ratio this
  platform's own `adtv60` panel can proxy (this hypothesis uses the ADTV
  level directly, per `liquidity_scores()`'s existing construction, rather
  than building the full Amihud ratio — a disclosed simplification, see
  §11).
- **Pástor & Stambaugh (2003, *Journal of Political Economy*)**: liquidity
  as a systematic, PRICED risk factor (not just a characteristic) — the
  strongest version of the claim, requiring a market-wide liquidity
  risk-loading estimate this platform's engine does not currently build;
  H-016 tests the weaker, characteristic-based version (cross-sectional
  sort on own liquidity), consistent with every other factor this platform
  has tested (H-011's size sort is likewise characteristic-based, not a
  risk-loading estimate).
- **Bekaert, Harvey & Lundblad (2007, *Review of Financial Studies*,
  "Liquidity and Expected Returns: Lessons from Emerging Markets")**: the
  closest direct precedent — confirms a measurable illiquidity premium in
  emerging markets, but explicitly flags that raw illiquidity measures in
  thin markets require correction for zero-return days (non-trading) before
  the premium can be trusted as real rather than a measurement artifact.
  This is the single most load-bearing citation for this pre-registration's
  robustness-check design (§6).
- **Lesmond, Ogden & Trzcinka (1999, *Review of Financial Studies*)**: the
  zero-return-days measure as a transaction-cost/staleness proxy, used
  here as a mandatory robustness diagnostic, not the primary signal.
- **No frontier-market (as distinct from emerging-market) study of this
  exact question on NGX was found in this review.** This is stated as an
  absence of evidence in this review, not as evidence of absence in the
  wider literature — a search was not exhaustively conducted across every
  possible outlet, and this limitation is disclosed rather than glossed
  over.

## 3. Frontier / emerging / developed market classification

**Frontier-market technique, testing a universal mechanism under
frontier-specific conditions.** The underlying illiquidity-premium theory
(Amihud & Mendelson) is developed-market in origin and universal in
applicability. Its closest validated precedent (Bekaert, Harvey &
Lundblad) is emerging-market evidence, one classification tier above NGX.
What makes this test frontier-specific rather than a repetition of that
emerging-market work: NGX's own documented cross-sectional liquidity
dispersion is extreme even by emerging-market standards (every hypothesis
tested on this platform reports 90%+ of trade legs rejected at ₦1bn AUM;
H-011's own median leg capacity is ₦694,336, 10-15× worse than any other
tested hypothesis) — a market this thin is exactly where both the
theoretical mechanism (limits to arbitrage in illiquid names) AND its
principal confound (non-synchronous/stale pricing, §5) are expected to be
strongest, simultaneously. This hypothesis does not assume the frontier
classification implies the effect WILL be found or will run in the
classic direction — only that NGX is a genuinely informative, rather than
redundant, place to test it. Institutional frontier-market investors would
plausibly treat a correctly-measured (staleness-corrected) result here as
differentiated evidence precisely because so few venues are this thin;
this document takes no position on what that result will be.

## 4. Economic mechanism

Two economically legitimate mechanisms are in tension, and this
hypothesis is designed to adjudicate between them using evidence, not
assume one in advance:

- **Illiquidity-premium mechanism (classic, Amihud & Mendelson
  direction)**: investors require compensation for the higher transaction
  cost and slower execution of illiquid names; on NGX specifically, thin
  trading and limited institutional participation mean fewer
  arbitrageurs are positioned to bid away this discount even once
  identified — a limits-to-arbitrage argument, amplified (not
  contradicted) by frontier-market thinness. Under this mechanism, the
  **long-illiquid** leg should show a positive premium over the
  whole-universe benchmark.
- **Liquidity-premium mechanism (the direction Phase R2's own evidence
  hints at)**: if H-013's finding — Size premium concentrated in the
  liquid half — reflects something more general about how returns behave
  across NGX's liquidity spectrum (rather than something specific to the
  Size-selected subset H-013 tested), a whole-universe liquidity sort
  could show the **long-liquid** leg outperforming instead. A plausible
  economic story for this direction: genuine price discovery and
  fundamental-information incorporation may require a minimum level of
  trading activity that illiquid NGX names structurally lack, such that
  "illiquid" partly proxies for "under-priced-in a stale, uninformative
  way" rather than "compensated for risk." This is a real, if less
  textbook, economic mechanism — distinct from, and this document does
  not conflate it with, a pure microstructure artifact (§5), though the
  two can be hard to tell apart without the robustness checks in §6.

**Both directions are pre-registered below (§7) as named, competing legs.
Neither is assumed correct. The hypothesis is confirmed only if one
(not necessarily the theoretically "expected") leg clears the full,
pre-declared bar.**

## 5. Frontier-market confounds (identified before any data is touched)

- **Non-synchronous trading / stale pricing (Scholes-Williams effect)**:
  illiquid NGX names may go multiple days without a trade; a "return"
  recorded on a day with no actual transaction is stale, not informative,
  and can produce spurious autocorrelation or an artificially smoothed
  return series. This is the single largest confound specific to this
  hypothesis and is directly addressed by a mandatory lagged-return
  robustness check (§6) — no prior hypothesis on this platform has needed
  this check in the same way, because none has sorted directly on
  liquidity before.
- **Zero-return days as a measurable staleness proxy**: per Lesmond,
  Ogden & Trzcinka (1999), the fraction of zero-return trading days is a
  direct, computable proxy for effective illiquidity/staleness using data
  already in `equity_prices` — no new source required. A materially higher
  zero-return-day rate in whichever leg shows the "premium" is a red flag
  that must be reported, not omitted.
- **Bid-ask bounce**: with wide effective spreads on illiquid names, a
  raw close-to-close return series can show artificial mean-reversion or
  volatility unrelated to true price movement — a related but distinct
  concern from staleness, both disclosed here rather than assumed away.
- **Size/Liquidity entanglement**: illiquid and small-cap names
  substantially overlap on NGX by construction (H-011's own prereg
  disclosed this in its own Expected Interaction section, 2026-07-22,
  before H-016 was conceived). A positive H-016 result could simply
  re-discover H-011 under a different label rather than represent
  independent information — addressed directly and mandatorily in §11-12,
  not treated as a minor caveat.
- **Thin-name idiosyncratic noise**: a handful of very illiquid IRU
  members could dominate an equal-weighted illiquid-leg portfolio's
  measured return with idiosyncratic, non-repeatable moves — the
  platform's existing `_eligible()` breadth guards (`len(elig) >= 10`)
  mitigate but do not eliminate this; per-cell eligible-name counts must
  be reported alongside every result (§9).

## 6. Statistical plan

Applied identically to both pre-registered legs (§7):

- **Look-ahead controls**: inherited from the existing PIT engine
  (formation-date-only scoring, `_eligible()` breadth guards) — no new
  look-ahead risk, since `liquidity_scores()` is already built on the same
  PIT-safe `load_panel()` construction every other cross-sectional
  hypothesis uses.
- **Placebo testing**: 100 iterations, same seeded, persistence-preserving
  ticker-relabeling convention as every prior xs_* hypothesis (ONE fixed
  permutation per iteration, applied consistently across all formation
  dates).
- **HAC / Newey-West inference**: `stats.newey_west_tstat` on daily
  excess-vs-benchmark returns, automatic Bartlett bandwidth — reported
  alongside, never in place of, the i.i.d. t-test, per METH-001 convention.
- **Deflated Sharpe Ratio**: computed on the real-risk-free basis
  (METH-002/METH-001b convention) against the existing 15-hypothesis trial
  pool. Reported as context, consistent with how every hypothesis since
  METH-001 has reported it — **not** treated as an additional confirmation
  bar beyond the six criteria in §8.
- **Multiple-testing treatment**: Holm and Benjamini-Hochberg across the
  full 6-cell stability grid (§7), identical correction discipline to
  H-011's own grid.
- **Out-of-sample validation**: full walk-forward with an untouched final
  OOS window (2025-01-02 → 2026-06-30), identical to H-011's own regime
  structure. **This is explicitly NOT scoped down the way Phase R2's
  forensic decomposition was** (Phase R2 reused H-011's own already-cleared
  OOS guarantee because it was a diagnostic of an already-validated
  hypothesis; H-016 is a fresh standalone claim and must clear the SAME
  full gauntlet H-011 itself cleared, not a reduced version).
- **Look-ahead audit**: standard PIT discipline, same machinery as every
  existing hypothesis — no new mechanism required.
- **Mandatory hypothesis-specific robustness checks** (beyond the standard
  suite, required by the confounds in §5):
  1. **Zero-return-day rate per leg**: computed directly from
     `equity_prices`, reported per bucket/leg. A materially elevated rate
     in whichever leg shows the stronger result must be disclosed as a
     staleness confound in the final report, not silently omitted.
  2. **Lagged-return sensitivity**: each leg's daily excess return series
     recomputed using a 1-trading-day lag on the illiquid-side
     constituents' returns; if the apparent premium disappears or
     reverses under this correction, the result does NOT meet confirmation
     criteria regardless of the unlagged figure (§8, criterion 7).
  3. **Spearman rank correlation, Liquidity score vs. Size score**,
     computed at every formation date and reported as a distribution
     (mean, range) — quantifies entanglement with H-011 directly, before
     any interpretation is offered (§11).
  4. **Sensitivity to ADTV lookback window**: 60-day base (matching the
     existing `adtv60` panel already computed by `load_panel`), with
     20-day and 120-day sensitivity variants reported alongside the base
     cell — consistent with how every prior score-construction hypothesis
     has been stress-tested.

## 7. Pre-registered directions — both legs, neither assumed correct

**Leg A — Long-Illiquid** (classic Amihud & Mendelson direction): long the
LEAST liquid 20 names by trailing 60-day ADTV within the IRU,
equal-weighted, quarterly rebalance, vs. the equal-weighted-IRU benchmark.
Score reuses `liquidity_scores()`'s existing convention unmodified
(negative standardized ADTV; nlargest selects least liquid).

**Leg B — Long-Liquid** (the direction Phase R2's own evidence hints at):
long the MOST liquid 20 names by the same trailing 60-day ADTV measure
within the IRU, equal-weighted, quarterly rebalance, vs. the same
benchmark. Requires only a sign inversion of the existing score (positive
standardized ADTV; nlargest selects most liquid) — a small, additive
change at implementation time, not a new data construction.

Both legs share: IRU v2 membership (PIT, rename-canonical), `equity_prices_asof`
with `min_confidence = 0.9`, **vintage = 2026-07-21**, `requires_coverage_gate = true`,
eligibility ≥120 valid observations in the trailing 12-month window (same
discipline as every prior xs_* hypothesis), ADTV participation cap 10%
(platform default), execution lag 1 trading day, retail cost schedule from
`db`.

**Stability grid (per leg, 6 cells, matching H-011's own grid exactly)**:
`rebalance ∈ {quarterly, semiannual}` × `top_n ∈ {15, 20, 30}`.

**Windows**: development 2016-01-02 → 2024-12-31; **untouched OOS
2025-01-02 → 2026-06-30**; same three regimes as every prior per-stock
hypothesis (pre_float / float_shock / oos_2025_26).

**Direction is decided by evidence, not chosen in advance beyond these two
named legs.** If both legs meet the confirmation bar, both are reported
honestly and the finding is that liquidity dispersion itself (in either
direction) carries information — an unusual but legitimate outcome that
would itself require its own honest interpretation, not a forced choice
between them.

## 8. Confirmation requires ALL of (per leg, evaluated independently)

1. Placebo p ≤ 0.05 on the base configuration (top_n=20, quarterly).
2. Base net excess vs. EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 4 of 6 grid cells with positive net excess, same direction.
4. ≥ 1 cell significant under Benjamini-Hochberg at FDR 0.10.
5. No single regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered (`failure_conditions.py`;
   capacity findings evaluated separately, per H-011's own established
   convention — a severe capacity constraint alone does not reject a
   signal-quality verdict).
7. **The lagged-return robustness check (§6, item 2) does not eliminate
   or reverse the base-cell result.** This criterion is unique to H-016
   and is not waivable — a result that only survives on unlagged, possibly
   stale returns does not confirm.

## 9. Rejection (any one suffices, per leg)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross
excess · regime concentration > 80% · any signal-quality failure condition
· the lagged-return check eliminates or reverses the result (§8, criterion
7) · eligible-name count per grid cell falls below the platform's standard
`len(elig) >= 10` breadth guard at more than an isolated handful of
formation dates (to be quantified in the implementation phase before any
result is interpreted, not assumed adequate in advance).

If **neither** leg meets the confirmation bar, H-016 is rejected in full —
this is explicitly recognized in advance (§4) as at least as likely an
outcome as confirmation, given Phase R2's own evidence is a real prior
against a clean, one-directional effect existing at all.

## 10. Economic Capacity Validation (mandatory, pre-registered before implementation)

**Why this section exists, stated up front**: every prior hypothesis on
this platform reports capacity as a POST-HOC finding (H-011's ₦694,336
median leg capacity was measured after the signal was already confirmed).
Liquidity is different in kind, not just degree: the platform's OWN
capacity-report machinery (`capacity_report()`, driven by `panel["adtv60"]`)
and H-016's own SIGNAL (also driven by `panel["adtv60"]`) share the same
underlying data. A liquidity factor that only "works" on names too thin to
actually deploy meaningful capital into is not a deployable finding — it
would be statistically real and simultaneously economically hollow. This
platform's charter ranks false positives as more costly than false
negatives, and an academically-significant-but-undeployable liquidity
result is exactly the kind of false positive a fund would be misled by if
this section did not exist. This is **a pre-registered robustness check
layered on top of §8/§9's confirmation and rejection criteria, not a new
hypothesis and not a change to those criteria** — the statistical verdict
is still decided at the unfiltered base configuration, exactly as every
prior hypothesis has been evaluated. This section produces a SEPARATE,
additionally-reported **Economic Capacity Verdict**, mirroring the
platform's existing, established split between `capacity_below_minimum`
(scalability) and `cost_drag_eliminates_excess` (signal quality) in
`failure_conditions.py` — capacity has never been allowed to silently
overturn a signal-quality verdict on this platform, and it will not do so
here either; it is reported alongside, with equal prominence, not folded
in.

### 10.1 Pre-registered questions (fixed before any data is touched)

1. **Does the premium survive progressively stricter minimum-ADTV
   filters?** Answered via the filter ladder in §10.2, applied to
   whichever leg (A or B) meets the §8 confirmation bar at the unfiltered
   base configuration.
2. **How many securities remain investable after each filter?** Reported
   per ladder rung as the eligible-name count per formation date
   (min / median / max across the sample), including rungs where the
   count falls below the platform's own `len(elig) >= 10` breadth floor —
   such rungs are marked **infeasible**, not silently dropped or treated
   as a pass/fail statistical result.
3. **Does performance degrade as capacity requirements increase?** Base-
   cell net excess return, Sharpe, and placebo p-value are recomputed at
   EVERY ladder rung and reported as a trend, not just a single pass/fail
   value at the strictest rung.
4. **At what capacity threshold does the signal cease to be economically
   meaningful?** Answered by the pre-registered stopping rule in §10.3,
   fixed now, before any rung is run.

### 10.2 The filter ladder (fixed values, not chosen after seeing results)

A new eligibility floor is applied ON TOP OF the existing
`_eligible()`/`len(elig) >= 10` breadth guard, at each formation date,
before either leg's universe is scored: a minimum trailing 60-day ADTV
(NGN), swept across six rungs:

**₦0 (no additional filter, the §7/§8 base case) → ₦1,000,000 →
₦5,000,000 → ₦10,000,000 → ₦25,000,000 → ₦50,000,000 → ₦100,000,000.**

At each rung, the eligible universe is names passing BOTH the existing
breadth guard AND this ADTV floor. The base-cell configuration (top_n=20,
quarterly) is re-run at every rung; the full 6-cell stability grid is NOT
re-run per rung (that would be a 42-run ladder, a disproportionate
compute cost for a robustness check rather than the primary confirmation
test) — this is a disclosed scoping decision, not a silent shortcut,
consistent with Phase R2's own precedent of explicitly scoping and
disclosing compute-driven reductions rather than hiding them.

**A disclosed asymmetry between the two legs, stated in advance rather
than discovered while interpreting results**: for **Leg B (long-liquid)**,
raising the ADTV floor shrinks the pool to sort FROM but should not
mechanically remove Leg B's own top holdings (already the most liquid
names by construction) — a "denominator" effect on the benchmark and
selection pool. For **Leg A (long-illiquid)**, raising the ADTV floor
works directly AGAINST the leg's own economic logic: it progressively
excludes the very least-liquid names that leg's own top-20 selection is
built to include, so the ladder for Leg A should be read as "how much of
the illiquid-name premium survives once the very worst, most untradeable
names are excluded from consideration" rather than a neutral capacity
sweep. Both readings are stated now, before any rung is run, specifically
to prevent this asymmetry from being explained away opportunistically
after seeing which direction the numbers move.

### 10.3 Pre-registered stopping rule — the Economic Capacity Ceiling

Fixed now, before any rung is run. The **Economic Capacity Ceiling** for a
confirmed leg is the ADTV floor of the STRICTEST ladder rung (§10.2) at
which ALL of the following still hold simultaneously:

- Eligible-name count per formation date remains ≥ 10 (the platform's own
  standing breadth floor) at every formation date in the sample, not just
  on average.
- Placebo p-value at that rung remains ≤ 0.05 (the same bar as §8,
  criterion 1 — the filter must not itself have destroyed statistical
  significance).
- `capacity_report()`, run at that rung's own filtered universe and at a
  pre-registered reference AUM of **₦100,000,000** (chosen as a
  realistic small frontier-market fund size, deliberately distinct from
  the platform's own ₦1bn default used elsewhere for signal-quality
  testing — using the ₦1bn default here would understate capacity at the
  scale a fund actually deploying this specific, admittedly
  capacity-constrained signal would operate at), rejects fewer than 50%
  of trade legs.

The STRICTEST rung clearing all three conditions is reported as the
Economic Capacity Ceiling — e.g., "the signal remains statistically
significant and minimally deployable up to a ₦25,000,000 minimum-ADTV
floor, beyond which [breadth / significance / capacity] fails." If NO
rung beyond ₦0 clears all three, the Economic Capacity Ceiling is reported
as **₦0 — statistically real but not economically deployable beyond the
platform's own already-disclosed severe-capacity-constraint pattern
(H-011's own precedent)**. If EVERY rung up to and including ₦100,000,000
clears all three, the ceiling is reported as **"≥ ₦100,000,000, not yet
bounded by this ladder"** rather than assumed unlimited.

**This ceiling does not retroactively change the §8/§9 statistical
verdict.** A confirmed signal with a ₦0 Economic Capacity Ceiling remains
`confirmed` in the ledger (exactly as H-011 remains `Validated` despite
its own severe capacity constraint) but must carry the Economic Capacity
Ceiling figure prominently in `FACTOR_REGISTRY.md`, with equal visibility
to the statistical evidence — not buried as a footnote.

## 11. Comparison against every previously tested hypothesis — independence check

| Prior hypothesis | Construction input | Overlap with H-016's Liquidity score |
|---|---|---|
| H-001 (sector momentum) | sector-level index momentum | None — different engine, different unit of analysis (sector vs. stock) |
| H-002 (untested, blocked) | total-return / dividend | None |
| H-003 (event catalyst) | discrete macro/regulatory event dates | None |
| H-004 (oil lead-lag) | Brent crude, FX | None |
| H-005 (MPC window) | MPC event dates | None |
| H-006 (PEAD) | earnings-surprise event reaction | None |
| H-007/H-009/H-010 (momentum family) | trailing return | Low — momentum and liquidity are different constructs, though thin names can show noisier momentum; not previously quantified, will be measured (§11.1) |
| H-008/H-012 (low-vol family) | realized return volatility | Low-Medium — illiquid names often show measurement-inflated volatility (a version of the staleness confound in §5), a genuine but distinct concern from Size entanglement |
| **H-011 (Size)** | market capitalization | **High, by construction** — the central independence risk for this hypothesis, addressed directly below (§11.1) |
| H-013/014/015 (Size interactions) | Size × {Liquidity, Momentum, Volatility} bucket splits | H-013 shares the same `panel["adtv60"]` INPUT but asks a structurally different question (does Size survive within a liquidity bucket, vs. does Liquidity itself carry a premium on the whole universe) — not a repeated test, but the closest prior work, cited throughout this document as motivation |

### 11.1 Could H-016 simply be a proxy for H-011 (or another prior effect)?

**Stated directly, as required**: yes, this is a real and material risk,
not a remote one. Small-cap and illiquid names overlap substantially on
NGX (disclosed in H-011's own prereg, 2026-07-22, before H-016 existed).
If Leg A (long-illiquid) confirms, it could mean either (a) liquidity
itself is independently compensated, or (b) H-016 has simply re-discovered
H-011's own signal, filtered through a highly correlated but different
characteristic. **This pre-registration does not permit declaring Leg A
"independent" on the strength of a positive result alone.** The mandatory
Spearman rank-correlation diagnostic (§6, item 3) must be computed and
reported for every confirmed leg; if the correlation with the Size score
is high (a threshold of |ρ| > 0.6, chosen here in advance rather than
after seeing the number, as a reasonable but not precision-tuned cutoff)
the confirmed result must be reported as **"confirmed, but not
demonstrated independent of H-011"** — a distinct, separately-logged
outcome from a clean, low-correlation confirmation, mirroring the
distinction the platform already draws between "confirmed" and
"confirmed-but-capacity-constrained" for H-011 itself. Leg B (long-liquid)
carries a symmetric version of the same risk (liquid names may
overlap with LARGE-cap names) and is subject to the identical diagnostic
requirement.

No claim of clean independence from H-011 is made in advance of this
diagnostic, for either leg, under any circumstance.

## 12. Rejected alternatives

- **Amihud (2002)'s full `ILLIQ = |return| / value_traded` ratio**,
  instead of the ADTV-level score `liquidity_scores()` already computes.
  Rejected for this pre-registration: the ADTV-level construction is
  already built, already unit-tested, and Amihud's own ratio is highly
  correlated with ADTV in practice for exactly the reason it was designed
  to capture (illiquidity) — reusing the existing, validated construction
  avoids introducing new, unvalidated signal-construction code for a
  first pass. Named here as a natural ROBUSTNESS variant for a later
  sensitivity pass if H-016 confirms, not a substitute for the primary
  test.
- **A Pástor-Stambaugh-style systematic liquidity risk-loading estimate**
  instead of a characteristic-based cross-sectional sort. Rejected: this
  platform's engine is a sort-and-simulate backtester (established
  precedent, H-013-015's own §8), not a factor-loading estimation
  framework; building one would be a materially larger, separately-risky
  undertaking than reusing the existing, validated engine — the same
  reasoning that rejected a regression-based approach for Phase R2.
- **Terciles or a continuous-score long-short design** instead of a
  top/bottom-20 long-only tilt. Rejected for consistency: H-011's own
  design (long-only, top-20, quarterly) is the platform's established
  per-stock hypothesis template; deviating from it for H-016 alone would
  make cross-hypothesis comparison (capacity, turnover, DSR context)
  harder to interpret than it needs to be, without a compelling reason to
  depart from convention.
- **Skipping the lagged-return robustness check** to keep the design
  identical to H-011's own template. Rejected explicitly: H-016 is the
  platform's FIRST hypothesis to sort directly on a liquidity
  characteristic, and the staleness confound (§5) is real and specific to
  this construction in a way no prior hypothesis's own template needed to
  address — omitting it would be a methodology gap, not fidelity to
  convention.

## 13. Multiple-testing treatment

6 cells under BH within each leg (12 total across both legs, corrected
separately per leg, not pooled — each leg is a distinct, named claim).
Program-level ledger count (16 hypothesis IDs through this wave, per
`docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`) reported in the IC memo,
consistent with every hypothesis since METH-001. Per the platform's own
≤2-active-hypotheses governance rule, H-016 and H-017 (Dividend
Payer-Status, named in the same Wave 4 document but not yet
pre-registered) together constitute this wave's full active research
capacity — H-016 is recommended to proceed first.

## 14. Expected Interaction with Existing Factors

- Family: **Liquidity** — first entry in this family; distinct from Size,
  Momentum, and Volatility, though empirically entangled with Size on NGX
  (§11, §11.1) in a way that must be measured, not assumed, before any
  claim of independence.
- Expected correlation with H-011 (Size): **High** by construction — this
  is the single largest open question this hypothesis exists to resolve
  quantitatively, not a footnote (§11.1).
- Expected correlation with H-007/H-009/H-010 (Momentum): Low, not
  previously measured on this platform; to be reported alongside the
  primary result.
- Expected correlation with H-008/H-012 (Volatility): Low-Medium — thin
  names can show measurement-inflated volatility, a partially shared
  confound (staleness) rather than a shared economic mechanism; the two
  factors are conceptually distinct (compensation for trading friction vs.
  compensation for return variance) even where their measured overlap is
  non-trivial.
- Diversification value if confirmed AND shown independent: would give the
  library its SECOND validated factor with a friction/microstructure
  economic story (alongside H-011), materially different in kind from a
  future information- or trend-based confirmation (e.g., a hypothetical
  future momentum retest) — directly relevant to a future Risk Engine
  regardless of whether the ALPHA claim itself survives the independence
  diagnostic.
- Portfolio construction value if confirmed but shown NOT independent of
  H-011: would still be valuable as CONFIRMATORY evidence deepening
  understanding of H-011's own mechanism (consistent with, not
  contradicting, Phase R2's finding that Size's premium concentrates in
  the liquid half) — a legitimate and useful outcome, not a failed test,
  per the same standard applied to H-013-015's own nuanced verdicts.
- Independence rationale: unlike every prior hypothesis (which used
  return, cap, or discrete event constructions with low mutual overlap),
  this is the first hypothesis whose primary construction input (ADTV) is
  ALSO a component the platform's OWN capacity-report machinery has used
  in every other hypothesis's own diagnostics — a genuinely closer
  relationship to existing platform infrastructure than any prior
  hypothesis has had to its own inputs, disclosed here rather than
  understated.

## 15. Known limitations (pre-declared)

L1 Uses the ADTV-LEVEL construction already built (`liquidity_scores()`),
not the full Amihud (2002) `|return|/value_traded` ratio — a disclosed
simplification (§12), not an oversight. L2 Full-issue, not float-adjusted
liquidity measure (no shares-outstanding data exists on this platform;
same limitation H-011 already carries). L3 Price-only returns (no dividend
reinvestment), same as every prior hypothesis. L4 Retail cost schedule
'assumed' confidence, same as every prior hypothesis. L5 Real
risk-free-rate coverage gap before 2015-07-23 (METH-002), same as every
prior hypothesis using the real-rf lens. L6 Turnover and capacity are
UNMEASURED on real data until this run — neither is asserted low or high
in advance beyond the qualitative expectation in §9 (illiquid-leg capacity
plausibly poor, mirroring H-011's own economic logic); both are the run's
own measurement objective. L7 The staleness/non-synchronous-trading
robustness check (§6) is a NEW addition to this platform's standard
statistical suite — its own false-negative/false-positive properties on
NGX-scale data have not themselves been previously validated on this
platform (no prior hypothesis needed it); this is disclosed as a
methodology limitation of the check itself, not just of the hypothesis it
serves. L8 The |ρ| > 0.6 independence threshold (§11.1) is a reasonable,
pre-declared cutoff, not a precision-calibrated one — stated as a
judgment call, not a proven-optimal value.

---

## Status

**Pre-registration complete. No experiment has been run. No signal-
construction code exists yet.** Per the standing methodology
(Pre-registration → Owner Review → Implementation → Validation), this
document is submitted for owner review before any implementation begins.
