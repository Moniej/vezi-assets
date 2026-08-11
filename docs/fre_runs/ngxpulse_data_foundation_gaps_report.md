# NGX Pulse / Research OS -- Data-Foundation Gap Closure Report

**Date**: 2026-08-10
**Scope**: Closes the five data-foundation gaps named in the "Close the
Remaining Data-Foundation Gaps" directive, following the 2026-08-10
cross-validation report's `TRUSTED_WITH_CAVEATS` verdict
(`docs/fre_runs/ngxpulse_cross_validation_report.md`).
**Explicitly out of scope**: no alpha/momentum/relative-strength/sector-
ranking/volatility-factor/portfolio-construction/predictive-model work was
done or started. No PostgreSQL migration, no parallel database, no second
ingestion architecture, no backtest-engine rewrite. Architecture unchanged:
NGX Pulse -> `NGXPulseProvider` -> `DataProvider` -> `ingest.py` -> SQLite
PIT -> Research OS.

---

## 1. Corporate actions

**Finding, definitively closed this session**: both `ngx_pricelist_v2`
(this platform's primary reference) and `ngx_pulse` store **raw,
unadjusted** historical prices -- neither retroactively adjusts closes for
splits, bonuses, or rights issues. This was independently confirmed using
CILEASING's real 2-for-3 bonus issue (`extracted_facts.fact_id=350`,
factor 0.60, filed 2023-11-13): both sources show the identical raw
5.13->3.38 close-to-close jump on 2024-01-05. This closes the exact
question `docs/METHODOLOGY_HARDENING_2026-08-04.md` flagged as real but
"not numerically quantified" for lack of a clean example.

**Real, disclosed architecture gap found (not fixed, out of scope)**: the
`corporate_actions` table used by the quant/backtest layer contains only
31 synthetic fixture rows (`SYNBNKA/B/C`) -- zero real dividend or bonus
data. The FRE extraction layer's `extracted_facts` table separately holds
real bonus/rights-issue facts (NEM, CILEASING, NB, CHAMPION, CHIPLC,
ENAMELWA, GTCO) that have never been synchronized into `corporate_actions`.
These two representations are unconnected. No merge was performed --
reconciling them is a pipeline-design decision beyond "close the remaining
gaps," and is flagged here for an explicit future decision.

