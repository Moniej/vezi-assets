# FSI Phase 23 — Final Report

*Sector Classification Data. Full narrative in
`docs/fre_runs/fsi_phase23_implementation_log.md`.*

## Executive summary

FSI Phase 23 populated `securities.sector_ngx` for 136 of 320 real
securities (including 9 of the 10 real FSI tickers) from NGX's own
official "Daily Official List (Equities)" — a genuine, primary,
exchange-authoritative document, introduced per the owner's explicit
authorization as reference metadata distinct from this platform's
analytical/investment-data boundary. This closes the single most-cited
data blocker across the entire FRE/FSI program (named as such since
Phase 9/10) and genuinely unblocks Part 9's Sector-coverage view, the
last unbuilt Tier-1 capability, for the first time in this program's
history.

## A wrong assumption found and corrected before acting

`docs/fre/10_dataset_strategy.md` assumed sector labels would be a
"free side effect" of the filings already archived. This phase
checked that assumption against a real filing (NASCON's FY2024 result
statement) before proceeding and found it false — NGX's sector
taxonomy is published separately from individual company filings. The
real source (NGX's own Daily Official List PDF) was found via web
search after two other candidates were tried and rejected (a
third-party aggregator with the right labels but the wrong
authority; NGX's own live pages, which are JavaScript-rendered and
unscrapeable with this session's tooling).

## Files created/modified

- `schema/schema.sql`: one new table, `sector_ngx_provenance`
  (additive).
- `scripts/fre/populate_sector_ngx.py` (new): the literal, disclosed
  ticker→sector mapping transcribed from NGX's own official document,
  plus the population logic.
- `scripts/fre/test_populate_sector_ngx.py` (new, 13 assertions).
- Disclosure-only corrections (no logic change, verified via
  regression) to three stale "0/320" claims: `valuation_engine.py`,
  `lim/audit.py`, `company_intelligence.py`, plus
  `configs/company_type_overrides.toml` and `HANDOFF.md`.
- This report, the implementation log, and the pre-registration.

**No modification to any existing table's rows outside `securities.
sector_ngx`, and no modification to any frozen module's actual
behavior** — confirmed via full regression, including the corrected
`test_valuation_engine.py` assertion.

## Results

- 136/320 real securities populated, each with a full provenance row
  (source document, URL, retrieval date) — confirmed zero drift
  between `securities.sector_ngx` and its own `sector_ngx_provenance`
  row for every ticker.
- Every populated value is one of NGX's own 13 top-level sector
  headings, verbatim — never normalized, reformatted, or invented.
- 9 of 10 FSI tickers covered; UBN is the one not found in the source
  document and correctly left `NULL`, disclosed rather than guessed
  (no delisting record exists on this platform either way).
- 183 unmatched securities are, by category: bonds/ETFs/synthetic
  placeholders (not equities), pre-rename ticker aliases already
  superseded by Phase 9's own edges, and real tickers simply absent
  from this document (most plausibly delisted/suspended, not
  asserted). A pre-existing `FIRSTHOLDCO`/`FirstHoldCo` duplicate-case
  ticker oddity was found and disclosed, not silently resolved.
- Full regression (33 test files, up from 32), `check_db_safety.py`,
  `test_reasoning_pipeline.py`, and Phase 5's harness (4 components,
  now 31 tables) all pass.

## Readiness gates updated; nothing activated without genuine cause

Three stale "0/320" claims were corrected for factual accuracy
(`valuation_engine.py`, `lim/audit.py`, `company_intelligence.py`,
plus a config comment and `HANDOFF.md`) — in every case, verified that
the underlying function's actual behavior is unchanged; partial
sector coverage does not by itself activate automatic company-type
classification, Industry Exposure profiling, or LIM sector-distribution
auditing, since none of those have logic wired to consume `sector_ngx`
yet. `docs/fre/10_dataset_strategy.md` (Part 10 of the frozen
architecture) was deliberately **not** edited, per this platform's own
standing discipline of leaving Parts 1-15 unmodified and tracking
divergence in the master index instead.

## Status: Part 9's last blocker is resolved

Sector-coverage view — the one Part 9 Tier-1 capability that has sat
on the externally-blocked list through every phase since 14 — is now
genuinely buildable. This phase does not build it (data population and
its consuming capability are kept as separate phases, matching this
session's own established build-then-consume pattern); it is Phase
24, next.

---

**FSI Phase 23 is complete: fully implemented, validated, and
documented.**
