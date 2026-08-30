# Directional Reasoning Layer — Repair & Validation

*2026-08-17. Investigates whether the reasoning layer's FACT -> DIRECTION
output can be repaired into a genuinely useful investment-intelligence
component, without allowing it near the quantitative Alpha Engine. Runs
entirely against the real, live database, read-only. New code:
`src/ngxrot/fre/directional_reasoning_v2.py` (Phases 1, 2, 3, 5, 7),
`scripts/fre/test_directional_reasoning_v2.py` (19/19 checks). No schema
change, no write path, no LLM calls made in this pass.*

---

## 1. Baseline (Phase 0 — freeze)

| Check | Result |
|---|---|
| git state | Zero diff on the four protected Alpha Engine files (`alpha_engine.py`, `engine_full.py`, `runner.py`, `registry.py`) before this pass and after, confirmed both times via `git diff --stat`. A large amount of unrelated pre-existing uncommitted work exists elsewhere in the repo (from prior sessions) — left untouched. |
| Production DB integrity | `PRAGMA integrity_check` = `ok` |
| `extracted_facts` | 495 rows |
| `financial_reasoning_conclusions` | 403 rows |
| `investment_implications` | 48 rows (grew from 43 at the last audit, 18 at FRE-4's original pilot) |
| `evidence` / `self_critique_reviews` / `llm_calls` | 627 / 184 / 69 |
| H-011 live output | 20 `buy` recommendations, unchanged from the run captured in `docs/fre_runs/engine_status_2026-08-17.txt` |
| `reaction_check()` (unmodified, zero diff) re-run over all 48 implications | 10 confirmed / 11 contradicted / 16 inconclusive / 11 not_applicable — matches the numbers this investigation was opened on |
| `check_db_safety.py` | PASS |
| No execution/broker path exists anywhere on the platform | confirmed (`grep` for order-placement/broker-API code: zero hits) |

**Pre-existing test staleness, found and disclosed, not fixed in this pass** (none caused by this work — none of these files were touched):
`test_reaction_check.py` 12/16, `test_valuation_engine.py` 79/81, `test_company_thesis.py` 20/21,
`test_evidence_graph.py` 24/29 — all failures are hardcoded historical row-counts that predate this
session's data growth (e.g. "18 real facts" now 48, "292 line items" now 321). Same class of issue
`reaction_check.py`'s own module docstring already discloses. Out of scope for this repair (it targets
the reasoning layer, not test-baseline maintenance) — flagged here so it isn't mistaken for a regression.

---

## 2. Failure taxonomy (Phase 1)

Ran a deterministic classifier (`classify_taxonomy()`) over all 48 implications, reusing
`reaction_check()`'s own ground truth. Category counts:

| category | n |
|---|---|
| inconclusive (flat move / no price data) | 16 |
| not_applicable (neutral direction, no claim to check) | 11 |
| confirmed_no_failure | 10 |
| fundamental_improvement_incorrectly_bullish | 10 |
| valuation_blindness | 11 |
| expectations_blindness | 11 |
| conflicting_factor_blindness | 1 |
| fundamental_deterioration_incorrectly_bearish | 1 |

**The load-bearing fact**: every one of the 11 `direction_contradicted` cases carries both
`valuation_blindness` and `expectations_blindness` simultaneously — 100%, not a majority. The failure
mode is uniform, not case-specific.

---

## 3. Contradiction analysis (Phase 2)

Built `detect_contradictions()` — groups implications by `(ticker, filing_date)` (the same anchor
`reaction_check()` uses) and flags any group containing both a `bullish` and a `bearish` claim on the
same filing.

**Result over all 48 implications: exactly one real contradiction.**

```
VERITASKAP, filing_date=2026-05-07
  implication 39: bullish  (source fact: revenue +N5.3bn — "expanding structural earning capacity")
  implication 40: bearish  (source fact: net_profit — "tax drag and FX losses reduced net cash
                             earnings, creating competing valuation signals")
  Market reaction: -6.90% over the next 5 trading days.
```

The system does **not** retain both `BULLISH` and `BEARISH` for this pair — `staged_conclusion()`
(Phase 3) returns `CONFLICTED` for **both** implication 39 and implication 40, per the explicit design
requirement. This is an honest trade: implication 40 happened to be directionally right, and the new
system suppresses it along with the wrong one, because at the decision timestamp there was no way to
know which of two opposing same-filing signals would dominate. Confirmed by regression test (see §9).

