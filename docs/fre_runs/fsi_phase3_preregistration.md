# FSI Phase 3 — Financial Reasoning over Validated Facts (Pre-registration)

*Design only. No implementation, no schema change, no new extraction, no
valuation activation, no portfolio reasoning, no alpha claim. Per
instruction, written and frozen BEFORE any execution begins — the same
two-gate discipline used throughout LIM and every prior FRE/FSI phase.
Builds on `fsi-phase2-baseline-2026-08-01` (106 financial-statement
facts, 5 tickers) and explicitly reorients away from further extraction:
Phase 3's objective is to transform this now-validated dataset into
institution-grade analytical conclusions, while preserving provenance,
explainability, auditability, and reproducibility — the four properties
named directly in the owner's instruction, treated below as the four
design axes every proposed mechanism must satisfy, not as background
values.*

## Objective

Build a **Financial Reasoning layer** that consumes the 106 validated
FSI facts (Phase 1's revenue/net_profit + Phase 2's balance sheet, cash
flow, EBITDA/EBIT) and produces structured, evidence-grounded analytical
statements about a single company's own financial condition and
trajectory — e.g. leverage direction, margin trend, cash-flow/earnings
consistency, balance-sheet strength — each one fully traceable to the
specific facts it was computed from, reproducible on rerun, and
explicitly incapable of producing a valuation number, an expected
return, a target price, a portfolio-sizing implication, or a cross-
company ranking. This is a **reasoning** phase, not an **extraction**
phase — no new fact_type is proposed, no new document is read, no new
`extracted_facts` row is written by anything in this design.

## What Phase 1+2 actually provide (the evidence base for every design choice below)

Direct query against the real, frozen `fsi-phase2-baseline-2026-08-01`
database, not assumed:

