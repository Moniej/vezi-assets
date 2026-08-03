# Pre-Registration — H-013/H-014/H-015: Size Interaction Forensics

*2026-08-03. Frozen BEFORE any interaction backtest is run. Phase R2 of
`docs/INSTITUTIONAL_AUDIT_WAVE2_2026-08-02.md`'s roadmap. Per the standing
directive, includes the mandatory benchmarking sections before
implementation.*

## 0. What kind of investigation this is (stated up front, per the owner's explicit requirement)

**This is a forensic decomposition of H-011 (Size), not a new standalone
factor search.** H-011 is the platform's only confirmed factor. Its own
existing documentation already contains a specific, concrete clue this
investigation follows up on: H-011's capacity report found its return
"genuinely concentrated in the most illiquid tail of the universe" (top
contributors per-regime were consistently thin/illiquid names — LASACO,
MULTIVERSE, NCR), and its median leg capacity (₦694,336) is 10-15x worse
than any other tested hypothesis. **This is already suggestive that
H-011's premium may not be a pure size effect — it may be partly or wholly
a liquidity effect that happens to correlate with size in this market.**
The academic literature makes the same general point for other markets:
Asness, Frazzini, Israel & Moskowitz (2018, *Journal of Financial
Economics*, "Size Matters, If You Control Your Junk") show the small-cap
premium in US equities is sensitive to controlling for quality/junk
characteristics; a closely related, long-documented concern (going back to
at least Amihud & Mendelson, 1986) is that size and illiquidity are
naturally correlated in most equity markets (smaller firms tend to be less
liquid), making a "pure" size effect hard to isolate without an explicit
double sort. **H-011 was never tested for this** — it was validated as a
standalone tilt against the whole-universe benchmark, which cannot by
itself distinguish "smallness compensates for something" from "smallness
correlates with illiquidity/low-momentum/high-volatility, and THAT is what
is compensated."

Consequently: **no new ledger status is being sought for "Liquidity,"
"Momentum," or "Volatility" as standalone factors here.** Those remain
separate, not-yet-run candidates per `docs/FACTOR_CANDIDATE_REGISTRY.md`.
H-013/H-014/H-015 test a narrower, specific claim each: *does H-011's size
premium survive, weaken, or disappear once the universe is split by
Liquidity / Momentum / Volatility first?*

## 1. Research questions

- **H-013 (Size × Liquidity)**: Does the Size premium exist independently
  within BOTH a high-liquidity half and a low-liquidity half of the IRU,
  or is it concentrated in (i.e., explained by) one half?
- **H-014 (Size × Momentum)**: Does the Size premium exist independently
  within BOTH a high-momentum half and a low-momentum half?
- **H-015 (Size × Volatility)**: Does the Size premium exist independently
  within BOTH a high-volatility half and a low-volatility half?

## 2. Null and alternative hypotheses (per interaction)

- **H0 (null, for each)**: The Size tilt's excess return over its own
  bucket-scoped benchmark is statistically indistinguishable from zero in
  at least one of the two buckets, OR the two buckets' excess returns
  differ so much that the "Size premium" is better described as
  concentrated in one bucket than as a general size effect.
- **H1 (alternative, for each)**: The Size tilt produces a statistically
  and economically similar positive excess return in BOTH buckets,
  supporting that the premium is attributable to size itself, independent
  of the interacting characteristic.

## 3. Data availability audit (before any design was finalized)

All three interacting dimensions use data and scoring logic already
computed and validated on this platform, at full IRU breadth — no new
external data:
- **Size**: `size_scores()` (existing, H-011's own scoring, unmodified).
- **Momentum**: `rank_scores()` (existing, H-007/H-009/H-010's own
  scoring, unmodified).
- **Volatility**: `vol_scores()` (existing, H-008/H-012's own scoring,
  unmodified).
- **Liquidity**: NOT previously coded as a scoring function (only the
  underlying data — `panel["adtv60"]`, already computed by `load_panel()`
  for capacity reporting — existed). A new `liquidity_scores()` function
  is added, additive only, reusing this already-loaded field; no new data
  source (confirmed against `docs/FACTOR_CANDIDATE_REGISTRY.md`'s own
  finding that Liquidity data is "Available now, zero new data required").

## 4. Method

**Double sort, not a regression.** This platform's engine is a
sort-and-simulate backtester, not a cross-sectional regression/factor-model
engine; introducing a whole new regression framework to "control for" the
interacting factor would itself be new, unvalidated methodology. A
double sort is the standard alternative for exactly this question in the
academic literature (Fama & French's own size×value double-sort
methodology, 1993) and reuses the platform's existing, validated
sort-and-simulate machinery unchanged.

For each interaction, at each formation date (shared calendar across both
dimensions — same rebalance frequency):
1. Compute Size scores and the interacting factor's scores (existing
   functions, unmodified).
