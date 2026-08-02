# FSI Phase 11 — Complete Institutional Research Dossier (Pre-registration)

*Design only. No implementation, no new extraction, no LLM call, no
subjective inference, no valuation, no ranking, no portfolio logic, no
alpha, no scoring, no narrative generation. Per instruction, written
and frozen BEFORE any execution begins. Builds on
`fsi-phase10-baseline-2026-08-02` and modifies nothing in Phases 1-10 —
all ten remain frozen, touched only for future bug fixes.*

## 1. Review of the complete platform architecture — LIM, FRE, FSI, Knowledge Graph

**LIM**: unchanged since the last three reviews — still RB-3c-
interrupted, `self_critique_quality` still 0.0, not a candidate input to
anything.

**FRE track**: FRE-1 through FRE-6 frozen, unchanged.

**FSI track + Knowledge Graph, the concrete state this review finds**:
five composition layers now exist over the FSI track's validated data —
`CompanyMemory360` (Phase 6: corporate memory + financial reasoning),
`CompanyThesis360` (Phase 8: `CompanyThesis` + `CompanyMemory360`,
adding concern/supplementary FSI evidence), and `entity_context`
(Phase 10: knowledge-graph identity/lineage + `CompanyMemory360`). But
only ONE presentation layer exists — `financial_reasoning_report.py`'s
`render_report()` (Phase 7) — and it renders **only** the original
`CompanyMemory360`. **Neither Phase 8's thesis evidence nor Phase 10's
graph context has ever been rendered into human-readable form.** The
one artifact in this entire platform actually meant for a human
researcher to read is now two phases behind what the platform has
actually built and validated.

## 2. The single highest remaining capability gap

**Extend the presentation layer to cover everything the composition
layers have built: render `CompanyThesis`'s bull/bear/base case
alongside its FSI concern/supplementary evidence (Phase 8), and the
ticker's own knowledge-graph identity and relationship lineage
(Phase 10), in one comprehensive, deterministic, fully-cited research
document — reusing Phase 7's own `render_report()` for the parts it
already covers, never reimplementing them.**

## 3. Why this should happen now, not later

This gap is not hypothetical or speculative — it is the direct,
mechanical consequence of the last two approved phases succeeding. Each
additional phase built on `CompanyMemory360` without a matching update
to the one presentation layer makes the eventual gap larger: today it
is two objects (`CompanyThesis360`, `entity_context`); left alone
through a hypothetical Phase 12, it would be three, and so on. Closing
it now, while the gap is small, concrete, and fully specified, is
cheaper and lower-risk than closing it after more composition layers
accumulate on top of an increasingly incomplete report. This is the
same "close it while it's small" reasoning that motivated Phase 9
(entities) and Phase 10 (graph context) — each closed a gap the
immediately preceding phase had just created.

## 4. Objective

Build `CompanyResearchDossier` — a new, additive composition combining
`build_company_thesis()` (FRE-5), `company_memory_360.as_of()`
(Phase 6), and `get_entity_context()` (Phase 10) for one ticker, calling
each exactly once (avoiding Phase 8/10's own internal duplicate calls to
`company_memory_360.as_of()` by flattening rather than nesting) — and a
new rendering function, `render_dossier()`, that reuses Phase 7's
`render_report()` verbatim for the `CompanyMemory360` portion and
appends two new, equally deterministic sections: **Investment Thesis
Evidence** (bull/bear/base case, plus Phase 8's concern/supplementary
evidence, each fully cited) and **Knowledge Graph Context** (entity
identity, and any real relationships, per Phase 10's own fields,
verbatim).

## 5. Research question

Can Phase 7's own presentation discipline (fixed section ordering, no
forbidden vocabulary, explicit missing-data disclosure, sentence-to-
field traceability, full determinism) be extended to two additional,
independently-built evidence sources without any loss of that
discipline — i.e., does composing three presentation-worthy objects
into one document introduce any new judgment, or does it remain pure
templating throughout?

## 6. Architectural rationale

This is the fourth application of the same composition pattern
established in Phase 6, extended in Phase 8 and Phase 10: compose over
already-frozen, already-tested modules, touch none of them. The
rendering half extends Phase 7's own precedent identically — call the
existing `render_report()` rather than reimplementing its logic, then
append new sections built with the exact same discipline (fixed,
disclosed ordering; explicit confidence-tier/limitations preservation;
mechanical forbidden-vocabulary avoidance). Nothing here is a new kind
of capability; it is the union of four already-approved ones.

## 7. Alternatives considered — the full remaining roadmap, each re-confirmed or newly addressed

1. **Reasoning-mode rollout (FRE-8)**: unchanged since Phase 9/10's own
   review — the classification half is mechanical but touches a very
   small real dataset (18 facts); the enforcement half needs the
   standing LLM/cost decision. Rejected, same reasoning as before.
2. **Cross-document reasoning**: still blocked on a new external data
   source. Rejected, unchanged.
3. **Multi-source evidence fusion**: still fully covered by the
   existing `corroborates_implication_id`/`contradicts_implication_id`
   mechanism, already surfaced in `CompanyThesis`. Rejected, unchanged.
4. **Event reasoning**: still blocked — `events.ticker` remains 0/157
   populated (re-confirmed, not re-derived from memory). Rejected,
   unchanged.
5. **Macro reasoning**: still blocked — requires new extraction per
   Part 2's own design. Rejected, unchanged.
6. **Sector reasoning**: still blocked — `securities.sector_ngx`
   remains 0/320 populated (re-confirmed). Rejected, unchanged.