No other ticker in the current 48-row dataset has more than one directional claim on the same filing —
this is not a systemic pattern yet, just the one real, disclosed case it was built to catch.

---

## 4. Root causes (Phase 3 investigation, using real data — not hindsight)

Four independent, verified causes, not one:

**(a) Valuation is structurally unavailable for the failing universe.** `valuation_engine.py`'s real
`PEAdapter`/`PBAdapter` (activated FRE-7, 2026-08-09 — this is NOT the "deliberately unimplemented"
state an earlier audit recorded; `compute()` now has real P/E and P/B formulas) were run, PIT-correct
(`as_of=filing_date`, no lookahead), against all 20 tickers that have ever received an implication.
**Only 3 of 20 — BUAFOODS, NASCON, UCAP — ever produce a computable point estimate, at any date.** Zero
of the 10 tickers in H-011's small-cap sleeve (CAVERTON, CUTIX, LASACO, NCR, PRESTIGE, MCNICHOLS,
CILEASING, REDSTAREX, VERITASKAP, UNIVINSURE) have ever had a computable P/E or P/B — the missing input
is shares-outstanding, which this platform has never acquired for these names. This is permanent, not
a point-in-time artifact: re-checked at the current date (2026-08-17) with the identical null result.

**(b) No earnings-expectations dataset exists anywhere on the platform.** Verified directly against the
live schema (`grep`-equivalent table scan for analyst/estimate/consensus/expectation naming): zero
matching tables. `docs/HYPOTHESIS_FAMILY_MAP.md`'s own F10 ("coverage-initiation effects") is tagged
`speculative` precisely because `broker_research_archive` was never acquired. This is not a gap the
reasoning layer could have closed on its own — the data literally does not exist.

**(c) The reasoning layer reasons fact-by-fact, never filing-by-filing.** Direct inspection of the
source facts behind the 5 mandatory red-team tickers: PRESTIGE, CILEASING, and REDSTAREX each received
**2–3 separate implications from the same filing** (revenue, net_profit, ebit each independently scored
bullish), with no cross-fact synthesis. CILEASING's own filing shows revenue=N12.78bn against
net_profit=only N500.41mn — a ~3.9% net margin, a real, visible-in-the-same-document red flag — but
because each fact is interpreted in isolation, no implication ever surfaces the thin-margin context
that the sibling `net_profit` fact from the *same document* discloses. This is a structural, not
statistical, finding: it explains why `conflicting_factor_blindness` only fired once (§3) despite
several filings visibly containing offsetting signals — the current architecture cannot see across
facts within one document unless two *separate* directional implications happen to be generated for
opposing metrics (as VERITASKAP's did).

**(d) Market-regime confound was checked and ruled out.** Compared each of the 5 mandatory tickers'
realized return against NGXASI (the broad market index) over the identical window:

| ticker | stock return | NGXASI return | same direction as market? |
|---|---|---|---|
| LASACO | -11.26% | +0.39% | **No** |
| PRESTIGE | -6.00% | +1.32% | **No** |
| CILEASING | -2.86% | +3.16% | **No** |
| REDSTAREX | -8.64% | -0.19% | Yes (both ~flat/negative) |
| VERITASKAP | -6.90% | +5.29% | **No** |

In 4 of 5 cases the broader market was actually *rising* while the individual stock fell. This rules
out "the whole small-cap segment sold off" as an excuse — these are genuine stock-specific reasoning
failures, not noise from a systemic down-move. Prior-60-trading-day momentum into each filing was also
checked (an "already priced in" test): mixed, no consistent pattern (LASACO -4.9%, PRESTIGE +4.9%,
CILEASING +0.7%, REDSTAREX 0.0%, VERITASKAP -18.7%) — this factor does not explain the failures either.

**(e) Financial-health-flag infrastructure (`financial_health_flags.py`) exists and partially helps,
but wasn't PIT-queryable as shipped.** The module always reads the *current* most-recent conclusion —
correct for live monitoring, wrong for a no-hindsight historical check. Added a thin, explicitly-scoped
PIT filter (`period_end <= anchor_date`) reusing the *exact same* rule definitions (not new logic) and
re-ran for the 5 mandatory tickers: LASACO had a real, PIT-available `cash_flow_earnings_divergence`
flag (`cfo_to_net_profit = 0.367`, period 2022, well before the 2026-03-28 decision) that would have
been a real, non-hindsight warning sign. The other 4 tickers have **no** PIT-available
`financial_reasoning_conclusions` at their decision dates at all — genuinely `insufficient_evidence`,
not a coverage gap this pass could close.

---

## 5. Architecture changes (Phase 3, 5, 7)

`src/ngxrot/fre/directional_reasoning_v2.py` — new, isolated module. Implements the staged pipeline
the task specified:

```
FACT -> FUNDAMENTAL_INTERPRETATION -> MATERIALITY -> VALUATION -> EXPECTATION -> CONFLICT -> CONCLUSION
```

- **`FundamentalInterpretation`** — reuses the existing LLM's own `direction` field as input (re-deriving
  it from raw prior-period deltas was out of scope for this pass; disclosed, not hidden).