| Ticker | Fact types covered | Periods | Notes |
|---|---|---|---|
| **NASCON** | revenue, net_profit, assets, liabilities, equity, cfo, cfi, cff, ebit, ebitda (10 of 12) | 3 (H1'24, FY'24, FY'25) | The only ticker with full cash-flow + EBITDA/EBIT coverage in every period — the natural first pilot case |
| **BUAFOODS** | revenue, net_profit, assets, liabilities, equity, ebit, ebitda (7), + cfo/cff in 1 of 3 periods | 3 | Cash-flow coverage is real but incomplete — a genuine partial-coverage case, not a gap to paper over |
| **AFRIPRUD** | revenue, net_profit, assets, liabilities, equity, ebit, ebitda (7 of 12) | 3 | No cash-flow data at all in any filing — a real, permanent gap for this ticker, not a temporary one |
| **CAP** | revenue, net_profit, ebit (3 of 3 periods); assets/liabilities/equity (2 of 3 — doc 4508 has none); capex/fcf (1 of 3) | 3 | The most unevenly-covered ticker; no ebitda anywhere (no D&A ever disclosed) |
| **UCAP** | revenue, net_profit, assets, liabilities, equity only (5 of 12) | 3 | A bank — no cfo/cfi/cff/ebit/ebitda by design (Stage 4's disclosed architectural scope boundary, not a gap to close) |

**A real, disclosed data-quality finding that directly shapes this
design**: `confidence_tier` is `NULL` on all 30 of Phase 1's original
facts (revenue/net_profit) — the column did not exist until Phase 2's
Stage 1 schema migration, and Phase 1's facts were never backfilled. Of
Phase 2's 76 facts, 62 are `direct_reported`, 11 `mapped_equivalent`, 3
`derived`; `interpretation` has never been written (0, confirmed).
**Any Phase 3 mechanism that propagates confidence must treat `NULL` as
its own distinct case — never silently assumed equal to
`direct_reported`** — this is a concrete, load-bearing design
requirement below (Area 5), not a hypothetical.

Coverage is genuinely uneven by real document content, not by omission —
any Phase 3 mechanism must be able to say "insufficient data for this
conclusion" per ticker/metric, honestly and mechanically, rather than
silently skip or force a conclusion from partial data.

## Explicit non-goals (restated up front, because this is the area of highest risk)

- **No valuation output of any kind** — no DCF/DDM/comparable output,
  no intrinsic value, no fair-value range. `valuation_engine.py`
  remains untouched and its `compute()` methods remain unimplemented
  regardless of anything in this phase.
- **No expected return, no target price, no alpha claim.**
- **No portfolio-sizing or portfolio-construction implication** — Phase
  3's output is about one company's own financial statements, not a
  buy/sell/hold/size signal.
- **No cross-company ranking or comparison** — a statement like "NASCON's
  leverage is healthier than CAP's" is explicitly OUT OF SCOPE, even
  though the data would technically support computing it, because a
  ranking is the first step toward an implied screening/portfolio
  signal (exactly the risk the frozen architecture's Part 9 and FRE-9's
  own "watchlist-creep-into-ranking" risk are designed to guard
  against). Phase 3 conclusions are always scoped to a single ticker.
- **No new extraction, no new document reading, no new fact_type.**

## Scope — the seven required design areas

### 1. Ratio derivation layer (mechanical, deterministic)

**Target ratios, computed only where their inputs exist for the same
ticker/period** (per Phase 2 final report's own recommendation #3):
`current_ratio` is not computable from this dataset (no current-vs-
non-current asset/liability split was extracted — only totals), so the
realistic starting set is **debt_to_equity** (`liabilities / equity`),
**ebitda_margin** (`ebitda / revenue`), **ebit_margin** (`ebit /
revenue`), **net_margin** (`net_profit / revenue`), and **cfo_to_net_profit**
(`cfo / net_profit`, a quality-of-earnings signal — see Area 3). Every
ratio computation records exactly which `fact_id`s were divided, never
just the resulting number.

**Confidence propagation rule (concrete, testable)**: a derived ratio's
confidence is the **weakest** of its inputs' tiers, using the order
`direct_reported > mapped_equivalent > derived > NULL/unknown` (worse
than `derived`, treated as the floor, per the finding above) — e.g. an
`ebit_margin` computed from a `mapped_equivalent` ebit and a `NULL`-tier
Phase-1 revenue fact is itself, at best, `NULL`/unknown-floored, not
silently promoted to `mapped_equivalent`. This is the direct, mechanical
answer to "preserving... explainability" from the owner's instruction —
a ratio is only as trustworthy as its worst input, stated plainly, not
averaged away.

### 2. Trend / trajectory classification (mechanical, per ticker, per metric)

For any metric with ≥2 real periods for the same ticker (all 5 tickers
qualify, all having exactly 3 periods), classify direction as
`improving` / `deteriorating` / `stable` using a **disclosed percentage-
change threshold** (proposed: >5% = directional, ≤5% = `stable` — a
reasoned, not empirically validated, choice, stated as such, matching
`period_normalization.py`'s own precedent of a disclosed, not derived,
threshold). Direction is **metric-specific**, not generically "good/bad"
— e.g. rising `debt_to_equity` is always classified `increasing`, never
labeled "deteriorating" without a metric-specific polarity table
(rising leverage is not universally bad; rising margin is not
universally good without context) — Phase 3 states the mechanical
direction only, and does NOT infer whether a direction is favorable,
which is exactly where a valuation/alpha-adjacent judgment would start
to leak in.

**A genuine limitation, disclosed rather than smoothed over**: 3 periods
per ticker is a very short trend window, and periods are not always
evenly spaced or of matching length (e.g. NASCON's own H1'24 vs FY'24 vs
FY'25 mixes half-year and full-year spans) — any trend statement must
name the exact periods and their `period_type`s it was computed over,
never imply a smooth annual trend from mismatched spans.

### 3. Rule-based financial-health flags (mechanical, auditable)

A small, fixed, disclosed rule set — each rule is a plain condition over
already-derived ratios/trends, with its own name, trigger condition, and
citation back to the exact facts involved. Proposed starter rules
(illustrative, not exhaustive — the actual rule set is an execution-time
design decision, not decided here):

- `leverage_increasing`: `debt_to_equity` trend = `increasing` across
  all available periods.
- `cash_flow_earnings_divergence` (a real quality-of-earnings check):
  `cfo_to_net_profit` < 1.0 in the most recent period with both facts
  present — net income exceeds operating cash generation, a real,
  named accounting-quality signal, not a valuation judgment.
- `margin_compression`: `ebitda_margin` or `net_margin` trend =
  `deteriorating` across all available periods.
- `insufficient_data_for_flag`: explicitly emitted (not silently
  omitted) whenever a rule's required inputs don't exist for a ticker —
  e.g. `cash_flow_earnings_divergence` is mechanically `insufficient_
  data` for AFRIPRUD (no cfo ever extracted) and for CAP (cfo never
  extracted, only fcf/capex in one period) — stated explicitly per
  ticker, never left as a silent absence.

Every flag is a **named, disclosed, deterministic function of the
already-derived ratios/trends** — no free-text model judgment enters
this layer at all. This is the layer that does the most direct work
toward "institution-grade analytical conclusions" while keeping
reproducibility total (rerun on the same fact set → byte-identical
flags, every time).

### 4. Evidence-grounded narrative ("why") — explicitly separated, optionally LLM-based, its own gate

Areas 1-3 are entirely mechanical. A genuine institutional analyst
conclusion often also explains *why* (e.g. tying BUAFOODS's real,
disclosed "EBITDA margin deteriorated... due to the increase in input
costs" narrative — already present in the filing text Phase 2 already
read — to a `margin_compression` flag). This is the one place a model
call could add real value, and it is the one place risk (hallucination,
ungrounded claims, silent alpha-adjacent framing) is highest — treated
here as its own explicitly gated sub-decision, not bundled into the rest
of Phase 3:

- **Reuses, does not fork, the existing AI Intelligence Layer's
  self-critique/grounding infrastructure** (`src/ngxrot/documents/
  extract.py`, `self_critique.py`, `grounding.py`) — any narrative
  explanation must pass the same quote-grounding and self-critique gate
  every other AI-generated claim on this platform already passes before
  being usable, never a new, looser check invented for convenience.
- **Requires its own LLM vendor/cost decision** — this remains a
  standing open item on this platform (Gemini free-tier quota
  limitations already encountered in the AI Intelligence Layer's own
  pilot); Phase 3's design does not resume that decision, it inherits
  it as a dependency (see Dependencies below).
- **Proposed as OPTIONAL / Phase 3b**, separable from Areas 1-3: the
  mechanical layer (Areas 1-3) is fully useful, fully reproducible, and
  requires no LLM call at all; the narrative layer is a genuine
  enhancement but not a precondition for Phase 3's core deliverable.
  This mirrors this program's own recurring pattern of separating a
  cheap, reproducible mechanical capability from a more expensive,
  harder-to-fully-audit LLM-based one (e.g. FRE-2's evidence graph
  being entirely mechanical while `extract.py`'s Steps 1-13 remain the
  separate, LLM-based, self-critique-gated layer).

### 5. Confidence and coverage propagation discipline

Every Area 1-3 output carries: (a) the exact `fact_id`s used, (b) the
propagated confidence tier (per Area 1's rule, `NULL`-input-aware), (c)
an explicit `insufficient_data` state distinct from a "clean pass"
result whenever required inputs don't exist for a ticker/period. No
conclusion is ever produced by substituting a different metric, a
different ticker's typical value, or an assumed default for a missing
input — the same "no inferred financial facts" rule that governed every
FSI Phase 1-2 extraction script applies identically here to reasoning
outputs.

### 6. Auditability and reproducibility mechanism (storage design — flagged, not built)

Proposed (not created in this pass, a real, disclosed schema need
requiring its own separate approval, exactly like Phase 2's own
`period_type`/`confidence_tier`/`restates_fact_id` were flagged in
Phase 2's own pre-registration before being approved and built): a new,
additive table — proposed name `financial_reasoning_conclusions` — with
columns for `ticker`, `conclusion_type` (ratio/trend/flag), `metric`,
`value_or_direction`, `confidence_tier`, `input_fact_ids` (a
traceable list/join table, not a free-text blob), `rule_version` (so a
future rule-set change is distinguishable from a data change — mirrors
`llm_calls.prompt_version`'s existing precedent), and `computed_at`.
**Append-only**: a rerun with the same inputs and the same rule version
must reproduce byte-identical rows; a rerun after a rule-set change
inserts NEW rows under a new `rule_version`, never overwrites old ones —
the same versioned, non-destructive convention as
`investment_implications` and `restates_fact_id` elsewhere on this
platform.

### 7. Single-company scope enforcement (a mechanical, auditable guardrail, not just a stated intention)

Per the non-goals section above, "no cross-company ranking" must be
enforced the same way FRE-9's design proposes enforcing "no watchlist-
into-ranking": a **mechanical import-graph/interface check** — the
reasoning module's public functions accept exactly one ticker at a time
and return no comparative field, verifiable by inspection, not merely
promised in a docstring. This is flagged here as a concrete acceptance
criterion for Phase 3's eventual execution, not assumed satisfied by
good intentions.

## Pre-registered success / partial / failure criteria

Set now, before any implementation — genuinely open, since this is the
first test of reasoning (not extraction) on this dataset:

| Component | Success | Partial | Failure |
|---|---|---|---|
| Ratio derivation (Area 1) | Correctly computed (verified by hand) for 100% of ticker/period/metric combinations where inputs exist; confidence propagation rule correctly applied (including the `NULL`-input case) in 100% of cases | Ratios correct but confidence propagation has ≥1 disclosed error | Any silently-wrong ratio value |
| Trend classification (Area 2) | Directionally correct (verified by hand against the raw facts) for every metric/ticker with ≥2 periods, mismatched-period-span caveat correctly attached whenever applicable | Correct direction, caveat occasionally missing | Any wrong direction |
| Health flags (Area 3) | Every flag's trigger condition is met exactly on the data that produced it (a mechanical audit, not a judgment call), `insufficient_data` correctly emitted for every ticker/metric combination lacking required inputs (e.g. AFRIPRUD/CAP's cfo gap) | Flags correct, `insufficient_data` handling incomplete | Any flag fires on data that does not meet its own stated condition |
| Single-company scope enforcement (Area 7) | Mechanical check confirms zero cross-ticker comparative output | n/a — this is a binary pass/fail guardrail | Any comparative or ranking output found |

Area 4 (narrative) is **not scored in this pre-registration** — it is
optional and depends on a separate LLM vendor/cost decision not yet
made; if pursued, it requires its own pre-registered success criteria
at that time, matching this platform's own precedent of never bundling
an unproven capability's evaluation into an already-approved one's.

## What Phase 3 explicitly does NOT do

- No implementation of any kind in this pass — this document is design
  only.
- No new extraction, no new document read, no new `extracted_facts`
  row, no new fact_type.
- No schema change — the `financial_reasoning_conclusions` table (Area
  6) is a named, disclosed need requiring its own separate approval, not
  built here.
- No valuation activation, no expected return, no target price, no
  alpha claim.
- No portfolio reasoning, no cross-company ranking or comparison.
- No LLM call of any kind in the mechanical core (Areas 1-3, 5-7); any
  narrative layer (Area 4) is explicitly optional, separately gated, and
  not part of this pre-registration's scored scope.
- No production-scale rollout — the 5-ticker, 106-fact pilot dataset is
  the entire proposed scope for Phase 3's first pass.

## Dependencies

The frozen `fsi-phase2-baseline-2026-08-01` dataset (106 facts, 5
tickers) and `configs/financial_ontology.toml`'s existing definitional
edges (reused for ratio semantics, e.g. confirming `debt_to_equity`'s
components are the same `liabilities`/`equity` nodes already used for
Stage 2's accounting-identity check — read-only reuse, no change
proposed). A new, unbuilt schema need (`financial_reasoning_
conclusions`, Area 6) flagged for future approval. If Area 4 (narrative)
is ever pursued: the existing AI Intelligence Layer's `extract.py`/
`self_critique.py`/`grounding.py` (reused, not forked) and a resolved
LLM vendor/quota decision (a standing open item, not resolved by this
document).

## Risks

- **Confidence-propagation correctness is the single highest-value
  check in this phase** — if the `NULL`-input handling (the concrete
  finding from Phase 1's un-backfilled facts) is wrong, every downstream
  ratio/flag inherits a silently-overstated confidence, which is exactly
  the kind of "hidden assumption" this entire program has been built to
  avoid. Flagged as the top mechanical-correctness risk for execution to
  test explicitly, the same way Phase 2 flagged EBIT/Operating-Profit
  equivalence as its own top risk.
- **Short, uneven trend windows** (3 periods, mismatched spans) risk
  producing a technically-correct but practically-thin trend statement
  — mitigated by requiring every trend output to name its exact periods,
  never implying more than 3 real data points support.
- **Rule-set arbitrariness**: the proposed starter flags (Area 3) are a
  reasoned but not empirically validated set — an execution pass may
  find them too permissive or too strict on real data; `rule_version`
  (Area 6) exists specifically so a rule-set correction is a new,
  disclosed version, not a silent redefinition of history.
- **Scope-creep risk toward valuation/ranking is the single largest risk
  in this entire phase**, given how naturally "which company looks
  healthiest" follows from having ratios for 5 tickers side by side —
  Area 7's mechanical enforcement exists specifically to make this risk
  auditable rather than merely policed by good intentions.

## Stop condition

If the confidence-propagation rule (Area 1) cannot be implemented
correctly against the real `NULL`-tier Phase-1 facts (i.e., if a
genuine architectural reason prevents distinguishing `NULL` from
`direct_reported` cleanly), stop and report that as a blocker — do not
proceed with a looser propagation rule that silently treats legacy
facts as fully trusted. If any mechanical rule (Area 3) cannot be
stated as a precise, auditable condition without importing a subjective
judgment, drop that rule from the proposed set and report why, rather
than keep an imprecise rule to preserve rule-set size.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration must be reviewed and approved — including, explicitly,
a decision on the `financial_reasoning_conclusions` schema need (Area 6)
and whether Area 4 (narrative) is authorized at all in this pass or
deferred — before any Phase 3 execution begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
