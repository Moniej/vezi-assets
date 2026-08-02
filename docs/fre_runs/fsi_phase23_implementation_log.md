# FSI Phase 23 — Implementation Log

*Per `docs/fre_runs/fsi_phase23_preregistration.md`, the owner's
explicit authorization to introduce NGX's own official sector
classification, and the standing continuous-execution authorization
for everything else. Append-only.*

## Entry 0 — Verified the dataset-strategy doc's own assumption against a real filing, and found it wrong

Before acting, read NASCON's own FY2024 result-statement PDF
(`data/archive/xissuer_docs/25934_43267_..._FY_2024_RESULT_
STATEMENT..._MARCH_2025.pdf`) directly to test `docs/fre/
10_dataset_strategy.md`'s own claim that sector labels are a "free
side effect of processing existing filings." The filing states
NASCON's business in prose ("Nigeria's leading refiner and
distributor of... salt") but never an NGX-assigned sector code — the
assumption does not hold. This determined the real source had to come
from NGX's own published documents, not the archived filings.

## Entry 1 — Source search: two rejected candidates, one real official source found

`ngxpulse.ng`'s "NGX Listed Companies" page has a clean per-ticker
sector table, corroborated independently by NGX's own Weekly Market
Report (which names "Financial Services Industry"/"ICT Industry" in
its own official prose) — but rejected as the primary citation since
the page itself discloses it is "an independent tracking platform,"
not NGX's own data, and the owner's authorization specifically requires
the official classification. `ngxgroup.com`'s own live "Listed
Companies"/"Fact Sheet" pages are the real official source but are
JavaScript-rendered SPAs; the fetched HTML contained only a flat,
unsectored list — not usable. NGX's own **"Daily Official List
(Equities) For 21/04/2026"** PDF
(`https://doclib.ngxgroup.com/DownloadsContent/Daily%20Official%20List%20-%20Equities%20for%2021-04-2026.pdf`,
found via web search, never guessed) is the real source: a genuine,
official, static document, copyright "Nigerian Exchange (NGX)
Limited," organizing every listed equity under NGX's own 13 top-level
sector headings and named sub-industries, across the Main Board,
Premium Board, and REITCEF sections. WebFetch's own HTML/text
extraction could not parse this PDF's binary structure; the locally-
saved copy it produced was read directly instead via this session's
PDF-capable Read tool, and transcribed verbatim into
`scripts/fre/populate_sector_ngx.py`'s own `SECTOR_MAPPING`.

## Entry 2 — Schema addition and migration

Added `sector_ngx_provenance` to `schema/schema.sql` (one new table,
`CREATE TABLE IF NOT EXISTS`, zero modification to any existing
table) — full audit trail (source document, URL, retrieval date) for
every populated `sector_ngx` value, mirroring the same discipline
`extracted_facts`/`evidence` already establish elsewhere on this
platform. Applied to production via `db.init_db(db.DEFAULT_DB,
seed=False)`, preceded by a full backup
(`ngx.sqlite.pre_fsi_phase23_sector_ngx_backup_2026-08-02`).

## Entry 3 — Population, verified against the mapping's own real counts before running

136 unique tickers in `SECTOR_MAPPING`, zero duplicates, all 136
confirmed to match a real `securities.ticker` row before running the
actual population (checked programmatically, not assumed). Ran
`populate_sector_ngx.py` against production: 136 rows updated in
`securities.sector_ngx`, 136 matching rows written to
`sector_ngx_provenance`, 0 skipped. Confirmed directly: all 9 of 10
FSI tickers covered (MTNN=ICT, DANGCEM/CAP=INDUSTRIAL GOODS,
OANDO=OIL AND GAS, NESTLE/NASCON/BUAFOODS=CONSUMER GOODS,
UCAP/AFRIPRUD=FINANCIAL SERVICES); UBN is the one FSI ticker **not**
found in the source document and correctly remains `NULL` —
`securities.delisting_date`/`delisting_reason` for UBN are also both
`NULL` (no record either way on this platform), so no reason is
asserted, only the omission is disclosed.

