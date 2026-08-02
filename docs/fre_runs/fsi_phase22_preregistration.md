# FSI Phase 22 — Pre-registration

*Portfolio-Context Dossier CLI. Per the owner's standing continuous-
execution authorization: gap identified, alternatives considered,
implemented without an approval checkpoint.*

## Gap identified

Phase 20 built `company_portfolio_context.py`'s `as_of()`/`render()` —
the annotated dossier combining Phase 11's research dossier with
watchlist status and portfolio-memory cross-reference — but, exactly
like every "build" phase's own pattern on this platform (Screening:
Phase 14 build → Phase 15 CLI; Research dossier: Phase 11 build →
Phase 12 CLI), it shipped with no command-line entry point. An
operator today can only reach Phase 20's output by writing Python.
Both Phase 20's and Phase 21's own final reports named this
explicitly as the live next candidate.

## Why this is the single highest-leverage gap right now, over the alternatives considered

A fresh review of the whole platform this phase (not just Part 9)
surfaced one other real candidate — a new financial-health flag
(e.g., "cash-flow-generation-deteriorating," using already-computed
`cfo`/`fcf`-family trend conclusions instead of extracting anything
new) — investigated and set aside; see below for why. Weighed against
that, this phase's CLI wrapper wins on leverage-per-unit-risk: it is a
pure read-only wrapper (the platform's lowest-risk category), requires
zero new analytical logic, and closes a gap named twice by name in
already-committed final reports, rather than a gap this phase itself
is the first to propose.

## Alternatives considered and rejected

1. **A new financial-health flag using an under-used already-computed
   trend metric** (`cfo`, `cfi`, `cff`, or `fcf`), as a genuinely new
   4th rule alongside Phase 3's three. Investigated first this phase
   by querying real `financial_reasoning_conclusions` data directly:
   `fcf` has **zero** computed trend conclusions on the real database
   today (never extracted with enough periods for any ticker); `cfo`/
   `cfi`/`cff` each have exactly **one**. A flag built on this data
   would be `insufficient_data` for effectively every real ticker —
   architecturally honest (matching this platform's "unknown stays
   unknown" discipline) but a far weaker "real, tested, currently
   useful" capability than this phase's CLI, which is fully exercised
   by all 10 real FSI tickers today. Rejected FOR NOW, not
   permanently — recorded as a live candidate for a future phase, once
   more `cfo`/`cfi`/`cff`/`fcf` periods exist (a natural side effect of
   any future coverage-expansion round, should one ever be justified
   on its own separate merits).
2. **Extending Phase 3's `margin_compression` rule to also check
   `ebit_margin`** (which does have 10 real computed trend
   conclusions today, unlike `fcf`). Rejected — this would be widening
   an EXISTING rule's coverage, not adding a new analytical category
   (EBIT margin sits in the same "margin compression" concept family
   as the two margins the rule already checks), which reads as
   coverage-expansion-in-disguise rather than genuinely new
   capability, and — more importantly — `financial_health_flags.py` is
   a frozen module (named explicitly in Phase 13's own list of frozen
   library code); modifying its rule set would break this platform's
   standing discipline of never editing an already-tagged frozen
   module.
3. **Writing a brand-new flag type to `financial_reasoning_
   conclusions`** in this same phase (compute + write + re-freeze the
   golden snapshot), rather than a read-only CLI. Rejected as
   over-scoped for one phase given point 1's data-thinness finding —
   this platform's own precedent (Phase 17 build → Phase 20 wiring;
   Phase 18 build → Phase 21 CLI) is to separate "compute, read-only"
   from "persist to the database," each its own phase, keeping one
   dimension of risk at a time.
4. **Coverage expansion round 2**, reconsidered again this phase and
   rejected again for the same reason as Phases 19/20/21's own review:
   not a new capability, belongs on the eventual final audit's
   optional-enhancements list.

## Design

- New script `scripts/fre/generate_portfolio_context_dossier.py`,
  mirroring Phase 12's `generate_research_dossier.py` exactly:
  `--ticker`, `--as-of`, optional `--output`; UTF-8 stdout/stderr;
  `mode=ro` connection (read-only, no write path — unlike Phase 21's
  CLI, this one touches nothing write-capable, since
  `company_portfolio_context.py` itself has none); ticker-existence
  check before calling `as_of()`; malformed-date check with a custom
  error message, exit code 1.
- Calls `company_portfolio_context.as_of()` and `.render()`,
  unmodified, exactly once each.

## Guardrails (mechanically verified, not just asserted)

- Real subprocess invocation (matching Phase 12/15's own test
  convention), output compared for exact equivalence against calling
  `as_of()`/`render()` directly, for both AFRIPRUD (not in the live
  sleeve, not on the watchlist) and CAVERTON (confirmed in the live
  H-011 sleeve today).
- Unknown ticker, malformed date, and missing required argument each
  produce a clear error and non-zero exit code, never a raw traceback.
- Zero database writes across the entire test run (row-count diffing
  before/after, matching every prior CLI test's own discipline).
- Confirmed `company_portfolio_context.py` is byte-for-byte unchanged
  (`git diff --stat`) after this phase.

## Expected outcome

A new, additive, read-only operator tool; no schema change; no
modification to any frozen module. Both of Part 9's built-and-wired
composition views (the base research dossier and this session's
portfolio-annotated one) are now equally reachable from the command
line.
