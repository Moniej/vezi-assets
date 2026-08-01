# FSI Phase 2 — Implementation Execution Plan / Checkpoint

*Planning document only. No implementation, no schema change, no code
change, no config file created in this pass. Per instruction, implementation
begins only after this checkpoint is reviewed and approved — the same
two-gate discipline used for every phase of this program. Builds on
`fsi-phase1-baseline-2026-08-01` and the approved
`docs/fre_runs/fsi_phase2_preregistration.md`.*

## 1. Constraints, restated as concrete mechanisms (not just principles)

| Constraint | Concrete mechanism |
|---|---|
| No inferred financial facts | Only Tiers 1–3 of the confidence hierarchy (§2) are ever written as facts. **Tier 4 (interpretation) is never written in Phase 2** — if a figure can only be established through subjective judgment beyond mapping or formula application, Phase 2 records a `research_task_candidates`-style missing-evidence note instead of a fact. This is a hard rule, not a preference. |
| No silent metric substitution | Every terminology-mapping decision (e.g., "Gross Earnings" → `revenue`) is recorded explicitly in the fact's own description, citing which config-listed synonym matched — never a bare value with no trace of which label produced it. |
| No overwriting historical values | Append-only throughout, unchanged from every prior phase. A restatement creates a **new** row linked to the original via the restatement mechanism (§4.3) — the original row is never updated or deleted. |
| No valuation activation | `valuation_engine.py` is not modified in Phase 2. New balance-sheet/cash-flow/EBITDA facts will further shift some adapters' `is_ready()` state (as Phase 1's revenue/net_profit facts already did) — expected, disclosed, and still produces zero numeric valuation output, per the existing, tested `NotImplementedError` gate. |
| Every extracted metric requires provenance | Enforced by the schema (§4.1) and by the extraction script's own structure (§5) — a fact cannot be written without all six provenance fields (§3) populated. |

## 2. Confidence hierarchy (new, explicit — not the same as the existing numeric `extraction_confidence`)

A new, **qualitative** dimension distinct from the existing 0.0–1.0
`extraction_confidence` float (which stays, unchanged, as the numeric
estimate within a tier). Four tiers, ordered highest to lowest trust:

