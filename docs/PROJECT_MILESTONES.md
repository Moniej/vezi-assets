# Fund Alpha / NGX Research Platform — Project Milestones

*Compiled 2026-08-02, at v1.0 (tags `platform-baseline-2026-08-02-stable`
/ `v1.0`). Covers the complete project history, not just the FRE/FSI
track — from the original sector-rotation backtester through the AI
Intelligence Layer, the Financial Reasoning Engine, and this platform's
first versioned release.*

---

## The arc, in one paragraph

What began as a research-grade NGX sector-rotation backtester grew,
through a deliberate, disclosed, hypothesis-by-hypothesis process,
into an institutional-grade equity research platform: a validated
quant factor, a full document-intelligence pipeline with a mandatory
adversarial self-critique gate, a 27-phase financial-statement
reasoning engine, and a complete portfolio-research toolkit — all
built without ever inventing an unvalidated signal, fabricating a
data point, or quietly crossing a guardrail. Every negative result
along the way was kept, not discarded, because a rejected hypothesis
is itself evidence.

---

## Milestone 1 — Quant Engine: the first hypothesis cycle (2026-07-15)

- **H-001 (NGX price momentum) rigorously tested and REJECTED** on
  real data, both pre-registered variants: placebo p=0.55 (real
  Sharpe below the shuffled-label mean), 0/20 cells surviving Holm/BH
  correction, 111 total experiments. Frozen with SQL triggers blocking
  any status change or new experiment under H-001 — no unfreeze
  mechanism exists.
- **H-011 (Size) reaches `confirmed`** (2026-07-22) — the platform's
  **first and, as of this writing, only validated factor**. This one
  event is the trigger for almost everything that follows: it is the
  Year-1 exit condition that unlocks the Company Intelligence Engine,
  and it remains the one factor Portfolio Construction's own ≥2-factor
  gate is still one short of.
- **Six more hypotheses tested and honestly rejected** (H-004 oil
  lead-lag, H-005 MPC windows, H-006 PEAD, H-007/H-009/H-010 momentum
  variants, H-008 low-volatility — the last one a *statistically
  robust negative* tilt, not merely an absent effect). Every rejection
  is recorded in `docs/FACTOR_REGISTRY.md`, cited as evidence
  throughout the platform rather than quietly discarded.

## Milestone 2 — AI Intelligence Layer built from scratch (2026-07-22)

- A one-day mega-charter escalation recast the assistant's mandate
  from "build a backtester" to "build an institutional AI equity
  research platform" — twelve named modules, multi-exchange ambition,
  and (the two genuinely new pieces) a **Document Intelligence
  module** and **exchange-independence as a first-class design
  requirement**.
- **Phase A**: 11,533 real documents processed into a structured
  `documents` table (7,399 native-text, 4,134 correctly flagged as
  not-yet-OCR'd, 0 errors).
- **Phase B**: 143 deterministic corporate-action facts extracted
  (dividends, rights issues, bonus issues), with full evidence
  provenance.
- **Phase C**: the complete 14-step reasoning pipeline built —
  identify → extract → recursive "why" → 14 fixed impact categories →
  duration/magnitude buckets → confidence with mandatory uncertainty
  rationale → full causal chain → bull/bear/base case → action
  classification → cross-reference against history → a **mandatory
  adversarial self-critique gate** (8 fixed questions, each paired
  with an independent mechanical check, not just a model's own
  self-report) → structured, versioned output. **32/32 engineering-
  correctness tests passed** before a single real document was ever
  analyzed with a live model.
- **Provider swapped Anthropic → Gemini** the same day, with zero
  changes needed to the reasoning pipeline itself — confirmed
  provider-agnostic by construction, not by luck.

## Milestone 3 — Company Intelligence Engine unlocked (2026-07-22)

H-011's confirmation triggered the one condition the platform's own
3-year roadmap named for this: `CompanyProfile` v0 scaffolding built,
carrying every field the platform's long-term vision wants — but each
one populated **only** from evidence that actually exists, with an
explicit, disclosed reason for every field that doesn't (never a
fabricated value).

## Milestone 4 — FRE: a 15-part architecture, designed then built (2026-08-01)

- The Financial Reasoning Engine's full 15-part design frozen as the
  architectural reference (`fre-architecture-baseline-2026-08-01`) —
  ten reasoning modes, a portfolio-reasoning tier system, a valuation
  engine architecture, a full research roadmap, gap analysis, and risk
  assessment.
- **FRE-2 through FRE-6 built**, individually owner-gated: Evidence
  Graph, Company Memory, a deterministic market-reaction cross-check,
  a Company Thesis engine (permanently barred from ever outputting a
  numeric expected return), and the Valuation Engine's own
  architecture (six method adapters, scaffolded and readiness-gated,
  `compute()` refusing unconditionally from day one).

## Milestone 5 — FSI: building the dataset that didn't exist yet (Phases 1-13, 2026-08-01/02)

A roadmap review found the financial-statements dataset the original
plan assumed simply didn't exist — so the platform built it, by hand,
from real filings, rather than assume or fabricate it:

