# FSI Phase 10 — Knowledge Graph Context Integration (Pre-registration)

*Design only. No implementation, no new extraction, no LLM call, no
subjective inference, no valuation, no ranking, no portfolio logic, no
alpha, no scoring, no narrative generation. Per instruction, written
and frozen BEFORE any execution begins. Builds on
`fsi-phase9-baseline-2026-08-02` and modifies nothing in Phases 1-9 —
all nine remain frozen, touched only for future bug fixes.*

## 1. Review of the complete architecture — FRE, FSI, LIM, and the Knowledge Graph

**LIM**: unchanged since the last two reviews — still RB-3c-interrupted,
`self_critique_quality` still 0.0, not a candidate input to anything.

**FRE track**: FRE-1 through FRE-6 frozen, unchanged.

**FSI track**: Phase 1-9 frozen. Phase 9 (just completed) populated
`entities` rows for all 5 FSI tickers and 4 real `renamed_from`
`entity_relationships` edges. **A concrete fact this review finds**:
nothing built in Phases 1-8 — `pit_financial_memory.as_of()`,
`company_memory_360.as_of()`, `company_thesis_360.as_of()`, or the
Phase 7 report generator — ever queries `entities` or `entity_
relationships` at all. Phase 9 gave all 5 tickers a real knowledge-graph
presence, but nothing in the platform's own reasoning/composition chain
reads it. The graph node exists; nothing connects to it.

