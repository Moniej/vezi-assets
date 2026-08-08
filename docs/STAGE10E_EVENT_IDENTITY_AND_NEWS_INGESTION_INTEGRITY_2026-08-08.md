# Stage 10E — Event Identity & News Ingestion Integrity

**Date:** 2026-08-08
**Scope:** `src/ngxrot/event_pipeline.py` dedup/conflict logic only. No changes to H-011, no backtest, no factor construction, no large-scale scraping, no new hypothesis. All tests below are read-only against the live database (`validate_batch()` performs no writes; `ingest_events()`, the only writer, was never called in this stage).

---

## 1. Root cause (confirmed, not re-derived from memory — re-read from source this stage)

`validate_batch()`'s natural key for both within-batch and vs-DB duplicate detection was, until the fix applied in the prior turn, `(event_type, announced_date, scope, index_code)` — four columns, omitting `ticker`. Every event source that had ever used this pipeline before Stage 10D (`scripts/ingest_events.py`, `scripts/ingest_mpc.py`, `scripts/scrape_cbn_mpc.py` — confirmed via grep to be the only three callers of `validate_batch`/`ingest_events`) submitted only `scope='market'` or `scope='sector'` rows, where `ticker` is NULL on every row and `index_code` (or its absence) already differentiated distinct rows. The gap was invisible for nine stages because nothing had ever submitted a `scope='ticker'` batch.

