# FSI Phase 13 — Implementation Log

*Live journal. Per `docs/fre_runs/fsi_phase13_preregistration.md` and the
owner's continuous-execution operating-mode instruction (per-phase
approval checkpoint disabled for this track). Append-only.*

## Entry 0 — Ticker selection and candidate confirmation

Re-ran `scripts/fre/fsi_scope_candidates.py` (read-only): confirmed the
349-candidate/49-ticker pool is still current. Selected 5 new tickers for
sector diversification, each with 2 candidate documents identified via a
direct `documents` query: **MTNN** (telecom, docs 8080/9430), **DANGCEM**
(cement/industrial, docs 8383/9741), **UBN** (banking, docs 5987/7232),
**OANDO** (oil & gas, docs 7058/9355), **NESTLE** (FMCG, docs 8089/9423).

## Entry 1 — Hand-reading and real findings, per ticker

Every figure below was read directly from the real archived filing text
(`data/staging/document_text/<doc_id>.txt`), the same discipline as Phase
1/2. Full quotes and line references are in `scripts/fre/
fsi_extract_phase13.py`'s own docstring and per-entry notes; summarized
here:

- **MTNN**: both FY2023 (doc 8080) and FY2024 (doc 9430) are REAL
  STATUTORY NET LOSSES (forex-driven) — FY2023 PAT -N137,020m, FY2024 PAT
  -N400,435m. Both filings' press releases headline a separate "adjusted
  PAT" (ex-forex-loss, N344.5bn for FY2023) — per the platform's
  no-fabrication rule, the statutory PAT is recorded as `net_profit`; the
  adjusted figure is noted in the fact's description only, never
  substituted. Doc 8080 additionally has a real, tiny internal
  inconsistency: its own highlights narrative states "(137,021)" for the
  same line its own detailed table states "(137,020)" — a 1-unit
  (N'million) rounding difference within the same document, disclosed,
  not resolved. The detailed table's "PAT" label matched the EXISTING
  `net_profit` synonym exactly — no new synonym needed.
- **DANGCEM**: both docs (8383, 9741) are Q1 (three-month) UNAUDITED
  results, not FY — `period_type='Q1'` for both, correctly derived from
  the actual period span, never from the filing's own headline label
  (same UCAP-precedent rule). Each filing independently confirms the
  other's own comparative-column figures exactly. Both filings carry TWO
  real label variants for the same figures in different sections (e.g.
  "Total revenue"/singular in one table, "Total revenues"/plural in
  another) — the singular, EXISTING-synonym-matching label was used in
  each case; "Net profit" (a real new label variant, distinct from "Group
  net profit" used elsewhere in the same filing) required one new
  `net_profit` synonym.
- **UBN**: a bank — Group "Gross Earnings" (mapped_equivalent, same
  sector convention as AFRIPRUD) and Group "Profit After Tax"
  (direct_reported, exact existing synonym) only; no EBIT/EBITDA (genuine
  architectural gap, same as UCAP). REAL CROSS-FILING RESTATEMENT
  DISCREPANCY DISCLOSED (same class of finding as CAP in Phase 1): doc
  7232's own FY2021 comparative column (Group Gross Earnings 177.3bn /
  PBT 18.2bn / PAT 16.9bn) does not match doc 5987 (the actual FY2021
  filing)'s own originally-reported FY2021 Group figures (172.0bn /
  20.8bn / 19.4bn). Each fact is recorded from its own filing's own
  stated figure; the comparative column is informational only, never a
  separate fact.
- **OANDO**: no EBITDA/D&A disclosure in either filing (genuine gap).
  Doc 7058's FYE2021 results were released 28 March 2023 — a real,
  unusually long reporting lag, not a data error. Two distinct real
  hyphenation variants of the net_profit label across its own two
  filings ("Profit/(Loss)-After-Tax" vs. "Profit-After-Tax") each
  required a new synonym.
