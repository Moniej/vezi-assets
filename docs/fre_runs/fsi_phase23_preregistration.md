# FSI Phase 23 — Pre-registration

*Sector Classification Data (`securities.sector_ngx`). Per the owner's
explicit authorization to introduce this one external data source
(exchange-authoritative reference metadata, not analytical data), and
the standing continuous-execution authorization for everything else.*

## Gap identified, and why the platform's own prior assumption was wrong

`securities.sector_ngx` has been 0/320 populated since before this
entire FSI track began — named in every phase's own review since
Phase 9/10 as "the single most-cited blocker across this whole
program" (`docs/fre/10_dataset_strategy.md` line 38) and the reason
Part 9's Sector-coverage view has stayed permanently on the
"externally blocked" list through Phases 19-22's own audits.

That dataset-strategy document assumed sector labels would be a "free
side effect of processing existing filings" (`docs/fre/
10_dataset_strategy.md`: "Entity-extraction side effect of processing
existing filings — no new document source needed"). This phase
checked that assumption against a real filing before acting on it
(NASCON's own FY2024 result-statement PDF, `data/archive/xissuer_docs/
25934_43267_..._FY_2024_RESULT_STATEMENT..._MARCH_2025.pdf`) and found
it does **not** hold: the filing describes NASCON's business in prose
("Nigeria's leading refiner and distributor of... salt") but never
states an NGX-assigned sector code. NGX's own sector taxonomy lives on
NGX's own published documents, not inside individual result-statement
filings.

## Owner authorization and its exact scope

The owner explicitly authorized introducing NGX's own official sector
classification as an external data source, on these terms: it is
exchange-authoritative reference metadata (like a ticker symbol or
ISIN), not analytical/investment data, so it sits outside the
platform's "never invent alpha" boundary the same way `securities.
isin`/`securities.board` already do. Explicit requirements, followed
exactly:

- Official NGX classification only, never inferred from company
  descriptions/business summaries.
- Full provenance per row (source, retrieval date, document/URL).
- Additive, fully auditable.
- Only verified values populated; unverifiable tickers left `NULL`
  and disclosed, never guessed.
- Full regression/integrity/PIT validation after the change.
- Update readiness gates that depend on `sector_ngx`, but do not
  activate gated functionality unless genuinely unblocked.
- Document exactly what becomes available vs. what remains blocked.

## Source found and verified

Two candidate sources were tried and rejected before finding the real
one:

1. **ngxpulse.ng's "NGX Listed Companies" page** — has a clean
   per-ticker sector column, and its labels are corroborated by NGX's
   own official terminology (confirmed independently via NGX's own
   Weekly Market Report, which names "Financial Services Industry,"
   "ICT Industry," "Services Industry" in its own prose). Rejected as
   the primary source anyway because the page itself discloses it is
   "an independent tracking platform," not NGX's own data — the owner's
   instruction requires the official classification specifically.
2. **ngxgroup.com's own live "Listed Companies"/"Fact Sheet" pages** —
   these are the real, official NGX source, but are JavaScript-rendered
   single-page apps; the fetched HTML contains only a flat, unsectored
   ticker/price list, with sector data loaded dynamically in a way this
   session's tooling cannot execute. Not usable as a scrapeable static
   source.
3. **NGX's own "Daily Official List (Equities)" PDF**
   (`https://doclib.ngxgroup.com/DownloadsContent/Daily%20Official%20List%20-%20Equities%20for%2021-04-2026.pdf`,
   found via web search, not guessed) — **this is the real source
   used.** A genuine, official, static, primary-source document,
   copyrighted "Nigerian Exchange (NGX) Limited," organizing every
   listed equity under NGX's own 13 top-level sector headings
   (AGRICULTURE, CONGLOMERATES, CONSTRUCTION/REAL ESTATE, CONSUMER
   GOODS, FINANCIAL SERVICES, HEALTHCARE, ICT, INDUSTRIAL GOODS,
   INVESTMENT, NATURAL RESOURCES, OIL AND GAS, SERVICES, UTILITIES)
   and named sub-industries beneath each, across the Main Board,
   Premium Board, and REITCEF sections — read via this session's
   PDF-capable Read tool directly (WebFetch's own HTML conversion
   could not parse this PDF's binary structure; the file it saved
   locally was read directly instead).

## Scope of this phase

- **137 of 320** real securities were found in this document with an
  exact, unambiguous ticker match and are populated with NGX's own
  top-level sector label, verbatim (e.g. `CONSUMER GOODS`, `FINANCIAL
  SERVICES`) — the sub-industry (e.g. "Food Products") is also
  recorded, in the new provenance table only, not in `securities.
  sector_ngx` itself (Part 9's own design names only the top-level
  field).
- **All 9 of the 10 FSI tickers** are covered: MTNN (ICT), DANGCEM
  (INDUSTRIAL GOODS), OANDO (OIL AND GAS), NESTLE (CONSUMER GOODS),
  NASCON (CONSUMER GOODS), UCAP (FINANCIAL SERVICES), CAP (INDUSTRIAL
  GOODS), BUAFOODS (CONSUMER GOODS), AFRIPRUD (FINANCIAL SERVICES).