2. Restrict to tickers scored by both dimensions that date.
3. Median-split into "High-X" and "Low-X" buckets by the interacting
   factor's own z-score.
4. Within EACH bucket separately, select the same top_n (by Size score)
   that H-011 itself uses, proportionally scaled to the bucket's smaller
   membership (H-011: top 20 of ~100 IRU names, 20%; here: top_n scaled to
   ~20% of a ~50-name bucket, see Section 6).
5. Benchmark EACH bucket's tilt against an equal-weight benchmark of ALL
   members of THAT SAME BUCKET (not the whole-universe EW-IRU benchmark)
   — this isolates whether being small adds anything BEYOND simply
   belonging to that liquidity/momentum/volatility half, rather than
   conflating a bucket-level tilt with the size effect itself.

## 5. Confirmation / partial-explanation / rejection criteria

For each interaction, compare the two buckets' Size-tilt excess returns
(vs. their own bucket benchmarks):

- **"Independent" (H1 supported)**: both buckets show net excess return in
  the same direction as H-011's own confirmed result, both economically
  material (not one large and one negligible), and neither bucket's
  placebo p-value is > 0.05 while the other is comfortably significant
  (i.e., no stark significance asymmetry between buckets).
- **"Partially explained"**: one bucket's excess return is materially
  larger/more significant than the other, but both remain directionally
  positive and neither placebo-fails outright — the premium is real in
  both but concentrated.
- **"Explained away"**: one bucket shows a real, placebo-passing positive
  excess return while the other is flat, negative, or placebo-fails
  outright — the "size premium" is better described as a premium
  specific to that bucket (e.g., illiquid-small, not small per se).

## 6. Statistical methods applied (per the owner's explicit requirement) and one disclosed scoping reduction

Applied to every bucket-config:
- **Look-ahead controls**: inherited from the existing engine (PIT
  eligibility, formation-date-only scoring) — no new look-ahead risk is
  introduced, since size_scores/rank_scores/vol_scores/liquidity_scores
  are each either unmodified or (liquidity) built on the same PIT-safe
  panel construction.
- **Placebo testing**: YES, 100 iterations per bucket-config, same
  persistence-preserving ticker-relabeling convention as every other
  xs_* method — but applied JOINTLY to both the Size and interacting-
  factor score series under one shared permutation per iteration (so a
  shuffled ticker's real, persistent size-AND-liquidity/momentum/vol
  relationship travels together, not independently).
- **HAC (Newey-West) inference**: YES, applied to each bucket's daily
  excess-over-bucket-benchmark return series (`stats.newey_west_tstat`,
  reused unchanged).
- **Deflated Sharpe Ratio**: applied as a SUPPLEMENTARY diagnostic only
  — each bucket's daily excess Sharpe is reported alongside the EXISTING
  10-hypothesis real-rf trial-pool distribution (from
  `docs/METH-001b_DSR_CONSISTENCY_RECONCILIATION_2026-08-02.md`), to show
  where it would rank, but **H-013/H-014/H-015 do NOT add new slots to
  the DSR trial-count** — these are diagnostic sub-analyses of an
  already-counted trial (H-011), not new independent looks at the data
  in the sense the trial count is meant to capture. This is stated
  explicitly rather than silently decided either way.
- **Multiple-testing discipline**: Holm/Benjamini-Hochberg applied across
  each interaction's own small stability grid (4 cells, see below),
  exactly as every other hypothesis's grid is corrected.

**One disclosed scoping reduction, not a silent shortcut**: this
investigation does NOT re-run a fresh walk-forward/untouched-OOS split for
each bucket. Rejected alternative: replicate H-011's full 3-regime
walk-forward (pre_float / float_shock / oos_2025_26) for all 6
bucket-configs. Rejected because (a) this is explicitly a diagnostic
decomposition of an ALREADY out-of-sample-validated hypothesis (H-011
already cleared its own untouched OOS window on the unconditional
universe), not a new confirmation bid that itself requires a fresh OOS
guarantee; (b) it would roughly double the compute for a marginal gain in
rigor given (a); (c) the stability grid + placebo + HAC + DSR-context
battery already applied is a real, substantial statistical treatment, not
a shortcut past validation entirely. All bucket-configs still run only on
H-011's own `development`-stage window (2016-01-02 to 2024-12-31),
**never touching the 2025-01-02+ OOS data H-011's own holdout reserves.**

