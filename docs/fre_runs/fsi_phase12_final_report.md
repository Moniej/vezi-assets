# FSI Phase 12 — Final Report

*Operational Research Dossier Generation. Prepared per the owner's
instruction on completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase12_implementation_log.md`; this report
summarizes outcomes.*

## Executive summary

FSI Phase 12 built `scripts/fre/generate_research_dossier.py` — the
platform's first real operational entry point. Eleven prior phases
built a complete, validated, fully-cited research capability reachable
only through direct Python calls; this phase makes it something an
actual user can run: `--ticker TICKER --as-of DATE`, with an optional
`--output PATH`. Zero new reasoning, zero new data, zero database
writes. Two real bugs were found and fixed during implementation and
testing — both are genuine "first time this boundary was exercised"
findings, not defects in any of the eleven prior phases' own logic.

## Files created (deliverables)

- **generate_research_dossier.py**: `scripts/fre/
  generate_research_dossier.py`.
- **Tests**: `scripts/fre/test_generate_research_dossier.py` (9
  assertions, run against the real CLI as a subprocess, not just the
  underlying Python functions).
- **Documentation**: this report plus the implementation log.
- **Implementation log**: `docs/fre_runs/fsi_phase12_implementation_log.md`.

**No schema change. No modification to `company_research_dossier.py`
or any other frozen module.**

## Requirement-by-requirement results

- **Script output matches `build_dossier()`/`render_dossier()` called
  directly, for all 5 real tickers**: confirmed via a real subprocess
  invocation compared against a direct in-process call, byte-for-byte.
- **`--output` writes the identical text to the given file, stdout
  still shows the same content**: confirmed directly.
- **Zero database writes, with or without `--output`**: confirmed — all
  29 tables' row counts, `integrity_check`, and `foreign_key_check`
  unchanged before and after the full test run, including every CLI
  invocation.
- **Unknown ticker / malformed date produce a clear, honest error, no
  crash**: confirmed — both produce exit code 1, a specific error
  message, and no Python traceback.

## Two real bugs found and fixed, disclosed in full

1. **Console encoding (`UnicodeEncodeError`)**: BUAFOODS's real filing
   text contains the literal Naira currency sign (U+20A6). A subprocess
   launched under Windows' default console codepage (`cp1252`) cannot
   `print()` it. This is the first time any phase in this program
   exercised a genuine subprocess/console boundary — all eleven prior
   phases' own tests called rendering functions directly in-process,
   inheriting whatever encoding the test harness already used, so this
   failure mode could not have surfaced earlier. Fixed by forcing UTF-8
   on the script's own `sys.stdout`/`sys.stderr` via `reconfigure()`.
2. **Mojibake in the test's own subprocess capture**: after fixing (1),
   the test itself showed corrupted characters (`â€”` in place of `—`)
   even though the child process's bytes were correct UTF-8. Root
   cause: `subprocess.run(..., text=True)` without an explicit
   `encoding=` argument decodes the child's stdout using the OS
   locale's default (`cp1252`), not the encoding the child actually
   wrote in. Confirmed precisely via a byte-level file diff, not
   guessed. Fixed by passing `encoding="utf-8"` explicitly to
   `subprocess.run()` in the test's own helper.

Both findings are disclosed in full because they are genuine, and
because they illustrate a real, general lesson: testing a capability
in-process (as every prior phase's own test suite did) does not
exercise the same code paths as testing it through a real subprocess/
console boundary — a distinction worth carrying into any future phase
that adds another real operational entry point.

## Validation results

`test_generate_research_dossier.py` (9/9): script-vs-direct-call
equivalence for all 5 tickers via real subprocess invocation;
`--output` file-write correctness; no-file-written-without-`--output`;
clean error handling for an unknown ticker, a malformed date, and a
missing required argument; full database immutability across the
entire test run. Full regression suite: all 17 prior FSI Phase 1-11
test files (232 assertions) plus the new 9-assertion test file, plus
`check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
FRE-6 (all unchanged, FRE-6 still 40/40). Phase 5's own validation
harness re-run after implementation and still reports PASS on all
three components.

## Known limitations

- **Single-ticker only, Markdown only** — no batch/`--all` mode, no
  other output format, by design (deferred, not rejected, per the
  pre-registration's own Alternative 3).
- **No web/API interface** — a CLI is the minimal viable operational
  entry point for a 5-ticker research capability; a service layer
  remains a much later, separately-justified step if ever needed.
- **The console-encoding fix is scoped to this script only** — any
  future CLI entry point built on top of `render_report()`/`render_
  dossier()`'s own text output should apply the same `reconfigure()`
  pattern, not assume it is inherited automatically.

## Recommendations for the next phase

1. If a batch/`--all` mode is ever wanted, add it as a thin, additive
   extension of this same script (not a rewrite) — the single-ticker
   core logic (`build_dossier()`/`render_dossier()`) needs no change.
2. Any future CLI entry point should apply the same UTF-8
   `reconfigure()` pattern from the start, and any test harness for it
   should pass `encoding="utf-8"` explicitly to `subprocess.run()` —
   both lessons from this phase's own two real findings.
3. Continue the standing discipline: any future capability remains
   subject to the same exclusions restated across all twelve approvals
   — no alpha, ranking, scoring, valuation, or unsupported conclusion.

---

**FSI Phase 12 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