7. **Valuation activation (FRE-7)**: still the most explicitly and
   repeatedly excluded category in this program. Rejected, unchanged.
8. **Portfolio reasoning**: still the standing exclusion, still
   dependent on a `CompanyThesis` layer whose own real evidence base
   only just began growing in Phase 8. Rejected, unchanged.
9. **Narrative generation**: still subjective inference by definition.
   Rejected, unchanged.
10. **Further knowledge graph expansion**: still blocked for the one
    zero-inference candidate (`index_membership`, confirmed 100%
    synthetic in Phase 10's own review); every other unbuilt part of
    Part 2 needs new extraction. Rejected, unchanged.
11. **Modify `render_report()` (Phase 7) directly to add the new
    sections**, rather than building a new composition and a new
    rendering function. Rejected — Phase 7 is frozen, touched only for
    bug fixes per standing instruction; a new function that calls the
    old one is the only option consistent with that constraint, exactly
    the same reasoning Phase 8 and Phase 10 already applied to their
    own underlying modules.
12. **Wait for a future phase to add a third or fourth composition
    object before addressing the reporting gap all at once.**
    Rejected — this is precisely the "let the gap grow" alternative
    Section 3 argues against; closing it now, at two objects, is
    lower-risk than closing it later at three or more.

## 8. Dependencies

`fsi-phase10-baseline-2026-08-02` in full. `build_company_thesis()`
(FRE-5), `company_memory_360.as_of()` (Phase 6), `get_entity_context()`
(Phase 10), and `render_report()` (Phase 7) — all called, none forked
or modified. No new schema, no new table, no new fact.

## 9. Risks

- **Duplicate-computation risk**: naively composing `CompanyThesis360`
  and `entity_context.as_of()` together (each of which independently
  calls `company_memory_360.as_of()`) would compute the same memory
  snapshot twice and risk two subtly different code paths drifting
  apart over time — mitigated by calling the three LEAF functions
  (`build_company_thesis`, `company_memory_360.as_of`,
  `get_entity_context`) directly, once each, rather than nesting
  Phase 8/10's own composed objects inside a new one.
- **Section-ordering risk**: appending two new sections could tempt an
  ordering that implies relative importance (e.g., always putting
  "concern evidence" first) — mitigated by a disclosed, fixed order
  (Corporate Memory → Financial Reasoning → Investment Thesis Evidence
  → Knowledge Graph Context), matching Phase 7's own neutral-ordering
  discipline.
- **Low graph-context yield remains true here too**: as in Phase 10,
  4 of 5 tickers will show no knowledge-graph relationships in the
  rendered dossier — correct, not a defect, disclosed explicitly in the
  rendered output itself (mirroring Phase 7's own "never hide missing
  data" rule).
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 10. Success criteria

- `render_dossier()` produces output for all 5 real tickers with zero
  exceptions.
- The `CompanyMemory360`-derived portion of the output is byte-
  identical to calling `render_report()` directly on the same snapshot
  (proving reuse, not reimplementation).
- Every Phase 8 concern/supplementary evidence item and every Phase 10
  relationship appears in the rendered output, each with its own
  citation (`conclusion_id`/`relationship_id`), `confidence_tier`/
  `confidence`, and limitations/provenance fields intact.
- Mechanical forbidden-vocabulary check (Phase 7's own precedent)
  passes on the extended output too.
- Single-ticker-scope guardrail holds.

## 11. Failure criteria

- Any duplicate or inconsistent memory computation between the
  dossier's own thesis/graph portions.
- Any field silently dropped from either new section.
- Any modification to `render_report()`, `company_thesis_360.py`,
  `entity_context.py`, or any other frozen module.
- Any new synthesized field (a combined score, a cross-section summary
  sentence) appearing anywhere in the output.

## 12. Evaluation methodology

Read-only against real production data: for all 5 real tickers, at
each ticker's own latest real filing date, (a) render the dossier,
confirm no exception; (b) confirm the `CompanyMemory360`-derived text
is byte-identical to a direct `render_report()` call on the same data;
(c) confirm every Phase 8 evidence item and Phase 10 relationship
appears with its own citation, matching Section 10's own bar for
Phase 8's `test_company_thesis_360.py`; (d) re-run Phase 7's own
forbidden-vocabulary mechanical check against the full, extended
output; (e) the same `inspect.signature`-style single-ticker-scope
audit used in every prior phase; (f) database immutability (zero
writes — this remains a pure read/render phase).

## 13. Implementation boundary

**In scope**: one new dataclass (`CompanyResearchDossier`), one new
composition function, one new rendering function (calling `render_
report()` and appending two new sections); its own test file;
documentation. **Out of scope, explicitly**: everything named in
Section 14.

## 14. Explicit statement of what will NOT be built

- No modification to `render_report()`, `company_thesis_360.py`,
  `entity_context.py`, `company_memory_360.py`, or `company_thesis.py`.
- No new fact, ratio, trend, flag, entity, or relationship — this phase
  renders what Phases 1-10 already produced.
- No combined score, rating, or cross-section summary sentence.
- No cross-ticker section or comparison of any kind.
- No LLM call of any kind.
- No PDF/HTML output — Markdown only, matching Phase 7's own scope.
- No schema change, no database write.

## Stop condition

If rendering the two new sections is found to require any judgment
call beyond direct field substitution (e.g., deciding which of several
relationships to show "first" without a disclosed, neutral rule
already established), stop and report this as a design limitation
before proceeding — do not invent an ordering or filtering rule not
already grounded in an existing platform convention.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this correctly
identifies the intended next step — must be reviewed and approved
before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
