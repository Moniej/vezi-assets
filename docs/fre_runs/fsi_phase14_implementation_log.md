# FSI Phase 14 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase14_preregistration.md` and the
owner's continuous-execution operating-mode instruction. Append-only.*

## Entry 0 — Real fields used, not the ones Part 9's original example imagined

Confirmed by direct grep that `company_thesis.py`/`company_thesis_360.py`
never implemented the `financial_quality`/`growth_quality`/`capital_
allocation_quality` fields Part 9's own screening example named — the
real, later-built design (Phase 5/8) uses `concern_evidence`/
`supplementary_evidence` from fired health flags and trend directions
instead. Screening was built against the REAL schema (`financial_
reasoning_conclusions`' `metric`/`conclusion_type`/`status`/`value_text`
columns, reached via Phase 4's `pit_financial_memory.as_of()`), not the
hypothetical fields — disclosed per the pre-registration's own Section 1.

## Entry 1 — `src/ngxrot/fre/screening.py`

Two functions: `screen_by_flag(con, flag_metric, fired, as_of_date)` and
`screen_by_trend(con, metric, direction, as_of_date)`. Both iterate over
`financial_ratios.list_tickers()` (already proven across Phase 3-13, now
10 tickers), call Phase 4's `pit_financial_memory.as_of(ticker, as_of_
date)` per ticker (PIT-safety inherited, not re-implemented), and filter
to conclusions matching the given categorical criterion. Results always
returned in alphabetical-ticker order (`sorted(list_tickers(con))` drives
iteration order directly, not a post-hoc sort). An unrecognized
`flag_metric`/`metric`/`direction` raises `ValueError` rather than
silently returning an empty list — an empty result must always mean "no
real match," never "the caller mistyped a name."

`KNOWN_FLAG_METRICS` (3 real flag names) and `KNOWN_TREND_METRICS` (12
base fact types + 5 ratio metrics) are both derived directly from the
real, already-frozen Phase 3 modules' own constants (`BASE_FACT_TYPES`,
`RATIO_DEFINITIONS`) — not a separately-maintained, driftable list.

## Entry 2 — Guardrail design, enforced not just documented

Per the pre-registration's Section 5: neither function accepts a numeric
threshold, `limit`, `top_n`, `sort_by`, `rank_by`, or `weight` parameter
— mechanically checked via `inspect.signature()`. `ScreenMatch` (the
result dataclass) carries no score/rank/weight/strength/priority field —
mechanically checked via dataclass-field introspection. No aggregate
statistic is ever computed (each match is an independent row). Confirmed
via AST-based import inspection (not a naive substring match, which would
have false-positived on this module's own docstring legitimately naming
`alpha_engine.py` in prose) that `screening.py` imports neither
`alpha_engine` nor `runner`, and that `alpha_engine.py` does not import
`screening` — the one-directional non-boundary confirmed both ways.

## Entry 3 — Validation and full regression (complete)

`scripts/fre/test_screening.py` (17/17): correctness verified against a
direct SQL query of `financial_reasoning_conclusions` for both functions
(not just internal self-consistency) — `screen_by_flag('leverage_
increasing', fired=True)` at a far-future date matches every real fired
instance across all 10 tickers; `screen_by_trend('net_profit',
'decreasing')` correctly includes MTNN's real FY2024 decline. PIT
correctness confirmed at NASCON's own real boundary (its `leverage_
increasing` conclusion's latest source fact filed 2026-03-03): not
screenable 2026-03-02, screenable exactly on 2026-03-03 — reusing Phase
4's own established day-before/day-of boundary-testing pattern. All 3
unrecognized-value cases raise `ValueError`. Ordering, no-ranking-
parameter, no-score-field, and import-boundary guardrails all confirmed.
Zero database writes across the entire test run.

Full regression: 24 test files (was 23), 350 assertions (333 + 17), all
green. `check_db_safety.py` PASS. `test_reasoning_pipeline.py` ALL CHECKS
PASSED. Phase 5's own `fsi_phase5_validate_pipeline.py` harness re-run:
golden-snapshot reproducibility PASS (137 facts, 267 conclusions,
UNCHANGED — this phase adds a pure read-only module, no new fact or
conclusion), cross-phase consistency PASS (0 violations), database
immutability PASS (all 29 tables unchanged).

**No schema change. No modification to any of the fourteen frozen FSI
modules this phase draws from** (`financial_ratios.py`, `pit_financial_
memory.py`, `trend_classification.py`, `financial_health_flags.py`).

**FSI Phase 14 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline.