- **UBN is the one FSI ticker NOT found** in this document — disclosed,
  not guessed. `securities.delisting_date`/`delisting_reason` for UBN
  are also both `NULL` (this platform has no record either way), so
  the reason is genuinely unconfirmed; `sector_ngx` stays `NULL` for
  UBN rather than assuming a delisting or picking a plausible sector.
- **The remaining 183 unmatched securities** are, by category: bond/
  ETF/synthetic-placeholder tickers (`FGS*`, `FG*`, `TAJSUKS*`,
  `SYN*`, `VET*`, `NEWGOLD`, etc. — not equities, correctly out of
  scope for an equity sector taxonomy); pre-rename ticker aliases
  already superseded by Phase 9's own `renamed_from` edges (`GUARANTY`,
  `ACCESS`, `FO`, `UBCAP` — the document lists only the current
  post-rename symbols, so matching an old alias to the new symbol's
  sector would be an inference beyond direct document matching, not
  performed here); and a large set of real tickers simply absent from
  this specific document (most plausibly delisted/suspended small-caps
  — Nigerian-market small-cap suspensions are common — but this phase
  does not assert that reason for any specific ticker without its own
  confirming source). All left `NULL`, disclosed in aggregate here
  rather than asserted individually.
- A duplicate-case oddity in the existing `securities` table was found
  and disclosed, not silently fixed: both `FIRSTHOLDCO` and
  `FirstHoldCo` exist as separate ticker rows. The document's own
  display convention is all-caps; only `FIRSTHOLDCO` is populated,
  `FirstHoldCo` is left `NULL` — a pre-existing data-quality question
  for a future phase, not touched here.

## Design

- New table `sector_ngx_provenance` (additive,
  `CREATE TABLE IF NOT EXISTS`): `ticker` (FK `securities`),
  `sector_ngx`, `sub_industry`, `board_section`, `source_document`,
  `source_url`, `retrieval_date`. One row per populated ticker — the
  full audit trail this platform requires for every consequential
  value, mirroring the discipline `extracted_facts`/`evidence` already
  established (never a bare value with no traceable source).
- `securities.sector_ngx` itself is updated via a plain `UPDATE`, only
  for the 137 verified tickers — `securities.board` is explicitly
  **not** touched this phase, even though the same document also shows
  board section (Main/Premium/REITCEF); that is a distinct field this
  task was not scoped to touch, left for a future phase if wanted.
- New one-time script `scripts/fre/populate_sector_ngx.py`, mirroring
  Phase 9's `populate_entities_and_relationships`-style one-time
  data-loading precedent: the full ticker→(sector, sub_industry,
  board_section) mapping is a literal, disclosed dict in the script
  itself (matching how Phase 9's `symbol_renames.csv`-sourced mapping
  was disclosed directly in its own script), backs up the production
  database first, applies the schema migration, then performs the
  `UPDATE`s and provenance `INSERT`s in one pass.

## Readiness gates updated, activation explicitly withheld where not ready

- `docs/fre/10_dataset_strategy.md`'s own inventory row for "Sector
  classification" is updated from `not_started` to `partial` (137/320,
  not all 320 — never claimed complete).
- Sector-coverage view (Part 9 Tier 1's last item) is **not** built in
  this same phase — this phase is data population only, matching this
  session's own established build-then-consume separation (Phase 9's
  data → Phase 10's consumption; Phase 17's read → Phase 20's wiring;
  Phase 18's persistence → Phase 21's CLI). It becomes the immediately
  obvious next phase (Phase 24), not activated here.
- `valuation_engine.py`'s `classify_company_type()` and the ≥2-
  validated-factor gate for Portfolio Construction/Part 9 Tier 2 are
  explicitly **not** affected — sector data was never their blocker
  (a validated quant factor is), and this phase does not touch either.

## Guardrails (mechanically verified, not just asserted)

- Every populated `sector_ngx` value has a matching
  `sector_ngx_provenance` row citing the same source document/URL/
  retrieval date — checked directly, not assumed.
- Every value written matches, byte-for-byte, one of NGX's own 13
  top-level sector headings from the source document — no normalized/
  reformatted/invented label.
- Confirmed zero rows were written for any ticker not present in this
  exact document (no inference for the 183 unmatched, including UBN).
- Full regression, `check_db_safety.py`, `test_reasoning_pipeline.py`,
  and Phase 5's harness all re-run after the schema change and data
  population.

## Expected outcome

`securities.sector_ngx` populated for 137/320 real equities (including
9 of 10 FSI tickers), each with a fully cited provenance row; one new
additive table; `docs/fre/10_dataset_strategy.md`'s own maturity marker
corrected from `not_started` to `partial`. Sector-coverage view (Part
9's last Tier-1 item) becomes genuinely buildable for the first time
in this program's history — built next, as Phase 24, not bundled into
this one.