**Knowledge Graph, checked directly, not assumed**: `entities` = 50
rows, `entity_relationships` = 5 rows (4 real `renamed_from` + 1
`effect_chains` artifact) — both real. `securities.sector_ngx` is
confirmed still 0/320 populated (unchanged since FRE-6's first check).
`events.ticker` is confirmed still 0/157 populated (every real event
is market- or sector-scope, never company-scope). `index_membership`
is confirmed, by direct query, to be **entirely synthetic placeholder
data**: all 12 rows carry `confidence=0.0` (this platform's own
established marker for "synthetic dev data, never feeds conclusions"),
and every `ticker` value is a fake `SYN*`-prefixed symbol
(`SYNBNKA`, `SYNOILA`, etc.) — no real ticker appears in this table at
all. This is a new, concrete finding this review surfaces: Part 2's own
design proposed projecting `index_membership` into the knowledge graph
as a zero-inference win ("read-only join, never duplicated"), but there
is currently no real data to project.

## 2. The single highest-impact remaining capability, filtered for zero subjective inference

**Connect the FSI composition chain (Phase 6/8's `CompanyMemory360`/
`CompanyThesis360`) to the Knowledge Graph nodes Phase 9 just created —
surfacing each ticker's own `entity_id`, canonical identity, and any
real `entity_relationships` (today: rename lineage, for the 4 tickers
where one exists) as an additional, read-only, cited context object.
Zero new data, zero new inference — purely wiring together two things
this program has already built and validated separately.**

## 3. Justification — why this precedes every other remaining item, and why several "obvious" alternatives are currently blocked by real data gaps, not merely policy

Every one of the owner's ten named candidates was checked directly
against the real database before being rejected — several fail not
because of a standing policy exclusion, but because the data they
would need does not yet exist in a usable form. Section 4 documents
this for each. What remains, after that filtering, is a genuine,
low-risk integration gap: Phase 9 built graph nodes that nothing
reads. Closing that is the only remaining candidate that is (a)
buildable today with zero new extraction, (b) directly serves
"explain and connect verified evidence" (the owner's own stated
emphasis) by literally connecting a company's own graph identity to
its financial reasoning for the first time, and (c) follows the exact
proven pattern (Phase 6, Phase 8) rather than inventing a new one.

## 4. Alternatives considered — all ten named candidates, each checked against real data

1. **Reasoning-mode rollout (FRE-8)**: the classification half is
   mechanical, but applies only to the LLM/FRE track's `causal_chain_
   steps`, which has real chains for very few facts (FRE-2's own
   docstring: 18 real facts). The enforcement half needs the standing
   LLM/cost decision. Rejected — smaller real footprint than the KG-
   integration gap, and partially blocked.
2. **Cross-document reasoning**: needs a new external data source
   (`news_outlets`) this document cannot acquire. Rejected.
3. **Multi-source evidence fusion**: the one real mechanism for this
   (`investment_implications.corroborates_implication_id`/
   `contradicts_implication_id`) already exists and is already
   surfaced by FRE-5's `CompanyThesis` (its own docstring: "already
   populated by the existing AI layer for 6 real rows -- not
   re-computed here, only surfaced"). There is no further zero-
   inference fusion mechanism to add today. Rejected.
4. **Event reasoning**: confirmed by direct query — `events.ticker` is
   0/157 populated; every real event is market- or sector-scope, never
   company-specific. There is no real ticker-scoped event data to
   reason over, and assigning company-scope to an existing event
   requires either new extraction or a verified mapping that does not
   exist. Rejected — blocked by a real, checked data gap.
5. **Macro reasoning**: Part 2's own design is explicit that a
   company's macro exposure "is itself an extraction target... not
   inferred purely from sector membership -- sector membership alone
   is a weak prior, not evidence." No zero-inference path exists.
   Rejected.
6. **Sector reasoning**: confirmed by direct query — `securities.
   sector_ngx` is 0/320 populated, unchanged since FRE-6's first check
   over a month ago. No verified alternative sector-classification
   source was found. Rejected — blocked by a real, checked data gap.
7. **Valuation activation (FRE-7)**: produces a number by definition —
   the single most explicitly and repeatedly excluded category
   throughout this program. Rejected.
8. **Portfolio reasoning**: the owner's standing exclusion, restated
   across nine consecutive approvals, plus Part 9's own dependency on
   Part 7 (Investment Thesis), which is only now beginning to be real.
   Rejected.
9. **Narrative generation**: subjective inference by definition — an
   LLM generating new explanatory text. The clearest rejection of the
   ten, against the owner's own stated filter. Rejected.
10. **Further knowledge graph expansion** (beyond Phase 9's own scope):
    checked directly and found currently blocked for the one
    zero-inference candidate Part 2's own design names —
    `index_membership` projection — because that table's data is
    confirmed 100% synthetic (`confidence=0.0`, fake `SYN*` tickers),
    not real. Every other unbuilt part of Part 2 (commodity/macro_
    variable/subsidiary entities, commercial/governance relation types)
    requires new extraction or LLM-based relation classification.
    Rejected for POPULATING more graph data — but this finding is
    exactly what motivates Section 2's proposal: the graph data that
    DOES already exist (Phase 9's own work) is not yet connected to
    anything, which is a more valuable, more available gap than adding
    more ungrounded graph nodes would be.

## 5. Objective

Build a small, additive `entity_context.py` module —
`get_entity_context(con, ticker) -> EntityContext`, single-ticker only
— that reads `entities`/`entity_relationships` for a given ticker and
returns its `entity_id`, `canonical_name`, `first_seen_doc_id`, and
every `entity_relationships` row involving it (as either subject or
object), each with its own `relation_type`, counterpart entity, `valid_
from`/`valid_to`, and `confidence` — verbatim, no new judgment. Then
compose this into a new, additive object alongside `CompanyMemory360`
(not modifying it, mirroring Phase 8's own precedent of composing over
a frozen module rather than editing it).

## 6. Research question

Does connecting Phase 9's real graph nodes to the FSI composition chain
surface anything genuinely new and useful (e.g., for AFRIPRUD/CAP/etc.,
does any real relationship exist at all, or will most tickers correctly
show "no known relationships"), and does composing a third layer
(entity context + `CompanyMemory360`) over two already-frozen modules
continue to require zero reconciliation logic, as Phase 6 and Phase 8
both found?

## 7. Architectural rationale

This is the third application of the same composition pattern
(Phase 6: `CompanyMemory` + `pit_financial_memory`; Phase 8:
`CompanyThesis` + `CompanyMemory360`; this phase: `entities`/`entity_
relationships` + `CompanyMemory360`). Each prior application composed
over two modules that were independently correct and never needed
reconciliation. This phase is lower-risk than either prior one, since
`entity_context.py` would be new (nothing to keep consistent with) and
the graph data it reads is small (50 entities, 5 relationships) and
fully verified.

## 8. Dependencies

`fsi-phase9-baseline-2026-08-02` (`entities`/`entity_relationships`, as
populated). `fsi-phase6-baseline-2026-08-01`
(`CompanyMemory360.as_of()`, called not forked). No new schema, no new
table, no new fact.

## 9. Risks

- **Low information yield for most tickers**: only NASCON (via its own
  pre-existing entity row) and, indirectly, none of the 4 renamed
  companies overlap with the 5 FSI tickers (already disclosed in Phase
  9's own report) — so 4 of 5 tickers will show zero `entity_
  relationships` in their context, correctly, not as a defect. This
  phase's value is completeness and future-readiness (any future real
  relationship immediately becomes visible through this same path),
  not an immediate rich payoff.
- **Scope-creep risk**: it would be tempting to also backfill
  `first_seen_doc_id`-derived narrative text or a "graph summary
  sentence" — explicitly rejected; this phase returns raw, structured
  fields only, exactly as Phase 6/8 did for their own composed objects.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 10. Success criteria

- `get_entity_context()` returns correct, complete data for all 5 FSI
  tickers with zero exceptions.
- For NASCON, `entity_id=22` and zero relationships (correct — NASCON
  was never renamed). For UCAP/BUAFOODS/AFRIPRUD/CAP, their own new
  Phase-9 `entity_id` and zero relationships (also correct — none was
  renamed).
- Composition with `CompanyMemory360` is exactly equivalent to calling
  each function directly — the same equivalence bar as Phase 6/8.
- Single-ticker-scope guardrail holds, verified mechanically as in
  every prior phase.

## 11. Failure criteria

- Any entity context returned for a ticker that doesn't match its real
  `entities`/`entity_relationships` rows exactly.
- Any modification to `entities`, `entity_relationships`, `Company
  Memory360`, or any other frozen module.
- Any narrative/synthesized field beyond the raw structured fields
  named in Section 5.

## 12. Evaluation methodology

Read-only against real production data: for all 5 FSI tickers, confirm
`get_entity_context()`'s returned fields match a direct query of
`entities`/`entity_relationships` exactly; confirm the composed object's
`CompanyMemory360` sub-result is unchanged from a direct call; confirm
the single-ticker-scope guardrail via the same `inspect.signature`
audit used in every prior phase; confirm database immutability
(zero writes — this is a read-only phase, unlike Phase 9).

## 13. Implementation boundary

**In scope**: one new module (`entity_context.py`) with one function
and its own return dataclass; one new, additive composition (naming an
execution-time decision, e.g. extending the existing pattern with a
`CompanyMemory360WithGraphContext` or similar); its own test file;
documentation. **Out of scope, explicitly**: any new extraction, any
new `entities`/`entity_relationships` row (Phase 9's own data is used
as-is), any modification to any frozen module, any LLM call, any
narrative synthesis, any cross-ticker output.

## 14. Explicit statement of what will NOT be built

- No new knowledge-graph data of any kind (no new entity type, no new
  relation type, no ownership/competitor/governance/macro edges).
- No sector, event, or macro reasoning (all three confirmed blocked by
  real, current data gaps, not merely deferred by policy).
- No narrative summary of a ticker's graph context — raw fields only.
- No cross-ticker relationship traversal (e.g., "which other companies
  share this entity's lineage") — single-ticker scope only, mirroring
  every prior phase's own guardrail.
- No modification to `entities`, `entity_relationships`, `Company
  Memory360`, `CompanyThesis360`, or the Phase 7 report generator.

## Stop condition

If composing entity context with `CompanyMemory360` is found to require
any reconciliation logic (unlike Phase 6 and Phase 8's own clean
compositions), stop and report this as a genuine finding — a
composition needing reconciliation would suggest the two data sources
disagree about something, which is itself worth surfacing honestly, not
smoothing over.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this correctly
identifies the intended next step, and whether the real, checked
blockers found for sector/event/index-membership reasoning are
accepted as genuine (not merely convenient) — must be reviewed and
approved before any implementation begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
