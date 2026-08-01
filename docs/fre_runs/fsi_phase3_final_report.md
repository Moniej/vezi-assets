# FSI Phase 3 — Final Report

*Financial Reasoning over Validated Facts. Prepared per the owner's
instruction to document results and freeze this phase as a baseline on
completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase3_implementation_log.md`; this report summarizes
outcomes.*

## Executive summary

FSI Phase 3 transformed the 106 validated financial-statement facts
frozen in `fsi-phase2-baseline-2026-08-01` into 177 structured,
provenance-linked analytical conclusions — 75 deterministic ratios, 87
trend classifications, and 15 rule-based financial-health flags — for
all 5 tickers, in the exact build order specified: (1) deterministic
financial metric calculations, (2) trend classification, (3) financial
health flags, (4) evidence-linked reasoning context. No new fact types,
no new documents, no valuation output, no alpha claim, no portfolio
ranking, no cross-company scoring, and no LLM call anywhere in the
implementation — every conclusion is mechanically computed and
mechanically reproducible. The optional narrative reasoning layer named
in the pre-registration was not built, remains gated, and requires its
own future authorization.

## Files created

- `src/ngxrot/fre/confidence_propagation.py` — shared NULL-aware
  "weakest tier wins" helper.
- `src/ngxrot/fre/period_normalization.py` — extended (additive) with
  `periods_overlap()`.
- `src/ngxrot/fre/financial_ratios.py` — Step 1.
- `src/ngxrot/fre/trend_classification.py` — Step 2.
- `src/ngxrot/fre/financial_health_flags.py` — Step 3.
- `src/ngxrot/fre/reasoning_context.py` — Step 4 (read-only).
- `scripts/fre/fsi_phase3_compute_metrics.py`,
  `fsi_phase3_classify_trends.py`, `fsi_phase3_compute_flags.py` —
  dry-run/`--apply` driver scripts, matching the established convention.
- `scripts/fre/test_confidence_propagation.py`, `test_periods_overlap.py`,
  `test_financial_ratios.py`, `test_trend_classification.py`,
  `test_financial_health_flags.py`, `test_reasoning_context.py`.
- `docs/fre_runs/fsi_phase3_implementation_log.md` (this phase's live
  journal), `fsi_phase3_final_report.md` (this document).

## Schema changes

Two new, additive tables (no existing table modified):

```sql
financial_reasoning_conclusions (
    conclusion_id, ticker, conclusion_type ['ratio'|'trend'|'flag'],
    metric, status ['computed'|'insufficient_data'], value_numeric,
    value_text, confidence_tier [nullable], method, limitations,
    rule_version, period_start, period_end, computed_at
)
financial_reasoning_conclusion_facts (
    conclusion_id, fact_id, role   -- join table, full source-fact traceability
)
```

Applied to production via `db.init_db(seed=False)` after scratch-copy
verification, backup: `data/ngx.sqlite.pre_fsi_phase3_schema_backup_
2026-08-01`.

## Results

| Step | Conclusions written | Computed | Insufficient data |
|---|---|---|---|
| 1. Ratios (debt_to_equity, ebitda_margin, ebit_margin, net_margin, cfo_to_net_profit) | 75 | 54 | 21 |
| 2. Trends (12 raw fact_types + 5 ratio metrics) | 87 | 87 | 0 (no row is written where no valid non-overlapping pair exists at all) |
| 3. Flags (leverage_increasing, cash_flow_earnings_divergence, margin_compression) | 15 | 12 | 3 |
| **Total** | **177** | **153** | **24** |

**Real, disclosed findings, not manufactured to demonstrate the
mechanism**:
- NASCON's `leverage_increasing` flag genuinely **fires** — real
  `debt_to_equity` rose from 0.823 (FY2024) to 0.900 (FY2025), +9.36%.
- AFRIPRUD's `margin_compression` flag genuinely **fires** — both its
  `ebitda_margin` and `net_margin` trends are `decreasing` across its
  own 2 available periods.
- BUAFOODS's `cash_flow_earnings_divergence` does **not** fire on its
  one available real ratio (~1.51, above the 1.0 threshold) — a
  negative check that could have fired but didn't.
- `cash_flow_earnings_divergence` is correctly `insufficient_data` for
  AFRIPRUD, CAP, and UCAP — none ever had a `cfo` fact extracted in
  Phase 2, a real rule-applicability gap, not a silent skip.
- NASCON's H1-2024-vs-FY2024 overlapping periods correctly produce
  exactly ONE trend pair (FY2024→FY2025), not two — the exact case that
  exposed FSI Phase 2's restatement-detection defect, this time handled
  correctly from the start by reusing `periods_overlap()`.

## Confidence propagation, verified

`debt_to_equity` is `direct_reported` throughout (both its inputs are
Stage-2 direct facts). Every ratio/trend touching `revenue` or
`net_profit` — Phase 1's original 30 legacy facts, which predate the
`confidence_tier` column and were never backfilled — correctly floors to
`NULL`, never silently upgraded. `confidence_tier='interpretation'`
occurs 0 times in `financial_reasoning_conclusions`, matching the hard
rule already enforced in `extracted_facts`.

## Guardrail verification (Area 7 — single-company scope)

Mechanically audited, not just asserted: across all four new modules,
zero public functions accept more than one ticker parameter, and no
dataclass field name suggests a ranking, comparison, or peer score. No
cross-ticker comparative output exists anywhere in this phase's code or
data.

## Regression and integrity results

Full suite passes: `check_db_safety.py`, `test_reasoning_pipeline.py`,
all prior FRE-2 through FRE-6 suites (FRE-6 40/40, unchanged — Phase 3
writes zero rows to `extracted_facts`, so no stale-assertion update was
needed, unlike every stage of Phase 2), plus all 6 new Phase 3 test
files (12+8+11+11+9+6 = 57 checks, all passing). `PRAGMA integrity_check`
→ `ok`; `PRAGMA foreign_key_check` → clean, database-wide; `documents`
unchanged at 11,533; `extracted_facts` unchanged at 267.

## Known limitations

- **Trend windows remain short** (at most 2 valid pairs per ticker,
  since each ticker has only 3 real periods and at most one pair is ever
  excluded for overlap) — a real, structural constraint of the
  underlying dataset, not something Phase 3 can improve without more
  filings.
- **The starter rule set (3 flags) is a reasoned, not empirically
  validated, choice** — `rule_version='flags_v1'` exists specifically so
  a future correction is a new, disclosed version, never a silent
  redefinition of history.
- **The optional narrative ("why") layer was not built** — Areas 1-3's
  mechanical output is the entire scored deliverable of this phase; a
  future narrative layer remains its own, separately-gated decision
  requiring an LLM vendor/cost decision not resolved here.
- **`insufficient_data` is a per-ticker, not a per-company-permanent,
  state** — if a future phase extracts more financial-statement facts
  for a currently-gapped ticker/metric (e.g. AFRIPRUD's cash flow),
  these conclusions would need to be recomputed under a new
  `rule_version`/run, not retroactively edited.

## Recommendations for the next phase

1. If more filings are added for any of the 5 tickers, rerun Steps 1-3
   to extend trend windows — the code already discovers periods
   dynamically, no logic change is needed for additional data.
2. The optional narrative layer (Area 4b) remains the most natural next
   increment, but requires its own pre-registration and an LLM vendor/
   cost decision, exactly as flagged in the Phase 3 pre-registration.
3. Continue the discipline used throughout: any change to shared,
   already-approved modules (e.g. `periods_overlap()`,
   `confidence_propagation.py`) found necessary in a future phase should
   be treated as a potential architectural blocker requiring the same
   stop-document-approve pattern used for the Phase 2 restatement-
   detection correction.

---

**FSI Phase 3 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
