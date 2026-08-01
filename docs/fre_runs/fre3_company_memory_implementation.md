# FRE-3 — Company Memory Implementation

*Implementation report. Builds on `fre-architecture-baseline-2026-08-01`
(`f6f4034`), the infrastructure recovery (`4a1ad50`), and FRE-2's Evidence
Graph (`f7dd990`). Additive only — no schema change, no modification to
any AI Intelligence Layer pipeline file.*

## Scope note

This pass carried no new pipeline specification from the owner (unlike
FRE-2's explicit 8-stage description) — "Approve FRE-3 and proceed... per
the frozen architecture." Absent an override, this report follows the
frozen roadmap's own next-highest-leverage phase,
`docs/fre/12_research_roadmap.md`'s **FRE-3: Company Memory** (Part 5),
which that document itself flagged as "substantially executable today on
real, already-existing data" — a claim this pass verified rather than
assumed, per standing practice.

## Objective

Implement Part 5's `CompanyMemory` — a PIT-safe, read-only, per-company
longitudinal aggregation (filing history, dividend/corporate-action
history, management history, major-event history, coverage disclosure) —
against real data, following the exact same "inspect real data before
writing the classifier/aggregator" discipline FRE-2 established.

## What was built

| Artifact | Role |
|---|---|
| `src/ngxrot/fre/company_memory.py` | `CompanyMemory`/`build_company_memory(con, ticker, as_of_date)` — the only new code |
| `scripts/fre/test_company_memory.py` | 16 assertion checks against the real database (no write path exists in this module, so no scratch copy is needed at all) |

No schema change. No write path of any kind — `build_company_memory` is
purely a set of `SELECT` queries; this is the first FRE module with zero
mutation surface.

## Real-data findings that shaped the design

Before writing any code, per-ticker coverage was inspected directly:
`documents.ticker` resolves for 11,134/11,533 rows (96.5%); the richest
real per-ticker fact history belongs to UCAP (United Capital Plc, 163
documents, 8 extracted facts). Two concrete, real findings emerged from
that inspection and materially changed the design:

**1. A real cross-ticker extraction mismatch, already caught by the
platform's own governance.** Fact 151 shares its source document (`doc_id
6955`, a genuine United Capital Plc filing) with fact 50, yet fact 151's
own LLM-extracted description reads *"The Board of Directors of NASCON
Allied Industries Plc approved..."* — a different, real, separately-listed
NGX company. This is a genuine extraction error from the 2026-07-27
stabilization pass's live pilot run, not a data-entry issue introduced
here. Direct query confirms it was **already caught**:
`investment_implications.status = 'blocked_by_self_critique'` for fact
151. A full-database query further confirms exactly **4 real
`blocked_by_self_critique` implications exist** (fact 144/GTCO, 151/UCAP,
154/LIVINGTRUST, 161/CILEASING) — 4 of the 18 real LLM-pilot facts, a
22.2% rate, matching `HANDOFF.md`'s own previously-recorded "22.2%
self-critique rejection rate" figure exactly, an independent confirmation
that this pass's read of the real data agrees with the platform's own
prior record.

**Design consequence**: `build_company_memory`'s `dividend_history`/
`corporate_action_history` **exclude any fact whose implication is
`blocked_by_self_critique`** — the same treatment every other consumer on
this platform already gives a blocked row — and report the exclusion
count in `coverage_note` rather than silently narrowing history with no
trace. Verified on two independent real cases: UCAP (1 excluded, fact 151)
and GTCO (1 excluded, fact 144, the same rights-issue case already on
record in `HANDOFF.md` as a real self-critique block).

**2. `events.ticker` is confirmed 100% NULL** across all 157 real event
rows (146 `market`-scope, 11 `sector`-scope, 0 company-scope) — verified
by direct query, not assumed. Every ticker's `major_event_history` is
therefore correctly empty today; this is a real, systemic, disclosed gap
in the existing `events` table's population, not a defect in this module.

## Scope decision: `strategy_narrative_timeline` deferred, not attempted

Part 5's design named this the hardest, most speculative component, with
an explicit constraint that it must never be built on insufficient
evidence. Real-data inspection confirms it cannot be meaningfully built
yet: even UCAP's richest case is 7 short, single-sentence, purely numeric
Phase-B facts ("Dividend per share: 1.5..."), and no company in the
current real dataset has more than one prose-bearing (LLM-extracted) fact
— there is no real pair of same-company narrative snapshots to compare.
Attempting the comparison anyway would manufacture a finding from data
that cannot support one. `CompanyMemory.coverage_note` states this
explicitly for every ticker rather than silently omitting the field.

## Alternatives considered

1. **Silently include `blocked_by_self_critique` facts in history** (they
   are, after all, "real" extracted rows). Rejected — this is exactly the
   governance the self-critique gate exists to enforce; a memory object
   that quietly launders a blocked claim back into "trusted history" would
   undo the platform's own review.
2. **Default `as_of_date` to "everything" (`None`) for convenience.**
   Rejected — matches every other PIT reader on this platform
   (`index_levels_asof`, `events_asof`) in requiring an explicit date; an
   implicit "give me everything" default is exactly how look-ahead bias
   enters a reasoning call that doesn't realize it's using one.
3. **Attempt a minimal strategy-narrative comparison anyway, capped at low
   confidence, rather than deferring entirely.** Rejected — a capped
   confidence still implies there is *something* to compare; with zero
   real same-company narrative pairs, there is nothing to cap, only
   nothing to build. Deferring outright is the more honest choice.
4. **Infer `major_event_history` from `sector`-scope events plus a
   company's sector.** Rejected — `securities.sector_ngx` is 0/320
   populated (the same disclosed gap this whole program has cited
   repeatedly); building a sector-inference path on top of an unpopulated
   field would compound one disclosed gap with another rather than
   resolve either.

## Trade-offs

- Excluding blocked facts means a ticker's dividend history could
  understate real corporate activity if a genuinely-correct fact is ever
  incorrectly blocked (a false-positive self-critique fail) — but the
  alternative (including a fact the platform's own review flagged) is the
  worse failure mode, consistent with the charter's "never optimize for
  positive results — optimize for truthful ones."
- Zero write path keeps this module maximally safe but means it produces
  no persistent artifact — every call recomputes from source tables,
  acceptable at current data volume (161 facts, 11,533 documents) and
  revisited only if query latency becomes a real, measured problem.

## Risks

- **`documents.ticker` reflects the filing/archive-source identity, not
  always the fact's actual subject company** (the UCAP/NASCON case is
  direct proof of this, not a hypothetical) — this module aggregates by
  `documents.ticker` because it is the only resolvable join key today; a
  future improvement could cross-check a fact's own description text
  against `securities.name` for a subject-mismatch flag, not built here.
- **The self-critique-block exclusion depends entirely on an
  `investment_implications` row existing and being current** — a fact with
  no implication row yet (LEFT JOIN yields `NULL` status) is *not*
  excluded, which is correct (nothing to block on) but worth restating
  explicitly: absence of a block is not the same as a confirmed-good fact.

## Future extensions

- A `securities.name`-vs-description cross-check for the ticker-attribution
  risk noted above.
- Re-run once `sector_ngx` is populated, to extend `major_event_history`
  with sector-scoped events for a company's own sector (still distinct
  from, never conflated with, a directly company-scoped event).
- Re-evaluate `strategy_narrative_timeline` once any company accumulates
  ≥2 real prose-bearing facts.

## Verification performed

| Check | Result |
|---|---|
| `scripts/fre/test_company_memory.py` | **16/16 PASS** (UCAP/GTCO real-data exclusion correctness, PIT-filtering correctness across two `as_of_date` values, graceful degradation on a nonexistent ticker, confirmed-empty `events.ticker`/`management_history`) |
| `scripts/test_reasoning_pipeline.py` (pre-existing) | 154/154 PASS, unchanged |
| `scripts/fre/test_evidence_graph.py` (FRE-2) | 29/29 PASS, unchanged |
| `scripts/check_db_safety.py` | PASS, 0 violations |
| Production DB row counts, all 27 tables | Unchanged — this module has no write path at all |

## Dependencies

`docs/fre/05_company_memory.md` (the design this implements), `documents`,
`extracted_facts`, `investment_implications`, `entities`/
`entity_relationships` (Part 2, read-only), `events` (read-only, confirmed
empty for this use today). FRE-2's `evidence_graph.py` module is
independent — no import between the two.

---

*Per the standing instruction, this concludes FRE-3. Stopping here and
awaiting review before beginning FRE-4.*