| Tier | Definition | Phase 1 example |
|---|---|---|
| **`direct_reported`** | The canonical metric is stated as its own explicit line item, under a label that already matches (or is the filing's own literal use of) the canonical name, with no arithmetic reconstruction needed. | UCAP's "Total Revenue 7,069,171" — read directly. |
| **`mapped_equivalent`** | The value is stated directly and literally, but under a label that differs from the canonical name and required a terminology-mapping decision (§4.4) to identify. | AFRIPRUD's "Gross Earnings 2,630,001" → mapped to `revenue`. |
| **`derived`** | No single stated line exists; the value is computed from other already-extracted, directly-sourced figures via a **definitional** (never causal) formula from `configs/financial_ontology.toml`. | AFRIPRUD doc 7540's revenue = revenue-from-contracts + interest income + other income (a 3-line sum, no explicit "Gross Earnings" row existed in that filing). |
| **`interpretation`** | Establishing the value requires a subjective judgment beyond mapping or formula application (e.g., choosing between two genuinely ambiguous candidate figures). **Never written as a fact in Phase 2** — recorded as a missing-evidence note instead. | None occurred in Phase 1 — even the BUAFOODS garbled-table case (doc 9357) resolved via an exact cross-reference match, which is `direct_reported` with a difficult *retrieval* process, not an interpreted value. Kept as a defined, real category for Phase 2's harder territory (cash flow, EBIT/Operating-Profit ambiguity) even though unused so far. |

**Retroactive note**: Phase 1's 30 facts would, under this new hierarchy,
classify as 24 `direct_reported`, 6 `mapped_equivalent` (all 3 AFRIPRUD
revenue facts plus... on inspection, only AFRIPRUD's 3 revenue facts
actually required a label-to-concept mapping; net_profit was always
directly labeled across all 15 filings) — corrected: **27 `direct_reported`,
3 `mapped_equivalent`, 0 `derived`, 0 `interpretation`** (AFRIPRUD doc
7540's revenue, retroactively, is actually `derived`, not merely
`mapped_equivalent`, since no single "Gross Earnings" line existed in
that specific filing — so the precise retroactive count is **26
`direct_reported`, 3 `mapped_equivalent` (AFRIPRUD docs 4245, 6349's
revenue), 1 `derived` (AFRIPRUD doc 7540's revenue), 0 `interpretation`**.
This retroactive tagging is itself a concrete Phase 2 validation test
(§5).

## 3. Provenance fields (mandatory on every fact, restated precisely)

| Field | Existing column | Notes |
|---|---|---|
| Reported value | `extracted_facts.numeric_value` | Existing, unchanged |
| Mapped financial concept | `extracted_facts.fact_type` | Existing, unchanged — the canonical name (e.g. `assets`), never the filing's own label |
| Source document | `extracted_facts.doc_id` (+ `evidence.quoted_text` with the `[line N]` location convention from Phase 1) | Existing, unchanged |
| Period | `extracted_facts.period_start`/`.period_end` (Phase 1) **+ new `.period_type`** (§4.1) | One new column |
| Confidence | `extracted_facts.extraction_confidence` (numeric, existing) **+ new `.confidence_tier`** (§4.1, qualitative, this document) | One new column |
| Validation status | Embedded in `description` (Phase 1's convention) **+ new, queryable link for restatements** (§4.3) | One new mechanism |

## 4. Expected files changed (implementation phase, NOT this pass)

### 4.1 Schema (additive only, FRE-1/FSI-Phase-1 safe-migration pattern)

`schema/schema.sql` (fresh-DB path) + `src/ngxrot/db.py` (existing-DB
`ALTER TABLE ... ADD COLUMN` + `try/except OperationalError`, scratch
-copy-tested before the real DB, exactly as done twice already):

```sql
ALTER TABLE extracted_facts ADD COLUMN period_type TEXT
    CHECK (period_type IN ('Q1','Q2','Q3','Q4','H1','H2','9M','FY'));
ALTER TABLE extracted_facts ADD COLUMN confidence_tier TEXT
    CHECK (confidence_tier IN ('direct_reported','mapped_equivalent','derived','interpretation'));
ALTER TABLE extracted_facts ADD COLUMN restates_fact_id INTEGER
    REFERENCES extracted_facts(fact_id);
```

`restates_fact_id` is nullable, self-referencing, additive — modeled
directly on the existing `investment_implications.corroborates_
implication_id`/`.contradicts_implication_id` pattern (a proven,
already-audited design on this platform, not a new invention). A fact
with `restates_fact_id` set means "this fact restates an earlier one for
an overlapping period, at a different value" — both rows stand, exactly
like every other append-only table here.

### 4.2 Config (new files/leaves)

- `configs/fact_taxonomy.toml`: extend `[financial_statements]` with
  `assets`, `liabilities`, `equity`, `cfo`, `capex`, `fcf`, `ebitda`,
  `ebit` (8 new leaves — added as config once, ahead of the staged
  extraction work in §6, since a config addition is low-risk and
  reversible; **the extraction and writing of facts for each type still
  proceeds strictly in the priority order given**, not all at once).
- `configs/financial_statement_terminology.toml` (new): the synonym
  -mapping table sketched in the Phase 2 pre-registration §7, populated
  with Phase 1's confirmed real synonyms (`revenue` ← "Revenue"/
  "Turnover"/"Gross Earnings"/"Gross Revenue"; `net_profit` ←
  "Profit for the period"/"Profit for the year"/"Profit After Tax"/"PAT";
  `ebit` ← "EBIT"/"Operating Profit", with the equivalence caveat carried
  in the config itself, not just in prose).

### 4.3 New library code (`src/ngxrot/fre/`)

- `period_normalization.py` — `classify_period_type(period_start,
  period_end) -> str`: a pure function computing `period_type` from the
  actual date span (e.g., ~91 days → a quarter type needing the calendar
  position to disambiguate Q1-4; ~181 days → H1/H2; ~273 days → 9M;
  ~365 days → FY), never from a filing's own headline label. Read-only,
  no DB access needed for the core function.
- `terminology_mapping.py` — `map_label_to_concept(observed_label: str) ->
  str | None`: reads `configs/financial_statement_terminology.toml`,
  returns the canonical `fact_type` for a matched synonym or `None` if
  unmatched (never a guessed fallback).
- `restatement_detection.py` — `find_restatement_conflicts(con, ticker,
  fact_type, period_start, period_end, new_value) -> list[int]`:
  read-only query finding prior facts for the same ticker/fact_type with
  an overlapping period and a different value — the caller (the
  extraction script) decides whether to set `restates_fact_id`, this
  function only detects and reports candidates.

### 4.4 Extraction scripts (`scripts/fre/`)

- `fsi_scope_candidates_phase2.py` — extends Phase 1's scoping keyword
  set with balance-sheet ("total assets", "total liabilities", "total
  equity"/"shareholders' fund") and cash-flow ("cash flow from operating
  activities", "net cash from operating") terms.
- `fsi_extract_phase2.py` — the real extraction script, structured in
  **three independent sub-runs matching the priority order** (§6):
  `--stage balance_sheet`, `--stage cash_flow`, `--stage ebitda_ebit` —
  each independently dry-run-then-apply, each independently backed up,
  mirroring Phase 1's proven script pattern exactly.

### 4.5 New tests (`scripts/fre/`)

- `test_period_normalization.py` — including the retroactive UCAP "Q3
  2020 labeled, actually 9M" case as a named, permanent regression test.
- `test_terminology_mapping.py` — including AFRIPRUD's real Gross
  Earnings/Gross Revenue case, asserting the config-driven function
  reproduces Phase 1's hand-verified mapping exactly.
- `test_restatement_detection.py` — using CAP's real, confirmed FY2020
  comparative-vs-original discrepancy as the fixture.
- `test_fsi_extract_phase2.py` — per-stage extraction correctness,
  confidence-tier assignment correctness, accounting-identity checks.

### 4.6 Documentation

`docs/fre_runs/fsi_phase2_results.md` (future, per-stage results,
mirroring Phase 1's report structure).

## 5. Validation test plan

| Test | Purpose |
|---|---|
| Full existing regression suite (154/154 pipeline + 29/16/16/21/40 FRE-2..6) | Must stay green after every schema/code change, exactly as every prior phase required |
| `scripts/check_db_safety.py` | Unchanged, run before/after every write |
| Scratch-copy schema migration test (§4.1's three new columns) | Before touching the real DB, matching FRE-1/FSI-Phase-1's proven two-step (scratch, then real) pattern |
| Retroactive Phase 1 re-tagging test | Apply `classify_period_type`/confidence-tier logic to Phase 1's own 30 real facts; confirm the UCAP 9M-mislabeled case and the AFRIPRUD mapped/derived cases classify exactly as predicted in §2 |
| Per-stage accounting-identity check | `assets ≈ liabilities + equity` (±0.5%) for every extracted balance-sheet triple; `ebitda ≈ ebit + d_and_a` where both are available |
| Restatement-detection fixture test | CAP's real FY2020 case must be detected as a conflict candidate |
| Row-count / foreign-key-check before-after, every write | Unchanged discipline from every prior phase |

## 6. Build order vs. stated priority order (reconciled, not overridden)

The stated priority order (balance sheet → cash flow → EBITDA/EBIT →
period normalization → restatement handling → terminology mapping)
reflects analytical value. Three of those six items (period
normalization, restatement handling, terminology mapping) are
**cross-cutting infrastructure the first three items structurally depend
on** — balance-sheet extraction cannot be labeled with a correct
`period_type` or a correctly-mapped `fact_type` without that
infrastructure existing first. This plan therefore proposes:

1. Build the shared infrastructure once (§4.1 schema, §4.2 config, §4.3
   library code, §4.4's terminology/period/restatement pieces) —
   necessarily first, purely mechanical, not itself a "priority" in the
   analytical sense.
2. **Then** execute extraction strictly in the stated priority order —
   balance sheet first (its own dry-run, apply, and results sub-report),
   cash flow second, EBITDA/EBIT third — using the shared infrastructure
   built in step 1 throughout, with restatement-detection and
   terminology-mapping active from the very first stage (balance sheet),
   not bolted on afterward.

This is a sequencing clarification, not a deviation from the stated
priorities — every extraction decision still happens in the requested
order; only the shared plumbing beneath all three is built once, first.

## 7. Rollback plan

- **Schema**: automatic backup (`data/ngx.sqlite.pre_fsi_phase2_schema_backup_<date>`)
  before the migration, exactly as done for both Phase 1 schema steps;
  restore from backup if the scratch-copy test or the real-DB
  before/after verification finds any discrepancy.
- **Data (per extraction stage)**: every Phase 2 fact's `description`
  carries a distinct, greppable marker ("FSI Phase 2 pilot extraction,
  stage=<balance_sheet|cash_flow|ebitda_ebit>") — rollback of a single
  bad stage is `DELETE FROM extracted_facts WHERE description LIKE
  'FSI Phase 2%stage=balance_sheet%'` (and the matching `evidence` rows),
  never a blanket delete, never touching Phase 1's or any other phase's
  rows. A backup is also taken automatically before each stage's
  `--apply` run, exactly matching Phase 1's `fsi_extract_phase1.py`
  convention.
- **Config**: config files are pure additions (`financial_statement_
  terminology.toml` is new; `fact_taxonomy.toml`'s new leaves are
  additive) — rollback is reverting the file via git, no data
  implication.

## 8. Success criteria for THIS checkpoint (readiness to implement, not extraction results)

This checkpoint is ready for approval when, as delivered above: the exact
schema DDL is specified (§4.1); the confidence hierarchy is fully defined
with worked Phase 1 retroactive examples (§2); every expected file change
is named (§4); the validation test plan is concrete and includes
real-data fixtures already on hand (§5); the build-order/priority-order
tension is reconciled explicitly (§6); the rollback plan reuses only
already-proven mechanisms (§7). Extraction-result success criteria
(the 80%/70%/80%/80% thresholds per metric family) remain exactly as
pre-registered in `docs/fre_runs/fsi_phase2_preregistration.md` — this
checkpoint does not restate or alter them.

---

*Awaiting review of this implementation checkpoint before any schema
change, config file, or extraction code is created.*