A duplicate-case ticker oddity in the pre-existing `securities` table
was found and disclosed, not silently fixed: both `FIRSTHOLDCO` and
`FirstHoldCo` exist as separate rows. Only `FIRSTHOLDCO` (matching the
source document's own all-caps display convention) was populated;
`FirstHoldCo` was deliberately left untouched — a pre-existing
data-quality question for a future phase, not addressed here.

## Entry 4 — Readiness gates updated; no gated functionality activated

Three stale, now-factually-wrong "0/320 populated" claims were found
and corrected (disclosure only, no logic change in any case):
- `src/ngxrot/fre/valuation_engine.py`'s module docstring and
  `classify_company_type()`'s own docstring — updated to state the
  real 136/320 figure and explicitly confirm `classify_company_type()`
  does not consult `sector_ngx` at all, so its own behavior (GTCO →
  `"general"`) is unchanged; verified via `test_valuation_engine.py`,
  still 40/40 green including the corrected assertion.
- `src/ngxrot/lim/audit.py`'s `compute_audit()` `sector_distribution`
  fallback message — was asserting the stale platform-wide claim even
  though the function's own logic is parameterized (`sector_lookup`)
  and no caller currently wires it to `securities.sector_ngx` at all;
  corrected to describe the real current state without changing the
  function's actual behavior.
- `src/ngxrot/company_intelligence.py`'s `UNAVAILABLE_FIELDS["Industry
  Exposure"]` and `configs/company_type_overrides.toml`'s own comment —
  both updated to state 136/320, explicitly disclosing that partial
  coverage does **not** activate either "Industry Exposure" as a
  populated field or automatic sector-to-company-type classification;
  both remain deliberately unbuilt, a distinct design decision, not a
  data gap, going forward.
- `HANDOFF.md` (a live status doc, not a frozen phase snapshot) was
  also corrected for the same reason.
- `docs/fre/10_dataset_strategy.md`'s own inventory row was
  **deliberately NOT edited** — per `docs/fre/
  00_fre_master_index.md`'s own governing note, Parts 1-15 are
  retained unmodified as the frozen architectural reference, with
  divergence tracked in the master index's running status header
  instead (the same pattern this entire session has followed for
  every prior correction). The `not_started` → `partial` correction
  for "Sector classification" is recorded there, not in Part 10
  itself.

## Entry 5 — Full regression and validation (complete)

`scripts/fre/test_populate_sector_ngx.py` (new, 13/13): confirms the
real production state directly (136 populated, 136 provenance rows,
zero drift between them, UBN correctly `NULL`, every value one of
NGX's own 13 verbatim sector headings, every provenance row cites the
same real source URL), and separately re-exercises `populate()`'s own
logic on a disposable scratch copy (reset then repopulated) to prove
it is mechanically correct in isolation, not just consistent with
whatever is already in production.

Full regression: 33 test files (was 32), all green — including
`test_valuation_engine.py`'s corrected assertion. `check_db_safety.py`
PASS. `test_reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5 harness:
all 4 components PASS — Component 3 now correctly reports 31 tables
(was 30, the new `sector_ngx_provenance` table included), still
unchanged before/after.

**No modification to any existing table's rows outside `securities.
sector_ngx` itself, and no modification to any frozen module's actual
logic** — only disclosure-only docstring/comment corrections, verified
to change no function's behavior. The golden snapshot (137 facts / 267
conclusions) is unaffected (this phase adds no `extracted_facts`/
`financial_reasoning_conclusions` rows).

**FSI Phase 23 is now complete, validated, and documented.** Sector-
coverage view (Part 9's last Tier-1 item) is genuinely unblocked for
the first time in this program's history — built next, as Phase 24.
