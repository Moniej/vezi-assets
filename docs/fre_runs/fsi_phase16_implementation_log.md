# FSI Phase 16 — Implementation Log

*Per `docs/fre_runs/fsi_phase16_preregistration.md` and the owner's
standing continuous-execution authorization. Append-only.*

## Entry 0 — Confirmed the exact stale files via grep before touching anything

`test_company_memory_360.py`, `test_financial_reasoning_report.py`,
`test_company_thesis_360.py`, `test_entity_context.py`, `test_company_
research_dossier.py`, `test_generate_research_dossier.py` all hardcoded
`["UCAP", "BUAFOODS", "AFRIPRUD", "CAP", "NASCON"]` (or the equivalent
tuple). None had been touched since before Phase 13.

## Entry 1 — Fix: dynamic ticker discovery via `list_tickers()`

All 6 files: `tickers = [...]` replaced with `tickers = list_tickers(con)`
(importing the SAME function `financial_ratios.py` and every composition
module already uses internally). Ticker-specific hardcoded assertions
(NASCON's leverage flag, GTCO's rename, AFRIPRUD's margin compression)
were left untouched — only the loop-driving list became dynamic. Message
strings ("for all 5 tickers") updated to use `len(tickers)` / `f`-strings
rather than a re-hardcoded "10" that would itself go stale at the next
expansion.

## Entry 2 — Two real fixes needed beyond a pure find-and-replace

1. **`test_company_thesis_360.py`'s `EXPECTED_FIRED_CONCERNS` dict** (a
   hardcoded ground-truth map used to verify CORRECT integration, not
   just "runs without crashing") needed 5 new entries. Ground truth
   obtained via a direct SQL query of `financial_reasoning_conclusions`
   (never assumed from memory): MTNN, OANDO, and NESTLE each show
   `margin_compression` fired; DANGCEM and UBN show nothing fired.
2. **`test_entity_context.py`'s equivalence check** originally required a
   matching non-NULL `entities` row (`direct is None -> mismatch`) —
   correct for the original 5 tickers (all have a real `entities` row
   since Phase 9) but WRONG for the 5 Phase-13 tickers, none of which has
   one yet (a disclosed, deferred gap, not a defect). Fixed the test's
   own comparison logic so "both sides empty" (`direct is None AND ctx.
   entity_id is None`) counts as a correct match — `entity_context.py`
   itself (frozen) already returns `entity_id=None` for exactly this
   case ("no graph presence yet KNOWN"), the test's comparison was simply
   incomplete for a case that didn't exist before Phase 13.

## Entry 3 — Phase 5 harness Component 4 (composition-layer smoke coverage)

Added to `scripts/fre/fsi_phase5_validate_pipeline.py`: for every real
ticker (`list_tickers()`), runs `company_memory_360.as_of()` ->
`render_report()` -> `company_thesis_360.as_of()` -> `entity_context.
get_entity_context()` -> `company_research_dossier.build_dossier()`/
`render_dossier()`, confirming zero exceptions. Deliberately a coarse
smoke check only (no re-implementation of each phase's own detailed
equivalence/PIT assertions, which already live in their own dedicated
test files) — this is the platform-level check that would have caught
Phase 13's own generalization gap automatically, if it had existed
sooner.

**Component ordering fixed during implementation**: the database-
immutability check (Component 3) had to move to run AFTER the new
Component 4, not before it — otherwise Component 4's own reads would
happen outside the "before/after" window the immutability check
measures, making that check meaningless for anything Component 4 might
have done. Components 1/2's own logic is untouched; only the ordering
of when the "after" snapshot is taken changed.

## Entry 4 — Validation and full regression (complete)

All 6 updated test files re-run individually and pass in full (7+13+13+
13+14+9 = 69 assertions, all previously-passing assertions still pass,
now exercising 10 tickers instead of 5). Phase 5 harness re-run: all 4
components PASS, including the new Component 4 across all 10 tickers,
and Component 3 (immutability) now correctly covers the entire run.

Full regression: 26 test files (unchanged count -- no new test file was
added, 6 existing ones were fixed in place), all green. `check_db_
safety.py` PASS. `test_reasoning_pipeline.py` ALL CHECKS PASSED.

**No schema change. No modification to any production module's own
logic** (`company_memory_360.py`, `financial_reasoning_report.py`,
`company_thesis_360.py`, `entity_context.py`, `company_research_
dossier.py`, `generate_research_dossier.py`, `screening.py` all
untouched) — every fix was to test files' own ticker-discovery
mechanism, plus one additive Component 4 in the harness's own runner
script.

**FSI Phase 16 is now complete, validated, and documented.**
