# FSI Phase 7 — Final Report

*Deterministic Financial Reasoning Research Report. Prepared per the
owner's instruction to document, commit, and freeze this phase as a
baseline on completion. Full narrative and validation detail is in
`docs/fre_runs/fsi_phase7_implementation_log.md`; this report summarizes
outcomes.*

## Executive summary

FSI Phase 7 built `render_report(CompanyMemory360) -> str` — a pure,
deterministic, template-based Markdown renderer for Phase 6's unified
company memory snapshots. It introduces no new reasoning, inference,
scoring, ranking, summarization, health assessment, or investment
interpretation of any kind, and calls no LLM. Every sentence in the
output is a direct restatement of a field already stored in
`financial_reasoning_conclusions`, `extracted_facts`, or
`CompanyMemory`. Neither of the two underlying modules (`company_
memory.py`, `pit_financial_memory.py`) nor their Phase 6 composition
(`company_memory_360.py`) was modified.

## Files created (deliverables)

- **Report generator module**: `src/ngxrot/fre/
  financial_reasoning_report.py`.
- **Fixed report template**: implemented as a single, disclosed Markdown
  structure inside `render_report()` (Filing History → Dividend History
  → Corporate Action History → Management History → Major Event
  History → Corporate Memory Coverage Notes → Ratios → Trends → Flags →
  Financial Reasoning Coverage Notes) — a fixed section order, never
  varied per ticker or per data content.
- **Tests for deterministic output**: `scripts/fre/test_financial_
  reasoning_report.py` (13 assertions).
- **Documentation**: this report plus the implementation log.
- **Implementation log**: `docs/fre_runs/fsi_phase7_implementation_log.md`.

**No schema change. No modification to any of the six frozen FSI/FRE-3
modules.**

## Requirement-by-requirement results

1. **Generated entirely from existing structured fields.** Confirmed by
   code review — the renderer's only inputs are `CompanyMemory360`'s own
   fields; nothing is computed or looked up independently.
2. **Every statement traceable to stored data.** Verified directly: for
   every real conclusion across all 5 tickers, its own `method` and
   `limitations` text appears verbatim in the rendered report (a direct
   substring check, not a sampling spot-check).
3. **No LLM calls.** Confirmed — the module imports no LLM provider,
   makes no network call; it is pure string formatting.
4. **No generated explanations beyond fixed template substitution.**
   Confirmed by code review — every line is an f-string substitution of
   an existing field, with fixed connective text only ("Status:",
   "Confidence tier:", etc.).
5. **Every confidence tier preserved, including `NULL` legacy
   confidence.** Confirmed: a `NULL` tier renders as an explicit
   "confidence tier NOT RECORDED" phrase (never omitted, never
   presented as equivalent to a real tier) — verified present in real
   output.
6. **All citations, provenance, filing dates, and limitations preserved
   exactly as stored.** Every conclusion's source facts (`fact_id`,
   `role`, `fact_type`, `doc_id`, `filing_date`) are rendered in full;
   every filing/dividend/corporate-action fact's own `doc_id`/`fact_id`
   appears in the report — confirmed by a field-coverage check across
   all 5 real tickers.
7. **Missing data never hidden.** Every `insufficient_data` conclusion
   appears in the report with its own limitations text — verified by an
   exact count match between each snapshot and its own rendered report
   (not merely "at least one appeared").
8. **No reordering to imply importance.** Corporate-memory sections
   preserve `company_memory.py`'s own existing chronological order;
   financial-reasoning conclusions use exactly one neutral, disclosed
   rule (alphabetical by metric, then by period_end) — verified
   mechanically against Python's own `sorted()` on the same key.
9. **Zero database writes.** Confirmed — all 29 tables' row counts
   unchanged before/after the full test run.
10. **No schema changes.** Confirmed — no `CREATE TABLE`/`ALTER TABLE`
    statement exists anywhere in this phase's code.

## Validation results

- **Sentence-to-field mapping demonstrated**: every conclusion's
  `method`/`limitations` text found verbatim in its own report, for all
  5 real tickers.
- **Determinism verified two ways**: (a) rendering the same snapshot
  object 3 times produces byte-identical output; (b) building two
  independent snapshots of the same `(ticker, as_of_date)` and rendering
  both also produces byte-identical output — confirming determinism
  holds through the full pipeline (Phase 4 → Phase 6 → Phase 7), not
  just within the renderer itself.
- **Full regression suite**: all 12 prior FSI Phase 1-6 test files (165
  assertions) plus the new 13-assertion test file, plus
  `check_db_safety.py`, `test_reasoning_pipeline.py`, and FRE-2 through
  FRE-6 (FRE-6 unchanged at 40/40). Phase 5's own validation harness was
  re-run after implementation and still reports PASS on all three
  components.
- **Database immutability**: confirmed before and after execution —
  `PRAGMA integrity_check` → `ok`; `PRAGMA foreign_key_check` → clean;
  all 29 tables' row counts unchanged.

## A real finding during test development, disclosed rather than hidden

While building the forbidden-vocabulary mechanical check (proving no
ranking/scoring/recommendation language leaks into the report), an
initial substring-based version produced a **false positive**: it
flagged the word "rating" inside the real, approved financial term
"Operating Profit," and flagged "rank"/"score" inside the report's own
required disclaimer sentence (which legitimately states "no ranking...
no health score" to describe what the report does NOT contain). Fixed
by excluding the disclaimer sentence from the scan and using whole-word
matching for the three ambiguous terms. Disclosed here as a genuine
test-development finding, consistent with this program's practice of
reporting what was actually found while building validation, not just
the final passing result.

## Known limitations

- **The report is only as complete as `CompanyMemory360`'s own
  disclosed gaps** — `management_history`/`major_event_history` remain
  empty (FRE-3's own systemic, disclosed gap), and Phase 4's
  zero-linked-fact fallback rules still apply unchanged; the report
  states these explicitly (inherited from the underlying coverage
  notes) rather than presenting a falsely-complete picture.
- **Markdown only** — no PDF/HTML/other output format was built; a
  future phase could add additional renderers over the same
  `CompanyMemory360` input without touching this one.
- **No cross-report comparison tooling** — by design; a future consumer
  wanting to compare two tickers' reports side by side would need to
  do so manually, since this phase deliberately builds no such
  capability.

## Recommendations for the next phase

1. If a future phase adds new conclusion types to Phase 3's frozen rule
   set (via a new `rule_version`, without modifying frozen code), this
   renderer would need no change — it renders whatever `conclusion_type`
   values exist, generically, for `ratio`/`trend`/`flag`; a genuinely
   new fourth type would need a new section added deliberately, not
   silently.
2. Continue the standing discipline: any future "investment reasoning
   layer" remains subject to the same exclusions restated across all
   seven approvals — no alpha, ranking, scoring, or unsupported
   conclusion.

---

**FSI Phase 7 is complete: fully implemented, validated, and
documented.** Per the governing instruction, implementation stops here
automatically, awaiting the owner's review before any subsequent phase
begins.
