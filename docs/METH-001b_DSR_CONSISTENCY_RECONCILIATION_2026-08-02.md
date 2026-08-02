# METH-001b — Recomputing DSR on a Real-Risk-Free Basis: A Reconciliation, Not a Replacement

*2026-08-02. Follow-up to the "next research step" both `METH-001_STATISTICAL
_HARDENING_REPORT_2026-08-02.md` and `METH-002_RISK_FREE_RATE_REPORT_2026-08-02
.md` named but did not perform: recompute the Deflated Sharpe Ratio using
real-risk-free-rate daily excess returns (METH-002) instead of the original
benchmark-excess daily returns (METH-001), for a "consistent definition of
risk-adjusted return." This was done in full — but the result requires
careful interpretation, not a straight swap of one number for another, and
this document exists specifically to prevent the friendlier of two answers
from quietly becoming the new headline without explaining why they differ.*

## What was recomputed

`scripts/compute_dsr_realrf_evidence.py` reran every resolved hypothesis's
frozen final-evaluation config read-only (same pattern as METH-001/METH-002's
own evidence scripts), computed each one's **daily excess return over the
real, point-in-time CBN MPR-implied daily rate** (rather than over the
EW-IRU benchmark), and fed those into the *same, unmodified*
`stats.deflated_sharpe_ratio()` from METH-001 — no new statistical code,
no change to the DSR formula itself, only a different input series.
H-006 was excluded from the trial pool entirely (not filled with any
value): its window starts 14 days before verified MPR coverage begins,
so no real-risk-free daily excess series can be honestly computed for it.

## The two results, side by side

| Basis | N | Trial-pool Sharpes range | sr_star (chance benchmark) | H-011's DSR |
|---|---|---|---:|---:|
| **Benchmark-excess** (METH-001, original) | 11 | -0.169 to +0.056 | 0.107 | **0.0071** |
| **Real-risk-free-excess** (this document) | 10 (H-006 excluded) | -0.116 to +0.077 | 0.083 | **0.396** |
| Benchmark-excess, cross-sectional-only peers | 7 | — | 0.080 | 0.130 |
| Real-rf-excess, cross-sectional-only peers | 6 | — | 0.041 | **0.964** |

These are dramatically different answers to what looks like "the same
question, just corrected for a better risk-free assumption." It is not
the same question, and the difference is real, economically meaningful,
and explained below — not an artifact of rounding or a coding error (the
DSR function itself was not touched; only its input changed).

## Why they differ: two different things are being measured

Per-hypothesis daily Sharpe under each basis:

| Hypothesis | Benchmark-excess daily SR | Real-rf-excess daily SR |
|---|---:|---:|
| H-001 | -0.0032 | **+0.0474** |
| H-003 | -0.0016 | **+0.0042** |
| H-004 | +0.0223 | +0.0262 |
| H-005 | -0.1691 | -0.1159 |
| H-006 | -0.0941 | excluded |
| H-007 | -0.0215 | **+0.0230** |
| H-008 | -0.0706 | **-0.0062** |
| H-009 | +0.0165 | +0.0446 |
| H-010 | +0.0173 | +0.0459 |
| H-011 | +0.0564 | +0.0774 |
| H-012 | -0.0780 | **+0.0008** |

**8 of 10 hypotheses flip from negative-or-near-zero to positive** when
measured against cash instead of the benchmark. This is exactly the
signature of **general long-only equity market exposure (beta), not
factor-specific skill**: over this sample window, NGX equities broadly
outperformed cash (the real average MPR was ~15%, but nominal equity
returns — including in strategies with no real factor edge — were higher
still in several regimes, e.g. the float-shock/OOS periods). A strategy
that is simply "long a basket of NGX names" will tend to beat cash in such
a period **regardless of whether its specific stock-selection tilt (size,
value, momentum, whatever) adds any value over the passive benchmark** —
because the passive benchmark itself was also beating cash. Measuring
Sharpe against cash therefore **conflates two separate claims**: "this
basket of stocks went up" (true of nearly everything long-only in this
window) and "this specific factor tilt beats simply holding the market"
(the actual research question every hypothesis in this program has always
been pre-registered to test, per every existing prereg's benchmark
specification: "vs the EW-IRU benchmark," never "vs cash").

Benchmark-excess Sharpe removes the shared market-beta component by
construction (both the strategy and the benchmark were exposed to the
same rising/falling NGX market); real-risk-free Sharpe does not. This is
not a novel critique — it is the standard reason active-management
research reports an Information Ratio (excess over a benchmark) rather
than a Sharpe Ratio (excess over cash) when the object of study is a
*tilt* within an asset class, not a decision about *whether to hold the
asset class at all*. Bailey & López de Prado's DSR framework was
originally specified for the classic cash-relative Sharpe Ratio; applying
it to the benchmark-relative form (as METH-001 first did) is a considered,
purpose-driven adaptation to this platform's actual research question, not
a deviation from correct practice.

## Recommendation: do not replace, use both, know which answers which question

- **Benchmark-excess DSR remains the primary, decision-relevant metric for
  factor confirmation.** It answers the platform's actual pre-registered
  research question for every hypothesis: does this specific tilt beat
  the passive alternative, adjusted for having tried 11 ideas against the
  same data? H-011's benchmark-excess DSR (0.0071 / 0.130 depending on
  trial pool) **stands, unchanged, as the platform's honest program-wide
  confidence read on its only confirmed factor.**
- **Real-risk-free DSR (0.396 / 0.964) is retained as a separate, disclosed
  diagnostic**, answering a different, also-legitimate question: "does
  this strategy also clear a cash hurdle, adjusted for trials?" This is
  relevant context (e.g., for an absolute-return / capital-allocation
  framing) but **must not be read as strengthening H-011's factor-specific
  validation** — doing so would silently substitute a more flattering
  number for a less flattering one without the underlying economic
  question actually having changed, which is precisely the kind of
  quiet-confidence-inflation this platform's guardrails exist to prevent.
- Going forward, any report citing "H-011's DSR" without qualifying which
  basis is meant is incomplete; both should be stated together, as in the
  table above, with the benchmark-excess figure identified as primary.

## What this changes and does not change

- No hypothesis's ledger status changes.
- `FACTOR_REGISTRY.md`'s H-011 entry is updated to present both DSR bases
  side by side with this same recommendation, not to elevate the
  real-rf figure.
- No new statistical code was added — this reused `stats
  .deflated_sharpe_ratio()` exactly as validated in METH-001; the only
  new artifact is `scripts/compute_dsr_realrf_evidence.py` (a read-only
  evidence-generation script, same pattern as its METH-001/METH-002
  predecessors) and `experiments/dsr_realrf_evidence_2026-08-02.json`.
- No registry writes.

## Honest self-assessment of this exercise

The user's requested consistency fix was performed faithfully and
completely — every number above is real, reproducible, and derived from
the same validated DSR formula. But "consistency" in *inputs* surfaced a
real *conceptual* inconsistency risk: two legitimate Sharpe definitions
answer different economic questions, and simply picking the newer
computation because it was requested most recently would have been a
subtle but real violation of "never fabricate confidence" — not because
either number is wrong, but because presenting the friendlier one alone,
without this reconciliation, would have implied H-011's factor-specific
case had strengthened when what actually happened is that a different,
market-beta-contaminated question was asked instead.
