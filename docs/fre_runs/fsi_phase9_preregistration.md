# FSI Phase 9 — Knowledge Graph Completeness: Verified Entities and Rename Lineage (Pre-registration)

*Design only. No implementation, no new extraction, no LLM call, no
subjective inference of any kind, no valuation, no ranking, no
portfolio logic, no alpha, no scoring, no narrative generation. Per
instruction, written and frozen BEFORE any execution begins. Builds on
`fsi-phase8-baseline-2026-08-02` and `fre-architecture-baseline-
2026-08-01`'s own Part 2 design (`docs/fre/02_knowledge_graph_
expansion.md`), and modifies neither — both remain frozen, touched
only for future bug fixes.*

## 1. Review of the entire platform architecture

**LIM**: still RB-3c-interrupted, `self_critique_quality` still 0.0 —
unchanged since the last review (Phase 8), not a candidate input to
anything.

**FRE track**: FRE-1 through FRE-6 all frozen. FRE-1 (2026-08-01)
already widened `entities.entity_type`'s CHECK constraint to add
`commodity`/`macro_variable`/`subsidiary`/`index` — but a direct query
against the real database confirms these four new types have **zero
populated rows**; only `company` (4 rows) and `competitor_mention` (35
rows) have ever been populated. `entity_relationships` has exactly
**one row, database-wide**, and its `relation_type` is
`affects_order_1` — an `effect_chains`-derived artifact, not a
genuinely classified relationship. `docs/fre/02_knowledge_graph_
expansion.md` (Part 2, frozen design, 2026-08-01) already names this
exact state as its own rationale: "Phase F's own propagation logic
works around this with a no-op filter... explicitly flagged in that
report as 'a no-op filter today, real once entity typing gets more
precise.' This document is that 'once.'" That "once" has still not
happened.

**FSI track**: Phase 1-8 all frozen, 106 facts, 177 conclusions, 8
composition/validation/presentation layers built on top. **A concrete,
newly-surfaced fact this review finds**: of the FSI track's own 5
validated tickers, only **NASCON** has a real `entities` row
(`entity_id=22`). UCAP, BUAFOODS, AFRIPRUD, and CAP — 4 of the 5
tickers this entire eight-phase program has built and validated
financial reasoning for — **do not exist as nodes in the knowledge
graph at all.**

## 2. The single highest-impact remaining capability, filtered for zero subjective inference

**Populate real `entities` rows for all 5 FSI tickers, and populate
real, typed `entity_relationships` rows for the 4 already
owner-verified ticker renames in `data/reference/symbol_renames.csv`
— closing Part 2's own two named gaps (entity coverage, real
relation-type population) using only data that already exists and is
already owner-verified. Zero new extraction, zero LLM call, zero
inference of any kind.**

## 3. Justification — why this precedes every other remaining item, filtered specifically for "no subjective inference"

Every other named candidate either requires new inference (violating
the owner's explicit filter for this phase) or is blocked on a decision
this document cannot make. This item is the largest gap that is
**purely mechanical, start to finish**: `symbol_renames.csv`'s 4
"verified" rows (status column, already owner-reviewed) are a
deterministic, already-trusted mapping the quant Data Layer itself
relies on; projecting them into the knowledge graph is a pure data
transcription, not a judgment. Section 4 compares this against every
one of the owner's seven named alternatives explicitly.

## 4. Alternatives considered — the owner's seven named candidates, each addressed against the "zero subjective inference" filter

1. **Reasoning-mode rollout (FRE-8)**: partially mechanical (a
   keyword-based classifier over already-existing causal chain text,
   the same pattern FRE-2's `implication_layer` classifier already
   uses) but the roadmap's own framing of this item bundles
   classification WITH "guardrail enforcement... wired into the
   self-critique gate" for future LLM calls — the enforcement half is
   inseparable from the standing LLM-vendor/cost decision. Rejected for
   this phase; a future, narrower "retrospective mode classification
   only" proposal could revisit the mechanical half specifically.
2. **Cross-document/multi-source reasoning (Part 6)**: requires a new
   external data source decision (a `news_outlets` registry) this
   document cannot make, and once acquired would still need LLM-based
   corroboration synthesis to be useful — subjective inference at its
   core. Rejected.
3. **Knowledge graph expansion (Part 2)** — proposed above, in its
   purely mechanical subset only.
4. **Evaluation improvements (FRE-10)**: blocked on an owner-authored
   "strategy-narrative gold set," named as its own blocker since the
   original roadmap and reconfirmed unresolved in Phase 5 and Phase 8's
   own reviews. Rejected for this phase.
5. **Portfolio reasoning (FRE-9-in-the-roadmap, not to be confused with
   this document's own Phase 9 numbering)**: rejected on the same two
   grounds restated in Phase 8's own review — the owner's repeated,
   explicit standing exclusion, and Part 9's own dependency table
   naming Part 7 (Investment Thesis) as its prerequisite, which itself
   is only now beginning to be fed by real FSI evidence (Phase 8) for 2
   of 5 tickers. Rejected.
6. **Valuation activation (FRE-7)**: produces a number by definition —
   the single most explicitly and repeatedly excluded category in this
   entire program. Rejected.
7. **Narrative generation** (the deferred Area 4b layer from Phase 3):
   this is, by definition, subjective inference — an LLM generating new
   explanatory text. This is the one candidate that fails the owner's
   own stated filter most directly and unambiguously. Rejected.

## 5. Objective

Populate, for the real, current database: (a) `entities` rows
(`entity_type='company'`) for the 4 FSI tickers currently missing one
(UCAP, BUAFOODS, AFRIPRUD, CAP), matching the existing pattern already
used for NASCON's own row; (b) `entity_relationships` rows
(`relation_type='renamed_from'`) for the 4 already owner-verified
ticker renames in `symbol_renames.csv` (`FO→ARDOVA`,
`GUARANTY→GTCO`, `ACCESS→ACCESSCORP`, `FBNH→FIRSTHOLDCO`), with
`valid_from` set to each rename's own recorded effective date. A new,
minimally-scoped `configs/relation_taxonomy.toml` seeded with only the
`[corporate_structure]` family and only the `renamed_from` type this
phase actually populates — not the full taxonomy Part 2's design
sketches, since nothing would populate the other families yet.

## 6. Research question

Can Part 2's own two named gaps be closed using only data this
platform already possesses and already trusts (the FSI track's own
5-ticker roster; `symbol_renames.csv`'s "verified" status column),
with zero new extraction and zero LLM call — i.e., is a real, useful
knowledge-graph presence achievable purely as a transcription exercise,
or does it turn out to require some new judgment even at this
minimal scope?

## 7. Architectural rationale

Every previous FSI composition phase (6, 8) succeeded by composing over
already-frozen, already-trusted modules without modifying them. This
phase applies the same discipline to a different kind of composition:
instead of combining two Python modules, it combines two already-
existing, already-trusted DATA SOURCES (the FSI ticker roster and the
quant engine's own verified rename mapping) into the one part of the
schema (`entities`/`entity_relationships`) that has sat almost entirely
unpopulated since FRE-1 first widened it. This is architectural
completeness in the most literal sense: filling in a real, disclosed,
already-designed gap with data already on hand, not inventing a new
capability.

## 8. Dependencies

`fsi-phase8-baseline-2026-08-02` (the 5-ticker roster). `data/
reference/symbol_renames.csv` (existing, quant-engine-owned,
owner-verified — read-only reuse, never duplicated). The existing
`entities`/`entity_relationships` schema (FRE-1's additive widening,
already in place, requires no further schema change). `db.py`'s
`_migrate_entities_table()` precedent, for reference only — not
re-run, since the schema itself needs no further change, only new rows.

## 9. Risks

- **Scope-boundary risk**: Part 2's own design bundles this mechanical
  sub-scope alongside much riskier extraction targets (ownership
  percentages, competitor/supplier relation classification, merger/
  demerger detection) — this phase must not be allowed to expand into
  those by "since we're already in this file" momentum. Mitigated by
  the explicit Section 11 exclusion list below.
- **Rename-edge correctness risk**: an incorrectly-dated or incorrectly-
  directed `renamed_from` edge would misrepresent real corporate history
  — mitigated by using ONLY the 4 rows marked `verified` in `symbol_
  renames.csv` (not the 49 `candidate` rows, which the CSV's own
  `evidence` column explicitly flags as needing verification before
  use — e.g. the `UBCAP→UCAP` candidate row is explicitly NOT used
  here for exactly this reason, even though UCAP is one of this
  program's own 5 validated tickers).
- **None of the 4 verified renames involve any of the FSI track's 5
  tickers** — confirmed by direct check. This phase's rename-edge
  population is a real, disclosed, general knowledge-graph improvement,
  not something that changes any FSI ticker's own graph connectivity;
  only the new `entities` rows (item (a) above) directly benefit the
  FSI track's own tickers. Disclosed here so this is not mistaken for a
  bigger FSI-specific win than it is.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 10. Success criteria

- All 5 FSI tickers have exactly one real `entities` row each
  (`entity_type='company'`), matching NASCON's existing row's shape.
- All 4 verified renames have exactly one `entity_relationships` row
  each (`relation_type='renamed_from'`), with `valid_from` matching
  `symbol_renames.csv`'s own recorded effective date.
- Zero rows created from any `candidate`-status row in `symbol_renames.
  csv`.
- Database immutability preserved for every table except `entities`/
  `entity_relationships` themselves (an explicitly additive write, not
  a "zero write" phase like Phases 4-8 — this is a data-population
  phase, disclosed as such, not a read-only composition).
- Full regression suite passes; Phase 5's validation harness re-run and
  still reports PASS (its own golden snapshot does not cover `entities`/
  `entity_relationships`, so no update to that snapshot is expected to
  be needed — verified, not assumed).

## 11. Failure criteria

- Any `entities`/`entity_relationships` row created from unverified
  (`candidate`-status) source data.
- Any existing row in any table modified or deleted (this remains an
  append-only, additive-insert-only phase).
- Any expansion into the excluded, LLM-dependent parts of Part 2's own
  design (ownership extraction, competitor/supplier relation
  classification, merger/demerger detection) — an explicit statement of
  what will NOT be built (Section 12) exists specifically to make this
  checkable.

## 12. Explicit statement of what will NOT be built

- No ownership/shareholding extraction (`major_shareholder_of` edges) —
  Part 2's own design flags this as "financially sensitive and
  error-prone," requiring new extraction this phase does not do.
- No competitor/supplier/customer/distributor relation classification
  (the `[commercial]` taxonomy family) — requires LLM-based
  relationship classification from text, explicitly excluded as
  subjective inference.
- No governance relations (`board_member_of`, `audited_by`, etc.) —
  same reason.
- No macro-exposure edges (`exposed_to_commodity`, etc.) — same reason,
  and additionally requires a company-specific exposure disclosure
  extraction not yet performed.
- No merger/demerger detection or edges — Part 2's own design requires
  this to go through the existing human-review entity-resolution queue,
  not be auto-created; not attempted here.
- No population of the `commodity`/`macro_variable`/`subsidiary`/
  `index` entity types — these remain real schema capacity with zero
  rows after this phase too; populating them requires either new
  extraction or a decision about what commodities/macro variables to
  seed, both out of scope here.
- No modification to `industry_reasoning.py`'s existing peer-
  propagation logic, even though this phase's new `renamed_from` edges
  could in principle improve it — that would be a change to a frozen
  FRE-track module, out of scope for a data-population phase.
- No LLM call of any kind.

## 13. Evaluation methodology

Read-only verification against the real database after the additive
inserts: (a) confirm exactly 5 `entities` rows with `entity_type=
'company'` matching the FSI roster, up from today's 1 (NASCON only);
(b) confirm exactly 4 new `entity_relationships` rows with
`relation_type='renamed_from'`, up from today's 0 real ones (the
existing 1 row, `affects_order_1`, is untouched and remains); (c)
confirm the 4 new relationship rows' `valid_from` dates match `symbol_
renames.csv`'s own `new_first` column exactly; (d) confirm zero rows
were created from any `candidate`-status source row; (e) full
regression suite; (f) Phase 5's own validation harness re-run.

## 14. Implementation boundary

**In scope**: one new, additive data-population script (dry-run/
`--apply`, matching the established convention from every prior FSI
extraction script); a new, minimally-scoped `configs/relation_
taxonomy.toml` (one family, one type); its own test file; documentation.
**Out of scope, explicitly**: everything named in Section 12. No
modification to any frozen FRE/FSI module. No schema change (the
`entities`/`entity_relationships` schema already supports everything
this phase needs, per FRE-1's own additive widening).

## Stop condition

If populating even this minimal, mechanical scope is found to require
any judgment call not already resolved by `symbol_renames.csv`'s own
`verified`/`candidate` status column (e.g., an ambiguous rename date,
or a ticker that appears in more than one verified row), stop and
report it — do not resolve an ambiguity by guessing, per this
program's standing "unknown stays unknown" discipline.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this correctly
identifies the intended next step — must be reviewed and approved
before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