- **`MaterialityAssessment`** — reuses the existing LLM's own `magnitude` field (informational reuse,
  not independently re-derived — avoids inventing a new, unvalidated materiality threshold).
- **`ValuationCheck`** — real `PEAdapter`/`PBAdapter.compute()` calls, PIT `as_of=filing_date`. Returns
  `insufficient_evidence` honestly (`point_estimate=None`) rather than ever fabricating a number.
- **`ExpectationCheck`** — always `insufficient_evidence`, with the reason stated (§4b) — a structural,
  platform-wide fact, not a per-case judgment.
- **`ConflictCheck`** — output of the Phase 2 contradiction engine.
- **`MarketContextCheck`** — NGXASI same-window return; **informational only, never gates the
  conclusion** (per the task's own framing: market regime is context, not proof).
- **Final conclusion** — one of `CONFLICTED` / `DIRECTIONAL_WEAK` / `INSUFFICIENT_EVIDENCE`.
  **Never a bare `bullish`/`bearish`** — this is the concrete mechanism enforcing "business improved"
  != "security should outperform": the pipeline is structurally incapable of re-adding the false
  confidence the original naive mapping had, because it only reaches a full market-direction claim if
  valuation *and* expectations both resolve — which (§4a, §4b) they structurally never do for this
  platform's real small-cap data today.
- **`unweighted_score()`** (Phase 5) — a **completeness count** (0–4 stages resolved), explicitly *not*
  a weighted composite. No weights were fit; guardrail against optimizing against the 21 observations
  respected by construction — there is nothing to overfit because nothing is weighted.
- **Phase 7 firewall**: `REASONING_WEIGHT = 0.0`, hardcoded, module-level, with a comment stating it is
  "never read by alpha_engine.py / engine_full.py / runner.py / registry.py." Verified by direct grep:
  zero references to this module in any of the four protected files, both before and after this pass.
  This module imports `reaction_check.py` and `valuation_engine.py` (read-only, pre-existing) and
  nothing else project-internal.

---

## 6. Tests

`scripts/fre/test_directional_reasoning_v2.py` — **19/19 checks pass**, including:
firewall (weight fixed at 0, zero imports from protected files), the VERITASKAP worked example resolving
both sides to `CONFLICTED`, no fabricated valuation numbers, expectation always `insufficient_evidence`,
neutral-direction implications never forced into a directional call, a nonexistent `implication_id`
raising rather than fabricating, and zero production-data mutation (`investment_implications`/
`extracted_facts` row counts unchanged before/after).

Full regression across existing FRE suites re-run (see §1 for the pre-existing, unrelated staleness
found): `test_reaction_check.py`, `test_evidence_graph.py`, `test_company_memory.py` (16/16, clean),
`test_valuation_engine.py`, `test_company_thesis.py`, `test_reasoning_pipeline.py` (all pass, clean).

---

## 7. Out-of-sample methodology (Phase 6)

**Explicitly reported as insufficient, not manufactured.** 21 scoreable observations is far below any
threshold for a meaningful train/design/validation/holdout split — and of those 21, the repaired
architecture's *only* discriminating mechanism (the contradiction engine) affects exactly **2** of them
(the VERITASKAP pair). A formal chronological split was attempted and abandoned: with contradictions
this rare, any split either contains zero conflict cases (nothing to validate) or is small enough that
a single case dominates the result — not a statistically meaningful test either way.

**Reported honestly as Phase 6 = INSUFFICIENT DATA.** This does not block reporting the shadow-test
result below (§8) as a descriptive, single-pass check — but no claim of statistical significance is
made from it, and none should be inferred.

---

## 8. Shadow-test results (Phase 8)

Ran `staged_conclusion()` against all 21 currently scoreable implications and compared against
`reaction_check()`'s realized ground truth (no capital, no execution, no change to H-011):

| staged conclusion | n | of which realized `direction_confirmed` | of which realized `direction_contradicted` |
|---|---|---|---|
| `CONFLICTED` | 2 | 1 (VERITASKAP #40) | 1 (VERITASKAP #39) |
| `DIRECTIONAL_WEAK` | 19 | 9 | 10 |

**The honest result**: the contradiction engine works exactly as designed on the one real case it was
given (§3) — it correctly refuses to assert either direction when the evidence is genuinely split. But
outside that single pair, the repaired pipeline provides **zero discriminating power**: 19 of 21 cases
land in the same `DIRECTIONAL_WEAK` bucket regardless of whether the market ultimately agreed (9) or
disagreed (10) with the original call, because valuation and expectations — the two stages that could
have discriminated — are structurally unavailable for essentially this entire universe (§4a, §4b). This
is not a tuning problem; it is a data-availability ceiling this pass cannot lift without a genuinely new
dataset (shares-outstanding for small-caps, and/or an earnings-expectations source), neither of which
exists on this platform today and neither of which this pass fabricated to force a better-looking
result.

---

## 9. H-011 status

Confirmed unchanged throughout: `git diff --stat` on `alpha_engine.py`/`engine_full.py`/`runner.py`/
`registry.py` empty before this pass and after (§1, §5). `REASONING_WEIGHT = 0.0`. No shadow run was
fed into H-011's ranking, portfolio construction, or any execution path (none exists on this platform —
confirmed §1). H-011 remains exactly what it was: a paper-only, quantitative, size-factor signal, fully
independent of this investigation's output.

---

## 10. Decision

## **B — REPAIR BUT KEEP EXPERIMENTAL**

Not A: the architecture is genuinely repaired (§5) and passes every structural test asked of it (§6,
§9), but it demonstrates **zero measured incremental discriminating value** on the one metric that
matters — telling a future-right call from a future-wrong one (§8, 19/21 indistinguishable). "Repeatable
out-of-sample value" (Phase 9's bar for A) cannot be claimed from a shadow test with 2 informative
observations out of 21.

Not C: outright abandonment is not supported either. The repair fixed a real, concrete defect (the
VERITASKAP same-filing self-contradiction, §3) that the old architecture could never have caught by
construction, and it structurally eliminated the "business improved != security should outperform"
conflation the old pipeline made every single time (§5). Killing the module would also kill a working,
tested, zero-cost contradiction detector with no offsetting benefit.

Close to D for one specific sub-question (Phase 6's out-of-sample validation, §7 — honestly
insufficient data, not fabricated), but the investigation as a whole is not blocked: the root causes
(§4) are concretely identified, not unknown, and the shadow test (§8), while statistically thin, is a
real, disclosed, negative-leaning result — not an absence of information.

**Exact next action**: leave `directional_reasoning_v2.py` wired with `REASONING_WEIGHT = 0.0`,
unpromoted, uncalled by anything in the alpha path. Two concrete, named prerequisites before this
question can be reopened as a validation question rather than a data-availability question:

1. **Shares-outstanding data for the small-cap universe** — without it, P/E and P/B stay permanently
   uncomputable for exactly the tickers this matters most for (H-011's own sleeve), and the valuation
   stage of the staged pipeline can never discriminate.
2. **A genuinely larger sample of same-filing multi-fact implications** — the contradiction engine's
   only proven catch (§3, §8) is n=1; it needs materially more real cases (not synthetic ones) before
   its hit rate can be assessed with any confidence.

Until both exist, re-running this investigation on more data will not change the answer — it will
still be data-starved on the two dimensions that matter, not architecture-limited. No paper-shadow run
against live H-011 output is warranted yet (Phase 8's "if and only if" condition was not met); none was
performed beyond the read-only comparison in §8.