Stage 10D was the first ticker-scoped submission (MarketForces Africa's Sept 1, 2025 article naming three suspended insurers). Two of the three named companies, REGALINS and UNIVINSURE, share `event_type='regulatory_action'`, `announced_date='2025-09-01'`, `scope='ticker'`, `index_code=NULL` — identical under the old 4-column key. UNIVINSURE's real, distinct event was rejected as a false-positive "duplicate" of REGALINS's.

## 2. Exact change applied

`src/ngxrot/event_pipeline.py`:
- Module docstring (lines 14-20): documents the new key shape and the no-op guarantee for market/sector-scoped rows.
- Within-batch dedup (line 132): `key = ["event_type", "announced_date", "scope", "index_code", "ticker"]`.
- Vs-DB existing-row query and match filter (lines 140-153): `existing` now selects `e.ticker`; the match filter adds `& (existing.ticker.fillna("") == str(r.get("ticker") or ""))`, using the same NaN-safe `fillna` pattern already used for `effective_date`/`direction` comparisons elsewhere in the same function — not a new pattern introduced for this fix.

No schema change was made. `schema/schema.sql`'s `ix_events_dates` index (`(announced_date, event_type)`) is confirmed (re-read this stage) to be a query-performance index, not a uniqueness constraint — all dedup logic lives in application code, so no migration was needed or performed.

**Why ticker-addition is safe for every pre-existing source:** for `scope='market'`/`scope='sector'` rows, `ticker` is NULL on both sides of every comparison. pandas' `duplicated()` treats `NaN == NaN` as equal (so within-batch grouping is unchanged), and the vs-DB filter's `fillna("") == fillna("")` reduces both sides to `""` (also unchanged). This is verified empirically in Tests 4 and 5 below, not just asserted from reading the code.

## 3. Regression tests — all 8 executed, read-only, zero writes

Test harness: `validate_batch()` called directly against the live `data/ngx.sqlite` with synthetic and real-replay batches. Confirmed after the run: `SELECT COUNT(*) FROM events WHERE ticker LIKE 'TEST%'` → 0, `event_uid LIKE 'test_%'` → 0, total `events` row count unchanged at 159. No `ingest_events()` call was made at any point in this stage.

| # | Test | Result | Interpretation |
|---|------|--------|-----------------|
| 1 | Two distinct tickers (TESTALPHA, TESTBETA), same type/date/scope, one batch | `accepted=2, rejected=0` | The bug shape itself, now fixed: two different companies sharing type/date no longer collide. |
| 2 | Same ticker (TESTALPHA), same type/date, submitted twice in one batch | `accepted=1, rejected=1` — 2nd row: "duplicate natural key within batch" | A true same-ticker duplicate is still correctly caught. The fix narrows what counts as a duplicate; it does not weaken duplicate detection. |
| 3 | REGALINS+UNIVINSURE resubmitted verbatim (same source, same event_uid, same headline) | `accepted=0, rejected=2`, both `REJECT`: "already ingested from this source with identical payload" | Real-data replay of the fix's own subject: both events are now recognized as pre-existing, ticker-differentiated rows (no false new-collision). Originally (before the §9 fix, applied later in this same stage) this test misfired as `RESTATEMENT`; re-run after the fix now correctly resolves to `REJECT` — see §9. |
| 4 | Two market-scoped rows (`ticker=NULL` both), same type/date | `accepted=1, rejected=1` — 2nd row: "duplicate natural key within batch" | Confirms the fix is a no-op for market-scoped data: behavior is bit-for-bit identical to pre-fix (both rows collide, exactly as they would have on the old 4-column key). |
| 5a | Two sector-scoped rows, different `index_code` (NGXBNK vs NGXINS), same type/date | `accepted=2, rejected=0` | `index_code` alone still differentiates sector rows; ticker addition changes nothing here (both NULL). |
| 5b | Two sector-scoped rows, same `index_code`, same type/date | `accepted=1, rejected=1` | Confirms sector-scoped collision behavior is unchanged from pre-fix. |
| 6 | Same ticker, same type, different dates | `accepted=2, rejected=0` | Sanity check: different `announced_date` was never a duplicate condition and still isn't. |
| 7 | One article naming 3 companies → how many events actually exist | DB query: only REGALINS and UNIVINSURE tickers present for this `event_uid` prefix; International Energy Insurance Plc (the article's 3rd named company) confirmed absent | Consistent with Stage 10D's disclosed scope (only 2 of 3 named companies were ever mapped to a ticker and ingested) — not a dedup artifact. No 3rd row was fabricated to "complete" the set. |
| 8 | Same economic event, 2nd hypothetical outlet, different `event_uid`, same payload | `accepted=1, rejected=0`, flagged `CONFLICT`: "existing source(s) ['stage10c_news_pilot'] disagree on effective_date/direction — both preserved; resolve by confidence, never by deletion" | Cross-outlet re-reporting of the same real-world event does not silently collapse into a duplicate reject, and does not silently overwrite — it is preserved as a logged conflict for confidence-based resolution later, per the pipeline's stated design (docstring §"conflicts"). No cross-outlet duplicate currently exists in the DB (only one news source, MarketForces, has been ingested so far), so this is necessarily a synthetic second-outlet test, disclosed as such. |

## 4. Document-duplication vs. economic-event-duplication (10E-D)

These are deliberately different concepts in this pipeline and must not be collapsed:

- **Document duplication** — the same physical article/filing being fetched or processed twice (e.g., the same URL scraped twice). This is not `event_pipeline.py`'s concern at all; it is a `documents` table / ingestion-provider concern (out of scope for this fix).
- **Economic-event duplication** — two *rows* in `events` claiming to describe the same real-world occurrence. This is what `validate_batch()` guards, and the two required behaviors are opposite:
  - **REGALINS + UNIVINSURE** (Test 1/3/7): one document, two distinct real-world events (two different companies suspended). Correct behavior: **2 event rows**. The pre-fix bug collapsed this to 1 row — the exact defect fixed.
  - **VERITASKAP Q3 2024, multi-outlet** (Stage 10C's own example, re-cited here as the required contrast case): the same real-world event reported by more than one outlet. Correct behavior: **1 economic event**, with subsequent reports handled via the uid/source-matching logic — either recognized as the same source's restatement (uid match) or preserved as a cross-source conflict (Test 8, above) — never silently duplicated into 2+ rows for the same underlying fact. This is now formally demonstrated (Test 8) rather than only asserted from Stage 10C's narrative account.

The ticker-key fix only touches the first case (identity across *different* real-world subjects sharing a date/type). It does not alter, and was never intended to alter, the second case (same subject, multiple sources) — that logic (uid-match → restate/reject; no-uid-match → conflict) is unchanged and pre-existing.

## 5. PIT integrity verification (10E-E)

Checked directly against `events` rows 168 (REGALINS) and 169 (UNIVINSURE), the two real rows the fix exists to protect:

| Field | 168 (REGALINS) | 169 (UNIVINSURE) | PIT-relevant? |
|---|---|---|---|
| `announced_date` | 2025-09-01 | 2025-09-01 | Yes — matches the article's own stated effective date, not a later processing date. |
| `effective_date` | 2025-09-01 | 2025-09-01 | Yes — suspension effective date, correctly same-day. |
| `ticker` | REGALINS | UNIVINSURE | The new differentiator — confirmed distinct and correctly attributed, not swapped or blank. |
| `event_type` / `scope` | regulatory_action / ticker | regulatory_action / ticker | Correctly ticker-scoped, not misfiled as market/sector. |
| `event_uid` | `news_marketforces_2025-09-01_regalins_suspension` | `news_marketforces_2025-09-01_univinsure_suspension` | Distinct per-ticker uids — this is what makes both restatable/resolvable independently going forward. |
| `source_id` | 16 (`stage10c_news_pilot`) | 16 | Same source, correctly shared (one article, one source record). |
| `as_of_date` | 2026-08-08 | 2026-08-08 | Correct — reflects actual ingestion date, not backdated to the announcement date (no look-ahead fabrication). |
| `confidence` | inherited from source | inherited from source | Unaffected by this fix; not a dedup concern. |

No field was altered by the ticker-key fix itself — the fix changes only which rows are *accepted*, not what is written once accepted. Both rows' PIT fields were already correct at insertion (Stage 10D); this stage re-verifies rather than re-derives that.

## 6. Historical collision audit (10E-F)

Query run (read-only, against the full `events` table, using the OLD 4-column key to find every pre-fix collision-equivalence class):

```sql
SELECT event_type, announced_date, scope, index_code, COUNT(*) n, GROUP_CONCAT(ticker) tickers
FROM events GROUP BY event_type, announced_date, scope, index_code HAVING n>1
```

**3 groups found, all individually investigated. No records have been modified.**

1. **`regulatory_action`, 2025-09-01, scope=ticker, tickers=REGALINS/UNIVINSURE** — the fix's own known subject. Both are genuine, distinct real events (two different insurers suspended the same day for the same regulatory reason). **Correctly resolved by the ticker-key fix; no remediation needed.**

2. **`recapitalisation_directive`, 2024-03-28, scope=sector, index_code=NGXBNK, n=2, tickers=NULL/NULL** — investigated by reading both full rows (event_id 63, 64). Event 63: `source_id=4` (`synthetic_dev`), headline "Synthetic: minimum capital directive for banks", `notes=NULL`. Event 64: `source_id=7` (`manual_primary_verified`), headline is the real CBN N500bn/N200bn/N50bn directive, `notes`: "Verified 2026-07-15 against CBN circular PDF (primary) and same-day reports by Nairametrics and Channels TV (secondary)." **This is intentional, disclosed synthetic/real coexistence** — the synthetic row is explicitly labeled as such and traceable to a distinct, disclosed source (`synthetic_dev`), consistent with the platform's own pre-existing "synthetic data isolated from evidence" design. **Not a bug. No remediation needed.** The ticker-key fix is a no-op here (no ticker involved; the differentiator that should exist is `source_id`/data-provenance labeling, which is already correct — `synthetic_dev` vs `manual_primary_verified` are unambiguous).

3. **`mpc_decision`, 2014-01-21, scope=market, index_code=NULL, n=2, tickers=NULL/NULL — UNRESOLVED, genuine anomaly, remediation candidate.** Full row comparison (event_id 154, 156):
   - Both: `source_id=10`, `source_url='https://www.cbn.gov.ng/monetarypolicy/decisions.html'`, `as_of_date='2026-07-16'` (**identical** — both parsed in the same ingestion run, not two captures over time), `notes='Parsed from CBN decisions page 2026-07-16; meeting no. unstated; CRR_DMB=None'` (**identical text**), `event_uid='CBN-MPC-2014-01-21'` (**identical**).
   - They differ only in `headline`/`outcome_numeric`: event 154 states "MPR retained at 30.00%" (`outcome_numeric=30.0`), event 156 states "MPR retained at 12.00%" (`outcome_numeric=12.0`).
   - This is **not** the same shape as the RESTATEMENT-preservation pattern (which exists to protect legitimate corrections captured at *different* times/lineages) — both rows share the same `as_of_date`, same source, same event_uid, and were evidently produced by the **same parsing run**, meaning the pipeline's uid-restatement path (append rather than reject, because `outcome_numeric` differed) fired for what looks like an internal parsing inconsistency, not a genuine two-vintage correction. Two contradictory MPR readings for one stated meeting date is not, on its face, a plausible pair of real, distinct events.
   - I am not able to determine from data alone in this archive which value (if either) is correct — I have not queried an external CBN historical-rate source in this stage, and doing so would exceed 10E's scope. I will only note, as an unverified plausibility observation and not a certified fact: Nigeria's MPR is commonly documented as having held at 12.00% through most of 2014, which makes the 30.00% row *look* anomalous, but I have not verified this against a primary source in this session and it should not be treated as confirmed.
   - **Classification: UNKNOWN — likely a same-batch scraper/parsing defect in the original CBN MPC ingestion (Stage/source predates this project's Stage 1-10 work; `source_id=10` and `as_of_date=2026-07-16` predate Stage 10), not caused by and not fixed by the ticker-key change (both rows have `ticker=NULL`, so the fix is a no-op here).**
   - **No remediation has been performed.** Per the explicit instruction to stop and report before modifying: the two exact candidate rows are `event_id=154` (30.00%) and `event_id=156` (12.00%), both `mpc_decision`/2014-01-21/market/NULL, same `event_uid`. Recommended next step (not taken): re-fetch the CBN decisions page's historical record for this date, or check for an independent secondary source, before deciding whether one row should be superseded (never deleted, per the pipeline's append-only/PIT design) with a corrected uid or explicit deprecation note.

**Summary for 10E-F:** the ticker-key fix's blast radius is confirmed to be exactly the REGALINS/UNIVINSURE pair — no other historical collision in the database was caused by, or is fixed by, the ticker addition. One additional, unrelated, pre-existing data-quality anomaly (`mpc_decision` 2014-01-21) was surfaced by the same audit query; it is out of scope for this fix, unresolved, and explicitly not remediated in this session.

## 7. News-document vs. economic-event dedup — summary finding

Confirmed via Tests 1/2/3/7/8 and the taxonomy walkthrough in §4: the pipeline correctly treats "one document, multiple subjects" (REGALINS+UNIVINSURE) as multiple events, and is designed (though only synthetically tested here, since no second real outlet has been ingested yet) to treat "multiple documents, one subject" as one event, via uid-restatement or source-conflict preservation rather than duplication. Document-level duplicate fetches are not this pipeline's concern and were not tested here (out of scope — belongs to the ingestion-provider layer, not `event_pipeline.py`).

## 8. What was NOT done (explicit scope discipline)

- H-011 config, prereg, and signal construction: untouched.
- No H-018/H-019 created.
- No backtest, no factor, no alpha claim.
- No large-scale scraping — this stage ran zero new fetches; all tests used synthetic rows or already-archived text.
- No new database table created.
- No manual insertion used as a substitute for the underlying fix — the actual `validate_batch()` logic was changed; nothing was patched around it.
- The `mpc_decision` 2014-01-21 anomaly and the `RESTATEMENT`-vs-`REJECT` ambiguity found in Test 3 (§9) were **not** silently fixed — both are reported, neither is remediated.

## 9. Second fix applied this stage: NULL-outcome identical-payload bug

**Found via Test 3** (not previously known): the "already ingested, identical payload" check in `validate_batch()` compared `outcome_numeric` via `prior_uid.outcome_numeric.astype(float).round(4) == round(float(r.get("outcome_numeric") or 0), 4)`. When the true stored value is `NULL` (as it is for both REGALINS and UNIVINSURE — qualitative regulatory events with no numeric outcome), `astype(float)` on `None` yields `NaN`, and `NaN == 0` is `False` regardless of the resubmitted row's own value. Effect: verbatim resubmission of an already-ingested `outcome_numeric IS NULL` event was misclassified as `RESTATEMENT` (appended as a "changed" row) instead of correctly `REJECT`ed as an identical repeat. This did not corrupt PIT data (append-only; a spurious restatement just adds a redundant row, never overwrites), but would have let exact duplicate re-scrapes silently accumulate.

**Fix applied** (`src/ngxrot/event_pipeline.py`, same section, ~line 169): replaced the float-coercion comparison with a NaN-safe `_outcome_matches()` helper — both-NULL now compares equal, one-NULL-one-numeric compares unequal, both-numeric compares as before (rounded to 4dp).

**Verified**, read-only, zero writes:
- Test 3 re-run post-fix: `accepted=0, rejected=2`, both `REJECT: "already ingested from this source with identical payload"` — correct.
- All other 7 tests re-run unchanged (identical accept/reject counts and messages to the pre-fix run) — confirms no regression from this second fix.
- Edge case: same uid, real payload change (different `outcome_numeric`) still correctly surfaces via the restatement/conflict path, not silently dropped.
- Edge case: prior `outcome_numeric IS NULL`, resubmission carries a real number — correctly resolves `RESTATEMENT` (genuinely different), not falsely `REJECT`ed as identical.
- `SELECT COUNT(*) FROM events` unchanged at 159 before and after all testing in this stage.

The `mpc_decision` 2014-01-21 anomaly (§6, item 3) is unrelated to this fix (both rows have `ticker=NULL` and differ in `outcome_numeric`, so they would never have been misclassified as "identical" by the bug just fixed) and **remains genuinely unresolved and UNKNOWN** — no remediation performed, per the standing instruction to stop and report before modifying historical records.

## 10. Remediation of the `mpc_decision` 2014-01-21 anomaly (post-decision addendum, 2026-08-08)

This section is appended after §6 identified the anomaly as UNKNOWN and stopped short of remediation. It does not alter §1-10 above (the original investigation is preserved as written); it records the separate, explicitly-authorized follow-up.

### 10.1 Further investigation (before any write)

Four additional, independent checks were run, all read-only, before concluding:

1. **Full trend re-check**: every `mpc_decision` event 2013-01-21 through 2014-11-25 (12 meetings) holds MPR at 12.00% except the November 2014 hike to 13.00% — 2014-01-21's `event_id=154` (30.00%) is the only value inconsistent with this run.
2. **Canonical batch file re-confirmed**: `data/events_batches/cbn_mpc/events/mpc_decisions_2026-07-16.csv` — the file both event_id 154 and 156's own `notes` field cites as their provenance — contains exactly one row for 2014-01-21, `outcome_numeric=12.0`. No 30.0 row exists in this file, nor in any other checked-in `.py/.csv/.json/.md/.sql` file in the repository (confirmed by full-repo grep for the literal headline text "MPR retained at 30").
3. **Scraper logic re-read**: `scripts/scrape_cbn_mpc.py` isolates the `<li>` clause naming "Monetary Policy Rate"/"MPR" specifically to avoid the corridor/Liquidity-Ratio percentages that appear in the same communiqués, and runs its own hold-vs-previous-level consistency check (would flag "hold at 30.0 but previous was 12.0"). The current script could not have produced `event_id=154`.
4. **External corroboration** (`WebSearch`, no robots.txt-restricted fetch performed): CBN's own published record confirms the January 20-21, 2014 MPC meeting retained MPR at 12% (±200bps corridor) while separately maintaining the **Liquidity Ratio at 30%** and raising public-sector CRR from 50% to 75%. This directly explains the mechanism: 30.00% is a real figure from that meeting, but it is the Liquidity Ratio, not the MPR — `event_id=154`'s headline mislabels it.

Conclusion: `event_id=156` (12.00%) is correct; `event_id=154` (30.00%, labeled "MPR") is a data-entry/mislabeling error, not a legitimate second reading and not a genuine economic restatement.

### 10.2 Correction mechanism selected

Before writing anything, the existing taxonomy (`configs/event_taxonomy.toml`, 8 categories: monetary/banking/commodity/corporate/macro/market_structure/insurance/pension) and schema (`events` table, `schema/schema.sql`) were checked for a dedicated correction/deprecation construct. **None exists** — there is no `data_correction` event type, and no status/lifecycle column beyond `event_uid`+`as_of_date` (the mechanism `docs` already describes as "restatements share the uid; PIT reads keep the latest as_of per uid" and that `src/ngxrot/db.py`'s `events_asof()` implements). `data_quality_log`'s `entity_type` column is `CHECK`-constrained to `('index','ticker')` only, so it cannot cleanly represent an event-level correction either.

The uid-sharing mechanism is therefore the only existing construct the architecture supports for "supersede this record's informational content without deleting it." It was reused, via the **standard ingestion path already established by this project's own precedent**: `scripts/ingest_events.py`'s `CSVProvider` + `event_pipeline.ingest_events()`, the same mechanism previously used for `data/events_seed/events/mpc_gapfill_2026-07-16.csv` (a hand-verified gap-fill row, source `manual_primary_verified`, `source_id=7`) and for the real `recapitalisation_directive` row (`event_id=64`, same source). A new, isolated batch directory `data/events_corrections/events/mpc_dq_correction_2026-08-08.csv` was created (separate from `events_seed` so the correction batch would not re-submit unrelated pre-existing CSVs in the same run) containing one row:

- `event_type=mpc_decision`, `event_uid=CBN-MPC-2014-01-21` (shared with 154/156, so it joins their PIT group)
- `announced_date=2014-01-21`, `effective_date=2014-01-21`, `scope=market` (matches the original pair)
- `headline`: "DATA QUALITY CORRECTION of event_id=154: MPR retained at 12.00% on 2014-01-21, not 30.00%"
- `outcome_numeric=12.00`
- `outcome_text=data_quality_correction` — a plain-text marker, chosen specifically because `outcome_text` has no `CHECK` constraint and is otherwise used for values like `'hold'`/`'hike +50bps'`; this value is deliberately never used for a genuine economic outcome, making it a queryable structural marker distinguishing corrections from real captures/restatements without any schema change.
- `notes`: the full evidentiary chain from §10.1, explicit cross-reference to `event_id=154` (original, erroneous) and `event_id=156` (already-correct), and an explicit statement that this is a data-quality correction, not an economic restatement.
- Source: `manual_primary_verified` (`source_id=7`, reused via `ingest.register_provider()`'s name-keyed idempotent lookup — confirmed no duplicate source row was created) — chosen deliberately over reusing `cbn_decisions_page` (`source_id=10`, the original scrape's source), because this row was not produced by a fresh scrape; attributing it to the scrape source would have been a false provenance claim. `manual_primary_verified` is this project's own pre-existing, disclosed convention for exactly this situation (see the gap-fill and recapitalisation-directive precedents above).

**Disclosed limitation found while doing this** (not fixed, out of scope for a remediation task): `validate_batch()`'s vs-DB uid-restatement/reject logic (§lines ~157-181) is gated on `same_src = m[m.src == r.get("_source_name","")]` — it only recognizes a submission as touching an existing uid group (and emits a `RESTATEMENT`/`REJECT` label) when the new row's source name matches the existing rows' source name. Because this correction intentionally uses a different, honestly-disclosed source, it fell through to the bottom silent-accept path (no `CONFLICT`, since `effective_date`/`direction` agree) rather than emitting an explicit `RESTATEMENT` label in the ingestion report. **This did not block or corrupt the write** — the row was accepted and correctly shares the uid — but it means cross-source corrections/restatements are not currently flagged as distinctly in the pipeline's own report text as same-source ones are. This is a real, pre-existing gap in `validate_batch()`'s reporting granularity, disclosed here per the standing instruction, not remediated (out of scope for this task).

### 10.3 Write executed

`event_pipeline.ingest_events(con, CSVProvider('data/events_corrections', name='manual_primary_verified', base_confidence=0.7), start='2014-01-01', end='2014-01-31')` — the standard path, not a raw `INSERT`. Quality report: `reports/event_quality_2026-08-08.md` (batch rows=1, accepted=1, rejected=0, issues=0).

### 10.4 Mandatory verification — all performed, all pass

| Check | Result |
|---|---|
| Event 154 remains present, unmodified | `SELECT * FROM events WHERE event_id=154` → headline "MPC: MPR retained at 30.00%", `outcome_numeric=30.0`, `source_id=10` — identical to pre-remediation. |
| Event 156 remains present, unmodified | `SELECT * FROM events WHERE event_id=156` → headline "MPC: MPR retained at 12.00%", `outcome_numeric=12.0`, `source_id=10` — identical to pre-remediation. |
| Row count before/after | 159 → 160. Exactly one new row (`event_id=170`). |
| Unrelated rows unchanged | Spot-checked event_id 83, 93 (surrounding MPC meetings), 168, 169 (REGALINS/UNIVINSURE), 1 (earliest MPC row) — all identical to their pre-remediation values. |
| Downstream PIT query no longer resolves 30.00% as current MPR | `ngxrot.db.events_asof(con, '2026-08-08', event_types=['mpc_decision'])` for `announced_date='2014-01-21'` now returns exactly one row: `event_id=170`, `outcome_numeric=12.0`. (Note: even *before* remediation, `events_asof()`'s `ORDER BY as_of_date DESC, event_id DESC` tiebreak already incidentally resolved this uid group to `event_id=156`, 12.0 — not 154 — since 154 and 156 share an identical `as_of_date` and 156 has the higher `event_id`. The 30.00% value was therefore never actually surfaced by this specific downstream function, even pre-remediation. Remediation nonetheless makes this correct-by-design rather than correct-by-accidental-tiebreak, and gives the group an explicit, evidenced correction record rather than an unexplained duplicate.) |
| PIT vintage behavior intact | `events_asof(con, '2026-08-08', vintage='2026-08-07')` (a vintage predating this correction's `as_of_date`) correctly still resolves to `event_id=156` — the correction is invisible to any point-in-time query taken before it existed, and does not retroactively alter what an earlier-vintage query would have seen. |
| `events_asof()` row count for `mpc_decision` unaffected | 142 rows both before and after remediation — the uid group still resolves to exactly one row, no duplication introduced into the PIT-current view. |
| Correction has proper provenance | `source_id=7` (`manual_primary_verified`) — reused via idempotent name lookup, no duplicate source row created (`sources` table row count unaffected); full evidentiary chain in `notes`; batch file `data/events_corrections/events/mpc_dq_correction_2026-08-08.csv` retained on disk as a permanent, disclosed artifact. |
| 8-test regression suite still passes post-remediation | Re-ran all 8 tests from §3 — identical accept/reject counts and messages to the pre-remediation run. No regression from this write. |
| Genuine restatements still distinguishable from data-quality corrections | Two checks: (a) a synthetic same-source (`cbn_decisions_page`) resubmission sharing this uid with a genuinely different payload correctly still triggers the `RESTATEMENT` label (mechanism intact); (b) `SELECT event_id, outcome_text FROM events WHERE event_uid='CBN-MPC-2014-01-21'` shows 154 and 156 both carry ordinary `outcome_text='hold'` while only the new row carries `outcome_text='data_quality_correction'` — a plain SQL predicate cleanly separates correction rows from genuine captures/restatements platform-wide, without a schema change. |

### 10.5 Remaining uncertainty

None on the factual question (four independent, converging lines of evidence — see §10.1). One structural caveat remains, already disclosed in §10.2: `validate_batch()`'s report-level `RESTATEMENT`/`CONFLICT` labeling does not currently distinguish a cross-source correction from a same-source restatement at the point of ingestion (it silently accepts both when no `effective_date`/`direction` conflict exists) — the distinction is fully recoverable afterward via `outcome_text`, but is not surfaced in `reports/event_quality_2026-08-08.md` itself. Not remediated; flagged for awareness only.

## 11. Decision — scaling news ingestion (ticker-identity dimension only)

**GO**, scoped specifically to: the event-identity/dedup logic is now safe for ticker-scoped, multi-company batches at the scale tested (2-company batches; REGALINS/UNIVINSURE real-data replay; synthetic multi-ticker and multi-outlet cases). All 8 mandated regression tests pass with behavior matching their derived (not invented) expected semantics, and market/sector-scoped behavior is verified bit-for-bit unaffected.

The `outcome_numeric IS NULL` identical-payload bug (§9) was found and fixed within this same stage, and re-verified with the full 8-test suite plus 2 additional edge cases — no longer a caveat on this GO.

This GO is **narrow** and does not extend to:
- The `mpc_decision` 2014-01-21 anomaly (§6) — unrelated to news ingestion directly (predates this project's news work, both rows are market-scoped with `ticker=NULL`), but is evidence that this pipeline's historical data has at least one unresolved integrity question, worth resolving independently.
- Any question of information novelty, source coverage, or economic value of news ingestion at scale — those were Stage 10C/10D questions, not re-litigated here.
- Systematic/large-scale ingestion itself, H-019, factor construction, or backtesting — all remain out of scope pending separate, explicit authorization.
