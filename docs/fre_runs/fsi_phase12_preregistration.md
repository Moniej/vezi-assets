# FSI Phase 12 — Operational Research Dossier Generation (Pre-registration)

*Design only. No implementation, no new extraction, no LLM call, no
subjective inference, no valuation, no ranking, no portfolio logic, no
alpha, no scoring, no recommendation, no narrative generation. Per
instruction, written and frozen BEFORE any execution begins. Builds on
`fsi-phase11-baseline-2026-08-02` and modifies nothing in Phases 1-11 —
all eleven remain frozen, touched only for future bug fixes.*

## Review of the complete frozen architecture

**LIM**: unchanged since the last four reviews — still RB-3c-
interrupted, `self_critique_quality` still 0.0, not a candidate input
to anything.

**FRE track**: FRE-1 through FRE-6 frozen, unchanged.

**Knowledge Graph**: `entities` = 50 rows, `entity_relationships` = 5
rows (4 real `renamed_from`, populated Phase 9; 1 `effect_chains`
artifact), unchanged since Phase 10.

**FSI track, Phases 1-11**: 106 facts, 177 conclusions, five
composition layers (`CompanyMemory360`, `CompanyThesis360`,
`entity_context`, `CompanyResearchDossier`), all frozen.

**Reporting layer**: `render_report()` (Phase 7) and `render_dossier()`
(Phase 11) both exist, both tested, both produce complete,
deterministic, fully-cited Markdown. **The gap this review finds**:
neither has an operational entry point. Every one of this platform's
outputs — including the single most complete artifact it can produce,
`render_dossier()`'s output — is reachable only by writing Python that
imports `ngxrot.fre`, opens a database connection, and calls two
functions in order. There is no script, no command, nothing a
non-developer (or a developer without this session's own context) can
run to actually get a dossier for a ticker.

## Objective

Build one small, additive, read-only command-line script —
`scripts/fre/generate_research_dossier.py` — that wraps `build_
dossier()` and `render_dossier()` (Phase 11, called unmodified) behind
a simple interface: `--ticker TICKER --as-of DATE`, printing the
rendered dossier to stdout, with an optional `--output PATH` to also
write it to a file. No new capability is added; this operationalizes
one that already exists and is already fully validated.

## Rationale

Phases 1 through 11 built a complete, deterministic, fully-cited
research capability. None of it is usable today by anyone who is not
independently able to write and run Python against this project's own
database layer. This is the highest-leverage remaining gap under the
owner's own stated priorities: it directly serves **research
usability** (the capability becomes something an actual researcher can
run), **auditability** (a script with fixed, named arguments and
optional persisted output is itself a more auditable invocation pattern
than an ad hoc Python session), and, to a lesser extent, **institutional
robustness** (an operational entry point is what makes a research
capability something an institution can actually rely on, rather than
something that only works in the hands of whoever last touched the
code). It requires zero new reasoning, zero new data, and zero
modification to any frozen module — purely argument-parsing and a call
to two already-tested functions.

## Alternatives considered

1. **Extend Phase 5's validation harness to cover Phases 6-11 and the
   Knowledge Graph** (a golden-snapshot/cross-phase-consistency
   extension analogous to Phase 5's own design, but for the newer
   composition layers). A real, legitimate candidate, and the first one
   this review considered. Rejected as the PRIMARY choice for this
   phase, not as without merit: regression protection for Phases 6-11
   already substantially exists, distributed across each phase's own
   dedicated test file (`test_company_memory_360.py`, `test_
   company_thesis_360.py`, `test_entity_context.py`, `test_company_
   research_dossier.py`, `test_phase9_knowledge_graph.py` — 5 files, 61
   assertions, each asserting specific, real values), all of which run
   as part of the standing "full regression suite" discipline already
   required after every phase. The marginal value of also consolidating
   this into Phase 5's own golden-snapshot mechanism is real but lower
   than closing a capability that currently has ZERO coverage of any
   kind (this phase's own proposal). Also, extending Phase 5's own
   `pipeline_validation.py` would either modify a frozen module or
   require a second, parallel golden-snapshot artifact — a larger,
   higher-scope undertaking than the owner's own stated preference for
   integration over expansion favors right now. A future phase remains
   free to propose this on its own merits.
2. **A web or API interface for the dossier.** Rejected — substantially
   larger in scope (a serving layer, authentication considerations,
   deployment) for a research capability that today has exactly 5 real
   tickers and no stated multi-user requirement. A CLI script is the
   minimal viable operational interface; a service layer is a much
   later, separately-justified step if ever needed.
3. **A batch mode generating dossiers for all 5 tickers at once.**
   Considered as a small extension of the same script. Deferred, not
   rejected outright — the single-ticker interface is the minimal,
   correctly-scoped starting point (and matches every prior phase's own
   single-ticker-only guardrail); a `--all` flag could be added later
   as a thin, additive extension of this same script without changing
   its core logic, but is not proposed as part of THIS phase to keep
   the change small and reviewable.
4. **Do nothing — leave the dossier reachable only via direct Python
   calls.** Rejected — this is precisely the gap Section "Rationale"
   above identifies as the platform's own highest-leverage remaining
   item; leaving it unaddressed means eleven phases of validated
   research capability remain operationally unusable outside a
   development session.

## Dependencies

`fsi-phase11-baseline-2026-08-02` (`build_dossier()`/`render_dossier()`,
called unmodified). `db.py`'s existing connection helpers (read-only
connection pattern, matching every prior FSI script's own convention).
No new schema, no new table, no new fact, no new module beyond the one
script itself.

## Risks

- **Output-file risk**: the optional `--output PATH` flag writes a
  file, which is a real write — but to a user-specified file path
  outside the database, never to `data/ngx.sqlite` itself. This must be
  disclosed precisely in the script's own help text and in this
  document's success criteria, not conflated with "zero database
  writes" (which remains true; "zero writes" more broadly does not,
  when `--output` is used).
- **Ticker/date validation risk**: an invalid ticker or a malformed
  date passed on the command line must fail clearly and honestly (e.g.,
  `build_dossier()`'s own existing behavior for an unknown ticker, or a
  clear argument-parsing error) rather than crash with an unhelpful
  traceback or, worse, silently produce a misleading empty-looking
  report.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual
  intent — flagged explicitly, redirection expected if wrong.

## Success criteria

- Running `scripts/fre/generate_research_dossier.py --ticker TICKER
  --as-of DATE` for all 5 real tickers at their own latest real filing
  dates produces output identical to calling `build_dossier()`/`render_
  dossier()` directly in Python — verified by direct comparison, not
  assumed.
- `--output PATH` writes the identical text to the given file, and
  nothing else; without `--output`, the script writes to stdout only,
  no file of any kind.
- The production database (`data/ngx.sqlite`) is unchanged after any
  invocation of this script, with or without `--output` — confirmed
  directly, matching the row-count/`integrity_check`/`foreign_key_
  check` verification convention used in every prior phase.
- An invalid ticker or malformed date produces a clear, honest error
  message, never a crash with a raw traceback and never a fabricated or
  misleadingly-empty report.

## Failure criteria

- Any discrepancy between the script's own output and calling `build_
  dossier()`/`render_dossier()` directly.
- Any write to `data/ngx.sqlite` under any invocation, with or without
  `--output`.
- Any modification to `company_research_dossier.py` or any other frozen
  module.

## Implementation boundaries

**In scope**: one new script (`scripts/fre/generate_research_dossier.
py`) with `--ticker`/`--as-of`/`--output` arguments; its own test file
(comparing script output against direct Python calls, and confirming
database immutability); documentation. **Out of scope, explicitly**:
any modification to `company_research_dossier.py`, `company_thesis_
360.py`, `entity_context.py`, `company_memory_360.py`,
`company_thesis.py`, or `financial_reasoning_report.py`; any new fact,
ratio, trend, flag, entity, or relationship; any batch/`--all` mode;
any web/API/service layer; any new reasoning, scoring, ranking,
recommendation, valuation, or portfolio output of any kind; any LLM
call.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this correctly
identifies the intended next step — must be reviewed and approved
before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
