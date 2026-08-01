# FRE-5 — CompanyThesis Folding: Pre-registration

*Pre-registration only. No implementation, no code, no experiment run. Per
`docs/fre/12_research_roadmap.md`'s own review checkpoint for this phase
("Owner reviews the pre-registration BEFORE this phase runs, then the
results separately"), this document stops here and awaits approval before
anything is built — the same two-gate discipline the LIM research program
has used for every training experiment (`rb3a_phase2_preregistration.md`,
`rb3c_experimental_design.md`).*

## Original design (as frozen in Part 12)

Implement Part 7's `CompanyThesis` append-only folding, with the fold
-weight parameter as the one independent variable, held against a frozen
naive baseline ("always show the most recent delta only"). Success
criterion: the longitudinal-consistency metric (Part 11) improves versus
the naive baseline with no more than a stated staleness-lag regression,
evaluated via a proper single-variable comparison.

## Real-data feasibility check — performed before writing anything further

**Finding: the real dataset cannot support this experiment as originally
scoped.** All 18 real `investment_implications` rows were grouped by
ticker. Exactly one ticker has a real, multi-point history spanning
meaningful time: **TOTAL** — 4 implications, 2016-07-29 through
2022-10-27, directions `bullish, bullish, bullish, neutral` (one genuine
direction change, in the final transition). CILEASING has 3 points
(2019/2025/2026) but **zero** real direction changes (`neutral` all
three times; only `confidence` moves, 0.0→0.0→0.3). MOFIREIF has 2 points
but they share the **same filing date** (2026-03-02, two different fund
series filed together) — not a temporal sequence at all.

**A "fold-weight sweep, compared against a naive baseline, evaluated via a
longitudinal-consistency metric" requires enough independent multi-point
sequences to compare — this platform has effectively N=1 usable case
(TOTAL) and N=1 weaker secondary case (CILEASING, no real direction
change to test stability against).** Running a parameter comparison on
this little data would not produce a statistically meaningful result; it
would produce a number that looks like an experiment but tests nothing —
exactly the trap this program's own Part 11 (Evaluation Framework)
explicitly warns against ("small-sample instability... report sample
sizes and confidence intervals alongside every number, never a bare point
estimate") and that the LIM research program has hit before (e.g., "the
held-out set (n=12 at the time) was too small for strong conclusions,"
`lim1_results` era finding).

## Recommended scope adjustment (this is the actual ask for approval)

Rather than force a statistically unjustifiable fold-weight comparison,
this pre-registration proposes **narrowing FRE-5 to a mechanism pilot, not
a parameter-tuning experiment**:

1. Implement `CompanyThesis`/the folding mechanism itself, using **one
   single, disclosed, non-tuned default** (equal-weight accumulation: each
   new delta is folded in with the same fixed weight, no parameter sweep)
   — not because this is expected to be optimal, but because with N=1
   real testable ticker there is no evidence basis to prefer any specific
   weight over any other. Picking one and disclosing it as arbitrary is
   more honest than dressing up a sweep with false statistical rigor.
2. Run this single mechanism against the two real cases that exist (TOTAL,
   CILEASING) and report, in full, exactly what the folded thesis looks
   like at each of TOTAL's 4 real time points — a worked case study, not a
   validated result.
3. **Explicitly do NOT claim** the fold-weight was validated, tuned, or
   shown to beat any baseline. The deliverable is "the mechanism runs
   correctly and produces a defensible, evidence-traceable thesis
   sequence on real data," not "we found the best fold-weight."
4. **Explicitly recommend** that the original fold-weight-comparison
   experiment (as Part 12 designed it) be deferred until enough real,
   independent, multi-point per-ticker sequences exist to support it —
   named as a concrete, re-triggerable condition (e.g., ≥5 tickers each
   with ≥3 real implications spanning meaningfully different dates), not
   an indefinite postponement.

## Pre-registered success criteria (for the adjusted scope)

Set **before** implementation, per the standing discipline:

- The folding mechanism must run against TOTAL's real 4-point sequence
  and CILEASING's real 3-point sequence without error, producing one
  `CompanyThesis` snapshot per time point, each citing its own
  `source_implication_ids` (append-only, per Part 7's design — never a
  silent overwrite of prior narrative).
- Every snapshot's `bull_case`/`bear_case`/`base_case`/`confidence` must
  be traceable back to the specific `investment_implications` row(s) that
  produced it (the same evidence-traceability bar every other FRE module
  has met).
- The one real direction change in the dataset (TOTAL's final
  bullish→neutral transition) must be reflected in the folded thesis's
  history in a way a reviewer can audit — i.e., the mechanism must not
  silently smooth over or discard the change.
- No claim of statistical validation, fold-weight optimality, or
  generalizability beyond these two worked cases will be made in the
  results report.

## What this pass will NOT do

- No fold-weight parameter sweep.
- No longitudinal-consistency metric computed as a validated score (Part
  11 already names this metric as needing real snapshot volume this
  dataset doesn't yet have — computing it on N=1-2 cases would produce
  the same false-precision problem this program has refused elsewhere).
- No modification to any AI Intelligence Layer file, schema, or existing
  FRE module (`evidence_graph.py`, `company_memory.py`,
  `reaction_check.py` are all independent of this work).

## Stop condition

If the folding mechanism cannot be implemented as a genuinely read-mostly,
evidence-traceable, append-only object on this real data (e.g., if
`CompanyThesis` cannot be built without inventing ungrounded content),
stop and report that honestly rather than shipping a mechanism that
produces plausible-looking but unevidenced narrative text.

## Dependencies

FRE-3's `company_memory.py` (for the real per-ticker implication
sequence), `docs/fre/07_investment_thesis_engine.md` (the design this
implements, narrowed as above), `docs/fre/11_evaluation_framework.md`
(the longitudinal-consistency metric, explicitly deferred, not computed
this pass).

---

*Awaiting approval of this pre-registration — including the scope
narrowing from a fold-weight experiment to a mechanism pilot — before any
implementation begins.*