- **137 real financial-statement facts** hand-extracted and
  cross-verified across **10 real NGX tickers** (revenue, net profit,
  balance sheet, cash flow, EBITDA, EBIT) — native-text-only, no OCR,
  no vendor data, ≥80% hand-verification bar held throughout.
- **267 mechanically-derived reasoning conclusions** (ratios, trend
  classifications, rule-based health flags) — every one traceable back
  to its own source fact.
- A **point-in-time memory layer** with a mechanical 30-point
  look-ahead audit finding **0 violations**.
- A **regression harness** that proved itself by successfully
  detecting 3/3 real historical defects re-injected via scratch-copy
  testing — not a rubber stamp.
- A **complete institutional research dossier** and the platform's
  **first operational CLI**.
- **Coverage expansion from 5 to 10 tickers**, with the entire
  9-module composition chain re-run against the expanded dataset with
  **zero code modification** and confirmed to generalize.

## Milestone 6 — The continuous-execution era: Part 9 built in full (Phases 14-25)

The owner temporarily lifted the per-phase approval checkpoint,
authorizing a self-directed pre-register → implement → validate →
document → commit/tag → auto-continue cycle — every phase still ran
the full lifecycle, only the human pause between phases was removed.

- **All five of Part 9's Tier-1 portfolio-research capabilities
  built, tested, and made CLI-operable**: Screening, Portfolio-Memory
  Cross-Reference, Watchlist Persistence (the platform's first new
  table since Phase 3, and its first write-capable operator tool),
  Qualitative Correlation Notes, and Sector-Coverage View — the last
  one only possible after Milestone 7 below.
- **A real regression caught and fixed by the platform's own
  discipline**: six dedicated test files had silently stopped covering
  five newly-added tickers; found, fixed, and the harness itself
  strengthened so it can't happen silently again.
- **A documentation error found in the platform's own prior work and
  corrected transparently**: two earlier phases had understated Part
  9's own Tier-1 capability count.

## Milestone 7 — The sector-data unlock: a wrong assumption found and fixed (Phase 23)

The platform's own architecture document had assumed, for over ten
phases' worth of audits, that NGX sector data would be a "free side
effect" of processing filings already on hand. **Nobody had actually
checked.** When the owner pushed back on an early stopping point, this
assumption was tested directly against a real filing — and found
false. The real source (NGX's own official "Daily Official List")
was located, verified as authoritative, and used — with full retrieval
provenance recorded for every one of the **136 real securities**
populated. This single correction:

- Resolved the single most-cited blocker in the platform's entire
  history.
- Unblocked Sector-Coverage View, closing Part 9 in full.
- Fed two more real subsystems (Phases 26-27): the Valuation Engine's
  own company-type classification, and Company Intelligence's Industry
  Exposure field — both wired deterministically, both verified,
  before and after, to activate zero new analytical or valuation
  output.

## Milestone 8 — v1.0: the platform's first versioned release (2026-08-02)

Three successive, honest stopping points were reached and re-verified
— each time because no further phase satisfied *all* of "closes a real
gap," "buildable internally today," and "does not violate a
guardrail." The third was accepted as the platform's architecturally
complete state within current constraints. Closed out with:

- A **consolidated architecture document** describing the complete
  system in one place.
- A **dependency map** (with a rendered diagram) showing every
  subsystem's real relationships.
- A **complete implementation timeline**, every phase, every tag,
  every disclosed defect.
- An **Owner Decision Backlog** — every remaining capability, mapped
  to the exact external input needed to unlock it.
- A **dependency-ordered expansion roadmap** — sequenced by what
  unlocks what, not by guessed value.
- One final, full regression pass, and the tag **v1.0**.

---

## By the numbers

| Metric | Count |
|---|---|
| Git tags (phase baselines + architecture milestones) | 41 |
| FSI phases completed | 27 |
| Real financial-statement facts extracted, hand-verified | 137 |
| Mechanically-derived reasoning conclusions | 267 |
| Real NGX tickers with extracted financial-statement facts | 10 |
| Real securities with NGX-official sector classification | 136 of 320 |
| Database tables (all additive, none ever dropped/renamed) | 31 |
| Dedicated regression test files | 38 |
| Individual mechanical assertions across the regression suite | 511+ |
| Real documents processed into the evidence base | 11,533 |
| Quant-engine hypotheses tested (1 confirmed, 7 rejected, honestly) | 8 |
| Git commits across the project | 112+ |

## What was never done, by design, and remains true at v1.0

- No unvalidated signal has ever been treated as predictive.
- No valuation number has ever been computed or fabricated —
  `compute()` still unconditionally refuses on every adapter.
- No hidden score, rank, or weight exists in any FRE/FSI module —
  mechanically checked, not just documented, in every phase.
- No data point has ever been guessed when it could instead be left
  `NULL` and disclosed.
- Every negative result — a rejected hypothesis, a wrong assumption,
  a test-coverage regression — was found, disclosed, and fixed in the
  open, never hidden or quietly patched over.

---

*Next milestone begins when a trigger named in
`docs/fre_runs/OWNER_DECISION_BACKLOG_2026-08-02.md` actually occurs —
see `docs/fre_runs/FUTURE_EXPANSION_ROADMAP_2026-08-02.md` for what
each one would unlock.*