**Stability grid, scaled down from H-011's 6 cells to 4, disclosed**:
`top_n = [8, 12]` × `rebalance = [quarterly, semiannual]` (vs. H-011's
`top_n = [15, 20, 30]` × 2 rebalance frequencies), proportional to each
bucket's roughly half-sized membership (~50 names vs. H-011's ~100), not
a reduction in per-cell rigor.

## 7. Benchmarking (mandatory, per the standing directive)

**Frontier Market Assessment** — *Adoption*: double-sort robustness checks
for a confirmed factor are not, to this audit's knowledge, commonly
published for NGX or African frontier markets specifically — stated as
absence of evidence in this review, not absence in the wider practice.
*Practicality*: high, since all required scores already exist at full
breadth. *Strengths*: directly interrogates the platform's single
highest-value existing result. *Weaknesses*: a ~50-name half-universe
bucket is a real breadth reduction from an already-thin 100-name IRU —
statistical power within each bucket is necessarily lower than H-011's
own unconditional test, an inherent, disclosed limitation of any double
sort on a small universe.

**Emerging Market Assessment** — *Adoption*: double-sorting to separate a
size effect from a correlated liquidity effect is standard practice in
broader EM factor research (implicit in most EM factor papers' choice to
report liquidity-adjusted or liquidity-controlled size premia). *Academic
support*: Amihud & Mendelson (1986) directly motivates the size-liquidity
correlation concern this investigation tests. *Known failures*: none
specific to this exact application; not verified against any specific
published EM study.

**Developed Market Assessment** — *Institutional usage*: double sorting
(2x2, 2x3, or finer) is the standard, textbook technique for isolating
whether one characteristic's premium survives controlling for another —
Fama & French (1993) itself is built on exactly this technique for
size×value. *Evidence quality*: strong, well-established methodology.
*Implementation complexity*: moderate — median-split bucketing and a
bucket-scoped benchmark are the only new mechanics; all scoring logic is
reused unchanged.

**Statistical Robustness** — HAC/Newey-West: applied (Section 6).
Multiple-hypothesis correction: applied within each interaction's grid;
explicitly NOT added to the cross-hypothesis DSR trial count (Section 6,
stated reasoning). Deflated Sharpe Ratio: applied as context, not a new
confirmation bar. Sample independence: the SAME joint-permutation placebo
design used elsewhere addresses ticker-identity independence; the
inherent reduction in bucket breadth (breadth ceiling, Grinold's
Fundamental Law) is a disclosed, not resolved, limitation. Survivorship
bias: not addressed by this investigation (a standing, separately-tracked
open item). Look-ahead bias: addressed by construction (Section 6).
Data snooping: mitigated by pre-registering the confirmation/partial/
rejection criteria (Section 5) before any bucket is run.

## 8. Rejected alternatives (explicit)

- **A cross-sectional Fama-MacBeth-style regression controlling for both
  characteristics simultaneously.** Rejected: would require building an
  entirely new regression-based inference layer this platform does not
  have, a much larger and separately-riskier undertaking than reusing the
  existing sort-and-simulate engine; a double sort answers the same
  economic question with the platform's own already-validated machinery.
- **Terciles or finer (3x3) sort instead of a median 2-way split.**
  Rejected for this investigation: a 100-name IRU split into thirds and
  then by size again would leave sub-buckets with single-digit
  membership counts at points in the sample, an unacceptably thin
  breadth for the platform's own established minimum-eligibility
  conventions (`min_obs_formation`, `len(elig) < 10` guards already
  present throughout `backtest_xs.py`). A 2-way split is the finest cut
  this universe can support with real breadth in each cell.
- **Re-running H-011's full walk-forward/OOS split per bucket.** Rejected,
  reasoning in Section 6.
- **Silently treating Liquidity/Momentum/Volatility as newly-confirmed
  standalone factors if their bucket shows a strong effect.** Rejected —
  explicitly out of scope; a real standalone factor claim for any of
  these would need its own full pre-registration and OOS validation,
  not be inferred from a forensic sub-analysis of H-011.

## 9. Ledger treatment

H-013, H-014, H-015 are registered in `data/registry.sqlite` for
permanent, reproducible recording — their `description`/`motivation`
fields state explicitly that these are diagnostic decompositions of
H-011, not standalone factor claims. Their resolution (`confirmed` /
`rejected`) reflects the NARROW claim in Section 1 (does the Size premium
survive this specific double sort), never a claim about Liquidity,
Momentum, or Volatility as independent factors. H-011's own `confirmed`
status and ledger entry are not modified by this investigation regardless
of outcome — a forensic finding here is new, additional evidence layered
onto H-011's record (in `FACTOR_REGISTRY.md`), not a retroactive edit to
what was already decided under H-011's own, different, pre-registered
criteria.