- **NESTLE**: both FY2023 (doc 8089) and FY2024 (doc 9423) are REAL
  STATUTORY NET LOSSES (forex/finance-cost driven) — FY2023
  -N79,473,781k, FY2024 -N164,595,022k. Doc 9423 additionally discloses a
  separate "Total Comprehensive loss for the period" (-N14,557,657k for
  FY2024) that INCLUDES a one-off N150,037,365k PP&E revaluation surplus
  (OCI, from a March 2024 change to the revaluation model) — NOT the same
  concept as net_profit and not used; the statutory P&L "Loss for the
  period" figure is what was recorded, per the same no-fabrication rule
  as MTNN's adjusted-PAT case. Doc 9423's EBITDA (N196.7bn) is
  narrative-only and rounded (no precise tabulated EBITDA line in either
  NESTLE filing) — direct_reported (the filing literally says EBITDA)
  but flagged lower-precision, same disclosed caveat as BUAFOODS's own
  narrative-only EBITDA in Phase 2. Two new label variants required new
  synonyms: "(Loss)/profit for the period" (doc 8089), "Loss for the
  period" (doc 9423); "Results from operating activities" (both docs)
  required one new `ebit` synonym.

## Entry 2 — Config changes (real, disclosed additions only)

`configs/financial_statement_terminology.toml`: 5 new `net_profit`
synonyms ("Net profit", "Profit/(Loss)-After-Tax", "Profit-After-Tax",
"(Loss)/profit for the period", "Loss for the period") and 1 new `ebit`
synonym ("Results from operating activities"), each tied to a specific,
named real filing in the config's own note. No synonym was needed for
`revenue` or `ebitda` — every new ticker's real label for those two
concepts matched an EXISTING synonym exactly (case-insensitively).

## Entry 3 — Extraction (`scripts/fre/fsi_extract_phase13.py`)

Mirrors `fsi_extract_phase2_ebitda_ebit.py`'s own structure exactly
(dry-run/`--apply`, automatic pre-write backup, `classify_period_type`,
`map_label_to_concept` with an assertion, `find_restatement_conflicts`
check before every write). Dry run confirmed all 31 planned facts (10
filings x revenue/net_profit/ebit/ebitda where disclosed) map correctly
with zero restatement conflicts and zero assertion failures, before
`--apply` wrote them. Scope: core metrics only (revenue, net_profit,
ebit, ebitda) — balance-sheet and cash-flow extraction for these 5
tickers is explicitly deferred to a future phase, matching Phase 1's own
original scope before Phase 2 later extended it.

Result: `extracted_facts` 267 -> 298 (31 new), `evidence` 301 -> 332,
`documents` unchanged (11,533). `foreign_key_check` clean,
`integrity_check` ok.

## Entry 4 — A real bug found and fixed during this phase's own execution: duplicated conclusions for the 5 original tickers

Re-running Phase 3's three frozen scripts (`fsi_phase3_compute_metrics.py`,
`fsi_phase3_classify_trends.py`, `fsi_phase3_compute_flags.py`) to compute
the 5 new tickers' financial-reasoning conclusions correctly added 90 new
rows for those tickers — but each script's `list_tickers(con)` call now
returns all 10 tickers (the frozen scripts were never designed with a
per-ticker skip/dedup check, since no ticker had ever been re-processed
before this phase), so all three scripts ALSO recomputed and
re-`INSERT`ed a byte-for-byte duplicate of the pre-existing 177
conclusions for the 5 ORIGINAL tickers (confirmed by direct inspection:
`conclusion_id` 1-177 was the untouched original set; every duplicate row
had `conclusion_id` > 177; each of the 5 original tickers' own conclusion
count had exactly DOUBLED). This surfaced downstream as real test
failures in `test_pit_financial_memory.py` (NASCON returning 10 ratio
conclusions instead of 5 at its own first filing date) and
`test_reasoning_context.py` (a ticker-scoped query returning duplicate
rows).

