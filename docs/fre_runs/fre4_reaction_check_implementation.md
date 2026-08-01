# FRE-4 — Cross-Document Reaction Check Implementation

*Implementation report. Builds on `fre-architecture-baseline-2026-08-01`,
`fre3-company-memory-baseline-2026-08-01`, and FRE-2's Evidence Graph
(`f7dd990`). Additive only — no schema change, no modification to any AI
Intelligence Layer pipeline file or data.*

## Scope

This pass carried no new pipeline spec from the owner ("proceed... per the
approved FRE roadmap"), so it follows `docs/fre/12_research_roadmap.md`'s
own **FRE-4: cross-document reaction-check module**
(`docs/fre/06_cross_document_reasoning.md`, Mechanism 2) exactly as
designed.

## Objective

Build a deterministic, non-LLM cross-check comparing a fact's own
qualitative `direction` verdict against realized price movement, reusing
the existing, validated PIT price panel (`equity_prices`) — never a new
inference.

## A real finding that changed this module's scope, twice

**Finding 1 — `market_reaction_assessment` is already populated.** Before
writing any code, `investment_implications.market_reaction_assessment`/
`.market_reaction_reasoning` were inspected directly (the same "verify
before designing" discipline as every prior FRE pass). Part 6's design
assumed these columns were unset; they are not. **All 18 real
implications already carry a value — 17 `fairly_priced`, 1 `unclear` —
each with a genuinely distinct, clearly LLM-generated reasoning string**
(*"Standard annual dividend proposal... typically anticipated and priced
into equity markets," "Routine dividend announcement consistent with
standard yearly corporate calendar expectations"*). This is not a
hardcoded default; it is the existing AI Intelligence Layer already
answering this question — by LLM speculation, not by reading a single
real price. This is exactly the failure mode Part 6's design warned about
in the abstract, now **confirmed concretely**. The near-uniform
`fairly_priced` verdict (17/18) is a plausibly mode-collapsed pattern,
similar in shape (though not independently proven identical in cause) to
LIM's own RB-3b finding.

**Design consequence**: this module does **not** overwrite
`market_reaction_assessment`/`market_reaction_reasoning` — doing so would
modify AI Intelligence Layer data with no documented blocker requiring it,
and would erase real experiment history. `reaction_check()` computes an
**independent** deterministic verdict and returns it *alongside* the
existing value, for comparison only — verified never to write anything
(see below).

**Finding 2 — the four-way `market_reaction_assessment` vocabulary cannot
be reproduced deterministically without inventing a threshold this
platform has explicitly refused to invent.** Distinguishing "overreacting"
from "fairly priced" requires mapping a qualitative `magnitude` bucket to
an expected numeric return range — exactly what
`docs/REASONING_ENGINE_SPECIFICATION.md` §6 refuses to do ("no numeric
mapping is pre-defined... that would be inventing a threshold with no
evidence behind it"). This module therefore answers a narrower, defensible
question instead: **does the sign of the realized return agree with the
fact's own `direction`** ('bullish'/'bearish'/'neutral'/'unknown')? Output
is a new, explicitly separate vocabulary —
`direction_confirmed`/`direction_contradicted`/`inconclusive`/
`not_applicable` — never conflated with `market_reaction_assessment`'s own
enum.

## What was built

| Artifact | Role |
|---|---|
| `src/ngxrot/fre/reaction_check.py` | `reaction_check(con, implication_id, window_trading_days=5) -> ReactionCheckResult` |
| `scripts/fre/test_reaction_check.py` | 16 assertion checks against the real database (no write path exists, no scratch copy needed) |

**Mechanics, disclosed in full**: anchor date = `documents.filing_date`
(`event_date` is confirmed 0/11,533 populated — a disclosed substitution,
not a design choice made lightly). Before-price = the most recent
`equity_prices` close at or before the anchor date; after-price = the
close `window_trading_days` (default 5) **trading rows** later — counted
by available rows, not calendar days, since real gaps of a month or more
exist for thinly-traded instruments (MOFIREIF). A `±1%` deadband
(disclosed heuristic, not validated) treats a small return as "flat," not
a real directional move. A `deals < 10` floor (same disclosure) flags thin
liquidity informationally — it does not suppress the computed return.

## Pilot result — all 18 real implications (the complete real dataset, not a synthetic sample)

| impl | ticker | direction | realized return | direction_check | thin liquidity | ex-div confound | existing LLM verdict |
|---|---|---|---|---|---|---|---|
| 1 | GTCO | bullish | −1.32% | **direction_contradicted** | No | No | fairly_priced |
| 2 | REDSTAREX | neutral | +0.82% | not_applicable | No | Yes | fairly_priced |
| 3 | TOTAL | bullish | +33.34% | direction_confirmed | No | Yes | fairly_priced |
| 4 | CILEASING | neutral | −10.23% | not_applicable | No | Yes | fairly_priced |
| 5 | TOTAL | bullish | +9.96% | direction_confirmed | No | Yes | fairly_priced |
| 6 | TOTAL | bullish | +0.00% | inconclusive | No | Yes | fairly_priced |
| 7 | TOTAL | neutral | +0.00% | not_applicable | No | Yes | fairly_priced |
| 8 | UCAP | bullish | +0.34% | inconclusive | No | Yes | unclear |
| 9 | BUAFOODS | neutral | +11.76% | not_applicable | No | Yes | fairly_priced |
| 10 | NASCON | bullish | +1.42% | direction_confirmed | No | Yes | fairly_priced |
| 11 | LIVINGTRUST | neutral | +0.00% | not_applicable | **Yes** | Yes | fairly_priced |
| 12 | STANBICETF30 | neutral | −5.00% | not_applicable | **Yes** | Yes | fairly_priced |
| 13 | UNILEVER | bullish | +0.00% | inconclusive | No | Yes | fairly_priced |
| 14 | CILEASING | neutral | +44.04% | not_applicable | No | Yes | fairly_priced |
| 15 | NGXGROUP | bullish | +0.98% | inconclusive | No | Yes | fairly_priced |
| 16 | MOFIREIF | neutral | +0.00% | not_applicable | **Yes** | Yes | fairly_priced |
| 17 | MOFIREIF | neutral | +0.00% | not_applicable | **Yes** | Yes | fairly_priced |
| 18 | CILEASING | neutral | −3.33% | not_applicable | No | Yes | fairly_priced |

**Summary**: 3 confirmed, 1 contradicted, 5 inconclusive (flat/no data), 9
not-applicable (no directional claim), 4 flagged thin-liquidity.

## The GTCO case — a concrete, real cross-validation of the self-critique gate

Implication 1 (GTCO's ₦400.5bn rights issue) is the single most
consequential result in this pilot. The AI layer's own `direction` verdict
was `bullish` (`magnitude='large'`) — and this exact implication was
independently **blocked by the platform's own self-critique gate**
(`status='blocked_by_self_critique'`, on record since the 2026-07-27
stabilization pass, per `HANDOFF.md`), specifically over concern that the
"bullish" framing understated real dilution risk. This module's fully
independent, deterministic, price-only check finds the realized return
over the following week was **−1.32%** — the actual market direction
**disagrees** with the bullish call. **The self-critique gate's skepticism
about this specific claim is now corroborated by real, independent
price evidence**, not just by the platform's own qualitative reasoning.
This is presented as a finding for review, not as proof that self-critique
"works" in general — a single case is not a validation study — but it is
a genuine, real, disclosed data point in the gate's favor.

## Disclosed limitation: the liquidity floor, chosen before seeing results, does not catch every real thin-trading case

The `deals < 10` floor was picked before running the pilot, deliberately
not tuned afterward to fit what was observed (the same discipline applied
throughout this FRE program). **It has a real, honestly-disclosed miss**:
implication 3 (TOTAL, +33.34% over the window) has only **21 deals** on
its anchor day (2016-07-29) before recovering to 52–141 deals within a
week — moderately thin, but not below the chosen floor, so the flag does
not fire even though this is plausibly the single most suspicious return
in the entire pilot (the largest move, on the thinnest anchor day). Raising
the floor after seeing this would be exactly the kind of after-the-fact
threshold-tuning this program has repeatedly refused to do elsewhere
(Part 1's ontology, FRE-2's classifier). The limitation is disclosed here
instead, as a concrete candidate for a future, separately-justified
refinement (e.g., averaging `deals` across the whole window rather than
checking only the two anchor points).

## Alternatives considered

1. **Overwrite `market_reaction_assessment` with the deterministic
   verdict.** Rejected — would destroy real experiment history (the
   existing LLM verdict is itself a disclosable data point about the
   AI layer's current behavior) and modify AI-layer data with no
   documented blocker requiring it.
2. **Reproduce the full four-way vocabulary via an invented magnitude→return
   mapping.** Rejected — directly contradicts the Reasoning Engine
   Specification's own explicit refusal to invent such a mapping; the
   narrower direction-only check is the defensible alternative.
3. **Adjust returns for the mechanical ex-dividend price drop.** Rejected
   for this pass — correct ex-dividend adjustment requires precise
   ex-date/amount data not uniformly available across all 18 facts;
   attempting a partial adjustment risked a subtly-wrong correction being
   presented as more rigorous than a plainly-disclosed raw return. Flagged
   in every dividend-fact result via `ex_dividend_confound_flag` instead.
4. **A calendar-day window instead of a trading-row count.** Rejected —
   MOFIREIF's real data shows month-long gaps between trades; a
   calendar-day window would silently fail (find no data) far more often
   than a trading-row count, which degrades gracefully to whatever data
   actually exists.

## Trade-offs

- The direction-only check is a narrower, less informative signal than
  the full over/under-reaction judgment Part 6 originally sketched — a
  deliberate trade of ambition for defensibility.
- Not adjusting for ex-dividend mechanics means roughly two-thirds of this
  pilot's results (12/18 dividend facts) carry a real, disclosed confound;
  the flag makes this visible per-result rather than hidden in an
  aggregate.

## Risks

- **The liquidity floor's known miss** (TOTAL, above) — disclosed, not
  fixed, in this pass.
- **A single real disagreement (GTCO) should not be over-generalized** —
  presented as one data point, not as proof the self-critique gate is
  reliable in general; a rigorous claim would require many more cases.
- **`filing_date` as an event-date substitute** may lag the actual
  event by days in some cases (the same substitution risk already named
  in Part 6's design) — disclosed, not solved.

## Future extensions

- A window-averaged liquidity check (mean `deals` across the whole window,
  not just the two anchor points) — would likely catch the TOTAL case
  above; not built here to avoid post-hoc tuning.
- Ex-dividend-adjusted returns, once precise ex-date/amount data is
  uniformly available.
- Re-run at greater volume once more real implications exist, to see
  whether the 17/18 "fairly_priced" LLM pattern persists or was itself an
  artifact of this session's small, dividend-heavy dataset.

## Verification performed

| Check | Result |
|---|---|
| `scripts/fre/test_reaction_check.py` | **16/16 PASS** (GTCO's real disagreement, ex-dividend flag correctness, thin-liquidity flag correctness on real NAV-pegged/thinly-traded instruments, all 18 real implications resolve cleanly, a nonexistent `implication_id` raises rather than fabricating) |
| `scripts/test_reasoning_pipeline.py` (pre-existing) | 154/154 PASS, unchanged |
| `scripts/fre/test_evidence_graph.py` (FRE-2) | 29/29 PASS, unchanged |
| `scripts/fre/test_company_memory.py` (FRE-3) | 16/16 PASS, unchanged |
| `scripts/check_db_safety.py` | PASS, 0 violations |
| Production DB row counts, all 27 tables | Unchanged — this module has no write path at all; explicitly verified `market_reaction_assessment`/`.reasoning` are byte-identical to their pre-existing values |

## Dependencies

`docs/fre/06_cross_document_reasoning.md` (the design this implements),
`investment_implications`, `extracted_facts`, `documents`, `equity_prices`
(the existing, Coverage-Gate-v2-validated PIT price panel) — all existing,
read-only. Independent of FRE-2's `evidence_graph.py` and FRE-3's
`company_memory.py` (no import between any of the three FRE modules).

---

*Per the standing instruction, this concludes FRE-4. Stopping here and
awaiting review before beginning FRE-5.*
