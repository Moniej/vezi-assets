# FSI Phase 3 — Implementation Log

*Live journal, appended to throughout implementation, not reconstructed
afterward. Per `docs/fre_runs/fsi_phase3_preregistration.md` (approved)
and the owner's implementation-order instruction. Append-only, matching
this program's own data discipline applied to its own documentation.*

## Entry 0 — Start

Implementation begins exactly per the approved pre-registration and the
owner's explicit build order: (1) deterministic financial metric
calculations, (2) trend classification, (3) financial health flags, (4)
evidence-linked reasoning context. No new fact types, no new document
ingestion, no valuation output, no alpha claims, no portfolio ranking,
no cross-company scoring, no LLM-generated financial conclusions as
primary outputs. Any narrative reasoning layer remains optional and
separately gated (not built in this pass). Builds on the frozen
`fsi-phase2-baseline-2026-08-01` dataset (106 financial-statement facts,
5 tickers).

## Entry 1 — Shared infrastructure: schema + helpers (in progress)

Two new, additive tables proposed in the pre-registration's Area 6 are
being added: `financial_reasoning_conclusions` (one row per derived
ratio/trend/flag, with `confidence_tier` nullable — a NULL result is a
meaningful "floor is unknown" signal, not an error, propagated from
Phase 1's own un-backfilled legacy facts) and
`financial_reasoning_conclusion_facts` (a join table, not a free-text
blob, for full source-fact traceability per the pre-registration's own
explicit requirement). Both additive-only, following the exact FRE-1/
FSI-Phase-1/2 pattern (`schema/schema.sql` for fresh DBs,
`src/ngxrot/db.py`'s `init_db()` `ALTER TABLE`/`CREATE TABLE IF NOT
EXISTS` for the existing production DB).

Two small, additive shared helpers: `confidence_propagation.py` (the
NULL-aware "weakest tier wins" rule from the pre-registration's Area 1)
and a new `periods_overlap()` function added to the existing, already-
approved `period_normalization.py` (needed so trend classification never
compares two periods that overlap in calendar time but represent
different reporting spans — e.g. NASCON's own H1 2024 vs FY2024 — the
exact real case that caused the restatement-detection false positive
corrected in FSI Phase 2 Entry 5; this reuses that lesson rather than
re-deriving it).

**Verification, in order**: (1) scratch-copy migration — 267 rows before/
after across `extracted_facts`/`evidence`/`documents`, two new tables
created (`financial_reasoning_conclusions`, `financial_reasoning_
conclusion_facts`), `foreign_key_check`/`integrity_check` clean; (2) real-
DB application via `db.init_db(seed=False)` — same checks, all pass,
backup taken first (`data/ngx.sqlite.pre_fsi_phase3_schema_backup_
2026-08-01`); (3) `test_confidence_propagation.py` 9/9 and `test_periods_
overlap.py` 6/6, both validated against the real NASCON H1-2024-vs-FY2024
case. **Entry 1 complete.**

## Entry 2 — Step 1: deterministic financial metric calculations (complete)

`src/ngxrot/fre/financial_ratios.py` computes `debt_to_equity`,
`ebitda_margin`, `ebit_margin`, `net_margin`, `cfo_to_net_profit` for
every ticker and every one of that ticker's own real reporting periods —
discovered dynamically from `extracted_facts`, never hardcoded (a
deliberate contrast with Phase 1/2's extraction scripts, which hardcoded
manually-transcribed filing values; Phase 3 computes over already-stored
facts programmatically instead). A ratio is only computed from a
numerator and denominator sharing the EXACT SAME (ticker, fact_type,
period_start, period_end) — reusing the "equivalent reporting spans"
discipline from the restatement-detection fix, applied here for a third
purpose (detection, trend-pairing, and now ratio validity all rest on the
same underlying idea: a calculation is only meaningful across facts that
describe the identical reporting span).

**Confidence propagation applied and verified**: `debt_to_equity` is
`direct_reported` throughout (both `liabilities`/`equity` are Stage-2
direct facts); every ratio involving `revenue` or `net_profit` (Phase 1
legacy, `NULL` tier) correctly floors to `NULL`, not silently upgraded —
confirmed for CAP FY2020's real `ebit_margin` (1,645mn / 8,737mn =
18.83%, hand-verified) by direct test assertion.

**Real, disclosed `insufficient_data` cases, exactly as expected from
Phase 2's own known gaps**: CAP FY2020 `debt_to_equity` (doc 4508 has no
balance-sheet data at all), every ticker's `cfo_to_net_profit` where no
`cfo` fact exists (AFRIPRUD all 3 periods, CAP all 3, UCAP all 3 — banks
and these two tickers never had cash-flow data extracted in Phase 2),
UCAP's `ebitda_margin`/`ebit_margin` in all 3 periods (a bank — no
ebit/ebitda ever, by Stage 4's own disclosed architectural boundary).

Dry-run then `--apply` (backup: `data/ngx.sqlite.pre_fsi_phase3_metrics_
backup_2026-08-01`): 75 new `financial_reasoning_conclusions` rows (54
computed + 21 insufficient_data), 128 new `financial_reasoning_
conclusion_facts` rows, `extracted_facts`/`documents` unchanged,
`foreign_key_check` clean. `test_financial_ratios.py` 12/12.

## Entry 3 — Step 2: trend classification (complete)

`src/ngxrot/fre/trend_classification.py` classifies `increasing` /
`decreasing` / `stable` direction (a disclosed ±5% threshold for
`stable`) across every NON-OVERLAPPING pair of a ticker's own real
periods, for both the 12 raw fact_types and the 5 Step-1 ratio metrics.
Deliberately neutral vocabulary throughout — never "improving"/
"deteriorating" — per the pre-registration's own resolution of an
internal tension in its own Area 2 wording (an earlier draft phrase
suggested value-laden labels; the design's own explicit "does NOT infer
whether a direction is favorable" sentence governs, and is what was
actually implemented).

**The central regression target, verified directly**: NASCON is the
only ticker among the 5 with two periods that overlap in calendar time
(H1 2024 and FY2024) — `periods_overlap()` correctly excludes this pair,
so NASCON's `revenue` (and every other metric) trend has exactly ONE
valid pair (FY2024→FY2025), not two. Confirmed by test assertion, not
just visual inspection of the dry-run output. UCAP, by contrast, has 3
real non-overlapping periods (2020, 2022, 2025) and correctly produces 2
valid trend pairs per metric.

Dry-run then `--apply` (backup: `data/ngx.sqlite.pre_fsi_phase3_trends_
backup_2026-08-01`): 87 new conclusions, all `status='computed'` (a
trend is either computable from two real non-overlapping periods or it
doesn't exist at all — there is no "insufficient_data" trend row, by
construction: `_classify_points` simply produces fewer results when
fewer valid pairs exist, e.g. UCAP has zero `ebit`/`ebitda` trend rows
because it has zero `ebit`/`ebitda` facts to compare, not a disclosed gap
row). `foreign_key_check` clean. `test_trend_classification.py` 8/8.

## Entry 4 — Step 3: financial health flags (complete)

`src/ngxrot/fre/financial_health_flags.py` evaluates exactly 3 named,
disclosed rules per ticker — `leverage_increasing` (most recent
`debt_to_equity` trend = increasing), `cash_flow_earnings_divergence`
(most recent `cfo_to_net_profit` ratio < 1.0), `margin_compression` (most
recent `ebitda_margin` or `net_margin` trend = decreasing) — reading only
Step 1/2's already-written conclusions, no free-text judgment anywhere.

**Real flags fired, disclosed as genuine findings, not manufactured to
demonstrate the mechanism**: NASCON's `leverage_increasing` FIRES (real
`debt_to_equity` rose from 0.823 to 0.900, FY2024→FY2025, a genuine
+9.36% increase); AFRIPRUD's `margin_compression` FIRES (both its
`ebitda_margin` and `net_margin` trends are `decreasing` across its own
2 available periods). BUAFOODS's `cash_flow_earnings_divergence` does
NOT fire on its one available real ratio (~1.51, above the 1.0
threshold) — a real negative-finding check that could have fired but
didn't, confirming the rule isn't tuned to always trigger.
`cash_flow_earnings_divergence` is correctly `insufficient_data` for
AFRIPRUD, CAP, and UCAP (none ever had a `cfo` fact extracted in Phase
2) — a real, disclosed rule-applicability gap, not a silent skip.

Dry-run then `--apply` (backup: `data/ngx.sqlite.pre_fsi_phase3_flags_
backup_2026-08-01`): 15 new conclusions (12 computed + 3
insufficient_data — one per ticker with no `cfo` ratio). `foreign_key_
check` clean. `test_financial_health_flags.py` 11/11.

## Entry 5 — Step 4: evidence-linked reasoning context (complete)

`src/ngxrot/fre/reasoning_context.py` is entirely read-only — it writes
nothing, calls no LLM, generates no new text. Given any `conclusion_id`,
it assembles the full structured trail: every linked `extracted_facts`
row (via `financial_reasoning_conclusion_facts`), each fact's own
`evidence` row (quoted filing text, page number) where one exists, and
the source `documents` row (ticker, filing_date, doc_type). This is the
non-generative half of the pre-registration's Area 4; the optional
narrative ("why") layer remains unbuilt and separately gated, exactly as
instructed — no LLM call exists anywhere in this module or in Steps 1-3.

**Single-company-scope guardrail, verified mechanically, not just
promised**: audited all four Phase 3 modules
(`financial_ratios`/`trend_classification`/`financial_health_flags`/
`reasoning_context`) via `inspect.signature` — zero public functions
accept more than one ticker parameter, and neither `ReasoningContext`
nor `SourceFactContext` carries any field name suggesting a ranking,
comparison, or peer score. This is the concrete acceptance check the
pre-registration's Area 7 called for, not a docstring-only assurance.

`test_reasoning_context.py` 11/11 (validated against CAP's real FY2020
`ebit_margin` conclusion, tracing correctly back to doc 4508's own two
source facts).

## Entry 6 — Full regression and integrity verification (complete)

Full suite: `check_db_safety.py` PASS, `test_reasoning_pipeline.py` ALL
CHECKS PASSED, `test_period_normalization.py` 23/23, `test_periods_
overlap.py` 6/6, `test_terminology_mapping.py` 8/8, `test_restatement_
detection.py` 9/9, `test_confidence_propagation.py` 9/9, `test_financial_
ratios.py` 12/12, `test_trend_classification.py` 8/8, `test_financial_
health_flags.py` 11/11, `test_reasoning_context.py` 11/11, FRE-2 29/29,
FRE-3 16/16, FRE-4 16/16, FRE-5 21/21, **FRE-6 40/40 with NO stale-
assertion update needed this time** — Phase 3 writes zero rows to
`extracted_facts`, so FRE-6's financial-statement-fact-count assertion
(106) is correctly untouched by this phase, unlike every stage of Phase
2.

**Full integrity verification**: `PRAGMA integrity_check` → `ok`;
`PRAGMA foreign_key_check` → clean, database-wide; `documents` unchanged
at 11,533; `extracted_facts` unchanged at 267 (Phase 3 never writes to
this table); `financial_reasoning_conclusions` = 177 (75 ratio + 87 trend
+ 15 flag), `financial_reasoning_conclusion_facts` = 418;
`confidence_tier='interpretation'` count is exactly 0 (the hard rule
holds in this new table too, not just `extracted_facts`).

**FSI Phase 3 (Steps 1-4 of the approved build order) is now complete,
validated, and documented.** Proceeding to the final report, then
freezing this baseline per the owner's instruction.