This is a real mistake made DURING this phase's own execution — not a
historical production defect, and not a frozen-module defect requiring
owner authorization to fix (the frozen scripts' own INSERT-only design
was correct and sufficient for a single, one-time run against a fixed
ticker set; re-running them against an EXPANDED ticker set without first
scoping out already-processed tickers was the actual mistake, made by
this execution, not a flaw in Phase 3's own architecture). Fixed via a
dedicated, disclosed cleanup script,
`scripts/fre/fsi_phase13_fix_duplicate_conclusions.py` (dry-run/`--apply`,
automatic backup): identified the exact 177 duplicate `conclusion_id`s
(all > 177, all belonging to the 5 original tickers) and their 418 linked
`financial_reasoning_conclusion_facts` rows, deleted them, and confirmed
the original 5 tickers' conclusion count returned to exactly 177 and the
5 new tickers' 90 rows were untouched. `foreign_key_check` clean,
`integrity_check` ok after the fix.

**Disclosed lesson for any future phase**: any future re-run of Phase 3's
scripts against a further-expanded ticker set must first scope the run to
only the newly-added tickers (or add an explicit dedup/upsert check) —
left as a documented operational note here, not a code change, since
Phase 3's own scripts remain frozen and their original one-time-run design
was not itself wrong.

## Entry 5 — Generalization test across Phases 4-12 (zero code modification)

Directly exercised `pit_financial_memory.as_of()`, `company_memory_360.
as_of()`, `financial_reasoning_report.render_report()`,
`company_thesis_360.as_of()`, `entity_context.get_entity_context()`/
`as_of()`, and `company_research_dossier.build_dossier()`/
`render_dossier()` for all 5 new tickers — all six composition/
presentation layers ran without exception, with zero code modification,
correctly returning "no knowledge-graph presence yet known" (honest,
never fabricated) for tickers with no `entities` row (Phase 9's knowledge
graph population is out of scope for Phase 13; entities/relationships for
these 5 new tickers remain a disclosed, deferred gap, same class as any
other "unknown stays unknown" case elsewhere on this platform). Also ran
Phase 12's real CLI (`scripts/fre/generate_research_dossier.py`)
end-to-end for MTNN via a real subprocess invocation — correct output,
including the correct empty-knowledge-graph-context message.

## Entry 6 — Golden snapshot re-freeze (disclosed, per the freeze script's own documented rule)

`scripts/fre/fsi_phase5_freeze_golden_snapshot.py`'s own docstring
anticipates exactly this case ("re-run only if a future, owner-approved
phase legitimately changes Phase 1-4's output"). Re-ran it: new frozen
baseline is 137 financial facts (was 106) and 267 conclusions (was 177:
125 ratio + 112 trend + 30 flag, was 75/87/15).

## Entry 7 — Stale test assertions updated (same discipline as every prior phase)

Three test files had hardcoded absolute counts that were now stale (the
same recurring pattern as `test_valuation_engine.py`'s own fact-count
assertion, previously updated 4 times as real data grew) — each updated
with a disclosed comment explaining the new number, never left silently
wrong:

- `test_financial_ratios.py`: `list_tickers` now expected to find all 10
  tickers (was 5).
- `test_phase9_knowledge_graph.py`: `extracted_facts` count updated to
  298 (was 267) — Phase 9's own script still never writes facts; this
  assertion only tracks the real, current total.
- `test_valuation_engine.py`: financial-statement line-item count updated
  to 137 (was 106), with the new per-metric breakdown disclosed.
- `test_pipeline_validation.py`: golden-snapshot baseline totals updated
  to 137 facts / 267 conclusions (125/112/30), matching Entry 6's
  re-freeze.

## Entry 8 — Validation and full regression (complete)

All 23 test files in `scripts/fre/` pass in full after the duplicate-
conclusion fix and the stale-assertion updates -- 333 total assertions
across all 23 files, every one green, zero failures. `scripts/check_db_safety.py`
PASS. `scripts/test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5's
own `fsi_phase5_validate_pipeline.py` harness re-run and reports PASS on
all three components (golden-snapshot reproducibility at the new 137/267
baseline; cross-phase Phase 3<->Phase 4 consistency across all 10
tickers, 0 violations; database immutability, all 29 tables unchanged
before/after).

**Full integrity verification**: `PRAGMA integrity_check` -> `ok`;
`PRAGMA foreign_key_check` -> clean, database-wide; `documents` (11,533,
unchanged), `extracted_facts` (298), `evidence` (332),
`financial_reasoning_conclusions` (267) all confirmed correct and
consistent with the re-frozen golden snapshot.

**FSI Phase 13 is now complete, validated, and documented.** Proceeding
to the final report, then freezing this baseline.
