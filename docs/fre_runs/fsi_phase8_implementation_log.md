# FSI Phase 8 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase8_preregistration.md`
(approved, with the owner's added implementation-boundary constraints)
and the owner's implementation instruction. Append-only.*

## Entry 0 — Design refinement before coding: no polarity judgment for trends

The pre-registration's own Section 5 loosely described folding "every
fired flag and every trend direction" into bull/bear evidence. Before
writing code, this is narrowed, deliberately more conservatively than
pre-registered (never less): **trends are NOT assigned a bull/bear
polarity in this phase.** Reason: Phase 3's own design (`docs/fre_runs/
fsi_phase3_preregistration.md` Area 2) explicitly committed trend
classification to neutral vocabulary — "states the mechanical direction
only, and does NOT infer whether a direction is favorable" — precisely
because favorability depends on the metric (rising revenue and rising
leverage are not symmetric) and assigning it would be exactly where a
valuation/alpha-adjacent judgment starts to leak in. Inventing a
per-metric polarity table now, in Phase 8, would be a NEW judgment this
program has never authorized.

By contrast, **all 3 of Phase 3's financial-health flags
(`leverage_increasing`, `margin_compression`, `cash_flow_earnings_
divergence`) were themselves DESIGNED as risk/concern checks** — Phase
3's own pre-registration frames them as flags for potential concerns,
never as positive signals. Categorizing a FIRED flag as bear-case-
relevant evidence restates what Phase 3 already established these
flags mean by design; it introduces no new judgment.

**Resulting design**: two evidence categories, not three:
- `concern_evidence`: fired risk flags only (bear-case-relevant, by
  Phase 3's own flag design).
- `supplementary_evidence`: everything else FSI produces (all ratios,
  all trends, not-fired flags, insufficient_data flags) — neutral,
  informational, no polarity assigned.

This is a stricter reading of the owner's own "must not introduce...
weighting... balancing algorithms" constraint than the pre-
registration's looser wording implied, and is disclosed here as a
deliberate, conservative refinement rather than silently narrowing scope.

## Entry 1 — Implementation (complete)

`src/ngxrot/fre/company_thesis_360.py` implements `as_of(con, ticker,
as_of_date) -> CompanyThesis360`: calls `build_company_thesis()`
(FRE-5) and `company_memory_360.as_of()` (Phase 6) unmodified, then
mechanically partitions the financial conclusions already present in
the Phase 6 snapshot into `concern_evidence` (fired risk flags only)
and `supplementary_evidence` (everything else — ratios, trends,
not-fired flags, insufficient_data flags). No new query beyond the two
calls to the frozen modules; no new fact, no new inference.

**Real, sanity-checked integration on all 5 anchor companies** (before
writing formal tests): NASCON's `leverage_increasing` and AFRIPRUD's
`margin_compression` correctly appear as `concern_evidence`; UCAP, CAP,
and BUAFOODS correctly show empty `concern_evidence` (no real fired
flag exists for any of them) — matching Phase 3's own real, frozen flag
results exactly.

## Entry 2 — Validation (complete)

`scripts/fre/test_company_thesis_360.py` (13/13):

1. **Output equivalence, `thesis` sub-result**: exactly equal to
   calling `build_company_thesis()` directly, for all 5 tickers — true
   regardless of whether FSI concern evidence exists, which is exactly
   how the pre-registration's "prove equivalence where no FSI evidence
   exists" requirement is satisfied: 3 of the 5 real tickers (UCAP, CAP,
   BUAFOODS) have zero concern evidence today and their `thesis`
   sub-result still matches exactly, by construction (the composition
   never touches `thesis` regardless of what FSI evidence exists).
2. **Output equivalence, `memory` sub-result**: exactly equal to calling
   `company_memory_360.as_of()` directly, for all 5 tickers.
3. **Correct integration verified against real, known values**: `concern_
   evidence` exactly matches the real fired flags per ticker (not just
   "produces some output") — NASCON/`leverage_increasing`, AFRIPRUD/
   `margin_compression`, and empty for the other 3.
4. **Completeness + non-overlap**: every financial conclusion in each
   snapshot is categorized into EXACTLY ONE of the two evidence lists —
   verified via set operations (union equals the full conclusion set,
   intersection is empty), not spot-checked.
5. **Trend-exclusion from concern evidence verified mechanically**:
   confirms Entry 0's design refinement actually holds in code, not just
   in the docstring.
6. **No synthesized field of any kind**: `CompanyThesis360`'s own 6
   dataclass fields and `FSIEvidenceItem`'s own fields checked by direct
   introspection — no strength/score/weight/rank/vote/balance field
   exists anywhere.
7. **Individual auditability**: every folded evidence item's `method`/
   `limitations`/`confidence_tier` matches its source conclusion exactly,
   verified by direct comparison against the conclusion it was built
   from — not merely "some text is present."
8. **Single-ticker-scope guardrail**, same style as Phases 3-7.
9. **Database immutability**: all 29 tables, `integrity_check`, and
   `foreign_key_check` unchanged/clean before and after the full test
   run.

No architectural blocker was encountered — the composition pattern
established in Phase 6 (compose over two frozen modules, touch neither)
applied cleanly one layer up, over `CompanyThesis` and `CompanyMemory360`.

## Entry 3 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, every prior FSI Phase 1-7 test file unchanged and
passing (13 files, 178 assertions), plus the new `test_company_
thesis_360.py` (13/13), FRE-2 29/29, FRE-3 16/16, FRE-4 16/16, FRE-5
21/21, FRE-6 40/40 (unchanged). Phase 5's own `fsi_phase5_validate_
pipeline.py` harness re-run and still reports PASS on all three
components, confirming Phase 8 did not disturb the golden snapshot or
cross-phase consistency.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` (11,533),
`extracted_facts` (267), and `financial_reasoning_conclusions` (177) row
counts all unchanged. Zero schema changes — no `CREATE TABLE`/`ALTER
TABLE` statement exists anywhere in this phase's code.

**FSI Phase 8 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline per the owner's
instruction.