**Logged, not silently fixed**: `data_quality_log` now carries a
`check_name='unadjusted_jump'` entry for the CILEASING case
(`resolved=1`, references `fact_id=350`). Investigating this also surfaced
a **real, pre-existing finding**: the platform's own
`corporate_action_audit.py` tool has independently logged the identical
`unexplained_jump` for this exact observation **150+ times** between
2026-07-21 and 2026-08-08, every entry still `resolved=0`. This session's
new entry explains the cause but does not retroactively resolve those
pre-existing rows -- `src/ngxrot/lineage.py`'s tracing of this observation
therefore correctly reports `flagged_unresolved`, not resolved (see
Section 5). No bulk update of those 150 rows was performed (would be
altering pre-existing records outside this session's stated scope);
flagged here for a deliberate decision.

## 2. Instrument identity

Built `src/ngxrot/instrument_identity.py` (purely additive, read-only, zero
new schema -- reuses the existing `entities`/`entity_relationships`
`renamed_from` edges already present from earlier FRE work):

- `resolve_ticker_history_symbols(con, ticker)` walks a ticker's real
  rename chain and returns ordered `TickerEra`s. Verified against all
  three real rename chains in the database: GTCO<-GUARANTY (2021-06-24),
  ACCESSCORP<-ACCESS (2022-03-28), FIRSTHOLDCO<-FBNH (2025-03-10).
- `full_price_history_query(con, ticker, source_id)` returns a
  ready-to-run UNION ALL SQL string bridging every real symbol a security
  has traded under, tagging each row with its `original_ticker` (never
  relabeled) and a `canonical_ticker`.
- Confirmed the underlying gap this closes: neither `ngx_pricelist_v2` nor
  `ngx_pulse` bridges renames on their own -- GUARANTY's rows stop
  2021-06-17, GTCO's begin 2021-06-24, with nothing connecting them. A
  caller who only ever queries "GTCO" was silently missing 100% of its
  pre-2021-06-24 history until now.

Tests: `scripts/test_instrument_identity.py`, **20/20 passing**.

## 3. Data-quality framework

No new table. `data_quality_log` (pre-existing, 55,661 rows before this
session, platform-wide) already anticipated exactly the check names this
work needed (`'unadjusted_jump'`, `'stale_series'` are named directly in
its own `CREATE TABLE` comment). `scripts/ngxpulse_log_dq_findings.py`
appended 4 real, specific, non-fabricated rows (append-only -- nothing
updated or deleted):

| check_name | entity_code | trade_date | severity | resolved |
|---|---|---|---|---|
| `unadjusted_jump` | CILEASING | 2024-01-05 | info | 1 |
| `stale_series` | REDSTAREX | 2026-05-11 | warn | 0 |
| `date_attribution_drift` (new check_name, disclosed as new) | NESTLE | 2025-05-19 | warn | 0 |
| `unresolved_material_difference` (bulk summary) | MULTIPLE | NULL | info | 0 |

The bulk entry honestly discloses that only 2 of the 124 real
`MATERIAL_DIFFERENCE` observations from the cross-validation pass were
individually root-caused; the remaining ~122 are pointed at the full CSV
(`data/raw/cross_validation_full_overlap.csv`) rather than assumed benign
or silently dropped. `data_quality_log` now has **55,665 rows**.

## 4. Sector/universe metadata

The one remaining gap from the cross-validation report -- MCNICHOLS'
`securities.sector_ngx` was `NULL` (absent from the NGX Daily Official
List PDF `scripts/fre/populate_sector_ngx.py` transcribed, most likely
because MCNICHOLS lists on NGX's Growth Board, a section that PDF did not
cover). `scripts/ngxpulse_fill_mcnichols_sector.py`:

- Sourced `sector='CONSUMER GOODS'`, `market='Growth Board'` from NGX
  Pulse's own real, already-cached `/ngxdata/stocks` snapshot
  (`data/raw/stocks/2026-08-10.json`) -- no new API call.
- **Refuses to run** if the target field is not already `NULL` (verified:
  the script checks and would abort rather than overwrite).
- Filled `securities.sector_ngx` and inserted one
  `sector_ngx_provenance` row (existing table, reused, not extended).

Confirmed before/after: `NULL` -> `'CONSUMER GOODS'`.

## 5. Research-data lineage

Built `src/ngxrot/lineage.py` (read-only, zero new schema) with
`trace_equity_observation(con, ticker, trade_date)`, composing the full
chain **security -> source -> endpoint -> observation date -> ingestion
run -> validation status -> transformation** entirely from existing
columns:

- security/observation date: `equity_prices.ticker`/`trade_date`
- source/endpoint: `equity_prices.source_id` -> `sources.name/kind/
  reliability/url_template`
- ingestion run: composite `(source_id, as_of_date)` -- deliberately NOT a
  new `ingestion_runs` table (every row from one `ingest.py` invocation
  already shares both fields; adding a surrogate table would duplicate
  information already fully recoverable, which the "no second ingestion
  architecture" constraint argues against)
- validation status: live join against `data_quality_log` by
  `(entity_type='ticker', entity_code, trade_date)`, classified
  `no_flags_found` / `flagged_and_resolved` / `flagged_unresolved`
- transformation: none currently applied anywhere in this pipeline (raw
  prices in, raw prices out) -- itself a disclosed fact, not silently
  assumed

Tests: `scripts/test_lineage.py`, **10/10 passing**, including tracing the
real CILEASING and REDSTAREX findings logged in Section 3 and confirming
the 150-pre-existing-unresolved-flags finding from Section 1 surfaces
correctly as `flagged_unresolved` rather than being masked.

## 6. Regression check

Re-ran the full standalone test suites built earlier this session --
**no regressions**:

- `scripts/test_instrument_identity.py`: 20/20
- `scripts/test_ngxpulse_provider.py`: 31/31
- `scripts/test_lineage.py`: 10/10 (new)

## 7. Files changed this session (this stage only)

- `src/ngxrot/instrument_identity.py` (new)
- `src/ngxrot/lineage.py` (new)
- `scripts/test_instrument_identity.py` (new)
- `scripts/test_lineage.py` (new)
- `scripts/ngxpulse_log_dq_findings.py` (new)
- `scripts/ngxpulse_fill_mcnichols_sector.py` (new)
- `docs/fre_runs/ngxpulse_data_foundation_gaps_report.md` (this file, new)

No existing file was modified. No row in `equity_prices` or any other
observational table was updated or deleted. All writes were either
append-only (`data_quality_log`) or strictly NULL-fill with a refuse-if-
non-NULL guard (`securities.sector_ngx`).

## 8. Open items disclosed, not resolved (deliberately, out of scope)

- `corporate_actions` (quant layer) vs `extracted_facts` (FRE layer)
  desynchronization -- real, sizeable, unresolved.
- 150+ pre-existing unresolved `unexplained_jump` `data_quality_log`
  entries for CILEASING 2024-01-05, now explained but not marked
  resolved.
- ~122 of 124 cross-validation `MATERIAL_DIFFERENCE` observations remain
  individually untraced (logged in bulk, not resolved).
- REDSTAREX-style stale-price carryforward has only been directly
  confirmed for one ticker/window -- not yet bounded across the full
  NGX Pulse universe.

---

## STOP

Per the governing directive: **do not proceed into alpha research.** This
report closes the five named data-foundation gaps. The next phase should
only begin after an explicit decision that the Research OS/data foundation
is sufficiently reliable.
