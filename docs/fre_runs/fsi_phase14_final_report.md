# FSI Phase 14 — Final Report

*Evidence-Based Screening. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase14_implementation_log.md`; this report
summarizes outcomes.*

## Executive summary

FSI Phase 14 built `src/ngxrot/fre/screening.py` — the platform's first
function that legitimately operates across ALL tickers at once, closing
a gap Part 9 of the frozen FRE architecture (`docs/fre/
09_portfolio_reasoning.md`) named and authorized over a week before FSI's
extraction/reasoning tracks existed to feed it. Every prior research
object (Company Memory, Thesis, Dossier, CLI) requires already knowing
which ticker to look up; with the roster now at 10 tickers (Phase 13),
that gap is materially more costly than it was at 5. Screening answers
"which companies currently show evidence of X?" without per-ticker
lookup — `screen_by_flag()` for health-flag status, `screen_by_trend()`
for trend direction — both pure, read-only filters over already-computed,
PIT-safe conclusions, never a new claim, score, or ranking.

## Files created (deliverables)

- **`src/ngxrot/fre/screening.py`** (new): `screen_by_flag()`,
  `screen_by_trend()`, `ScreenMatch` dataclass.
- **Tests**: `scripts/fre/test_screening.py` (17 assertions).
- **Documentation**: this report, the implementation log, and the
  pre-registration.

**No schema change. No modification to any frozen module.**

## Requirement-by-requirement results

- **Correctness vs. a direct SQL query (not just internal self-
  consistency)**: confirmed for both functions across all 10 tickers.
- **PIT correctness**: confirmed at a real boundary — NASCON's own
  `leverage_increasing` flag is not screenable the day before its
  conclusion's latest source fact was filed, and is screenable exactly
  on that date.
- **Zero database writes, zero LLM calls, zero schema change**: confirmed.
- **Guardrails hold**: neither function accepts a numeric threshold,
  limit, sort, or rank parameter; results are always in alphabetical-
  ticker order; the result dataclass carries no score/rank/weight field;
  the module neither imports `alpha_engine.py`/`runner.py` nor is
  imported by them (verified via AST inspection in both directions, not
  a naive substring match).
- **Unrecognized filter values raise, never silently return empty**:
  confirmed for flag name, trend metric, and trend direction.

## Design decisions, disclosed

- **Categorical filters only — no numeric threshold.** A "screen for
  margin below X%" style filter is a real, common finance use case, but
  it introduces exactly the kind of value-based cutoff that could
  function as an implicit score. This phase deliberately restricts
  filtering to values Phase 3 already classified categorically (a
  flag's fired/not-fired boolean, a trend's increasing/decreasing/stable
  direction) — the conservative choice, consistent with the standing
  "boring correctness over impressive speculation" instruction. Any
  future numeric-threshold screen would need its own separate
  pre-registration and risk analysis.
- **Part 9's own screening example cited fields that were never actually
  built** (`CompanyThesis.financial_quality`/`.growth_quality`/
  `.capital_allocation_quality`) — confirmed by direct grep before
  building anything. Screening was built against the real schema
  instead, a disclosed correction in the same style as Phase 9's own
  `relation_taxonomy.toml`/`documents.raw_symbol` corrections.
- **Portfolio-memory cross-reference (Part 9's OTHER Tier-1 item, which
  reads `alpha_engine.py`'s live sleeve) was deliberately NOT built in
  this phase** — kept out to hold this phase's risk surface to a single
  new boundary (cross-ticker read within the FSI track's own data), not
  two. A future, separately-scoped phase could add it.

## Validation results

24 test files (was 23), 350 assertions, all passing. `check_db_safety.py`
PASS. `test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5's own `fsi_
phase5_validate_pipeline.py`: golden-snapshot reproducibility PASS (137
facts, 267 conclusions — unchanged, since this phase adds no new fact or
conclusion); cross-phase consistency PASS; database immutability PASS.

## Known limitations

- **Numeric-threshold screening is out of scope** — deliberately, per the
  design decision above, not an oversight.
- **Watchlist persistence (Part 9's other Tier-1 item) is not built** —
  Screening is stateless; a researcher's query results are not saved
  anywhere. A future phase could add a `WatchlistEntry` table if wanted.
- **No CLI entry point for Screening yet** — reachable only via direct
  Python calls, the same gap Phase 12 closed for the single-ticker
  dossier. A thin CLI wrapper would be a natural, low-risk follow-on.

## Recommendations for the next phase

1. A CLI wrapper for Screening (mirroring Phase 12's `generate_research_
   dossier.py` pattern) would close the same "reachable only via Python"
   gap Phase 12 closed for the dossier — a natural, low-risk follow-on.
2. Portfolio-memory cross-reference (Part 9's other Tier-1 item, reading
   `alpha_engine.py`'s live sleeve) is a legitimate next step, kept out
   of this phase to isolate its own distinct risk surface.
3. Continue the standing discipline: no numeric-threshold screening, no
   aggregate statistic, no ranking, in any future extension of this
   module.

---

**FSI Phase 14 is complete: fully implemented, validated, and
documented.** Per the owner's continuous-execution operating mode,
proceeding to commit and tag this baseline.
