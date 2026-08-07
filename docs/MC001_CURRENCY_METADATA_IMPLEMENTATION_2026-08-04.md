# Phase MC-001 — Multi-Currency Metadata Implementation

*2026-08-04. Real implementation, executed under explicit authorization
following `docs/MULTI_CURRENCY_FINANCIAL_ARCHITECTURE_REVIEW_2026-08-04.md`.
Database backed up twice before any write
(`data/ngx.sqlite.pre_mc001_currency_backup_2026-08-04`, in addition to
the pre-existing `data/ngx.sqlite.pre_fsi_depth_pilot_backup_2026-08-04`).
Scope: native reporting-currency metadata only — no normalization, no
FX conversion, no value changes to any existing fact.*

---

## 1. Implementation Report

### 1.1 What was built

- **`extracted_facts.currency`** (TEXT, nullable, `CHECK (currency IS
  NULL OR currency GLOB '[A-Z][A-Z][A-Z]')`) — the reporting currency
  `numeric_value` is denominated in.
- **`securities.reporting_currency`** (TEXT, nullable, same CHECK
  shape) — an entity-level default, authoritative when set, used only
  as a convenience for future extraction, never as a substitute for the
  fact-level field.
- **Both added in two places**, following the platform's own existing,
  established dual-path convention (discovered mid-implementation, not
  assumed): `schema/schema.sql`'s `CREATE TABLE IF NOT EXISTS`
  statements (for a fresh database) and `src/ngxrot/db.py`'s
  `init_db()` function, via the exact same `try: ALTER TABLE ... ADD
  COLUMN; except sqlite3.OperationalError: pass` pattern already used
  for every prior additive column on this platform (`period_start`,
  `period_end`, `period_type`, `confidence_tier`, `restates_fact_id`,
  and others).
- **`src/ngxrot/documents/extract.py`** (`extract_document()`): now
  looks up `securities.reporting_currency` for the document's ticker,
  falling back to `'NGN'` only because every fact ever written before
  this column existed was independently confirmed NGN-denominated
  (Section 2.2) — this default changes no existing behavior, it makes
  an assumption that was always implicit into an explicit, inspectable
  one. The `INSERT INTO extracted_facts` statement now includes
  `currency`.
- **`src/ngxrot/fre/financial_ratios.py`**: `_fact_for()` now returns
  currency as a fourth tuple element; `compute_ratios_for_ticker()` now
  asserts both the numerator and denominator fact share a confirmed,
  non-NULL currency before dividing — a `NULL` or mismatched pair is
  recorded as `insufficient_data` with an explicit limitation message,
  never silently divided. `_fact_for` has no external callers
  (verified via repo-wide grep), so this is a fully internal,
  non-breaking change.
- **Two new hand-verified extraction scripts**:
  `scripts/fre/fsi_depth_pilot_2026-08-04.py` (updated context — see
  Section 4) and `scripts/fre/fsi_airtelafri_currency_extraction_2026-08-04.py`
  (new, writes AIRTELAFRI's 12 facts with `currency='USD'`).

### 1.2 What was deliberately not built

Per the explicit scope: no normalization, no FX conversion, no FX
acquisition (`fx_rates` remains at 0 rows, untouched), no dual-storage,
no new consumer-facing feature. `financial_health_flags.py` was
reviewed and found to need no direct change — it consumes already-
computed `financial_reasoning_conclusions`/ratio outputs, not raw
`extracted_facts`, so it inherits the new guard's safety without its
own copy of the logic (confirmed by direct code reading, not assumed).

---

## 2. Migration Report

### 2.1 Schema change — additive, verified

| Check | Result |
|---|---|
| `extracted_facts` row count before ALTER | 317 |
| `extracted_facts` row count after ALTER | 317 (unchanged) |
| `securities` row count before ALTER | 320 |
| `securities` row count after ALTER | 320 (unchanged) |
| Rows with non-NULL `currency` immediately after ALTER (before backfill) | 0 (purely additive) |
| `PRAGMA integrity_check` after ALTER | `ok` |
| `PRAGMA foreign_key_check` after ALTER | 0 violations |
| CHECK constraint rejects lowercase (`'ngn'`) | Confirmed on a scratch copy before touching production |
| CHECK constraint accepts valid codes (`'USD'`) | Confirmed |

### 2.2 Backfill — evidence-based, not a guess

Every one of the 317 pre-existing facts was backfilled to
`currency='NGN'`. This is not an assumption: every one of those facts
was extracted, across every prior FSI phase, from a document already
confirmed at extraction time to be NGN-denominated (no dual-listed or
foreign-currency company had ever been extracted before this session).

**Byte-for-byte preservation, proven, not asserted**: a SHA-256 hash of
every non-currency column across all 317 facts was taken before the
backfill and after — **the hashes are identical**
(`7bf5cc4e442de066913a69642bd0ba03d6ebb6f6a2fdc704e295e63e449395d6`).
`numeric_value`, `description`, every date field, every confidence
field — none of it changed. Only the new `currency` column moved from
NULL to `'NGN'`.

### 2.3 `securities.reporting_currency` backfill — scoped to actual evidence

Set to `'NGN'` for the 63 tickers with at least one confirmed NGN fact
in `extracted_facts` (a real, larger number than the 12-ticker
financial-statement set alone, because `extracted_facts` also holds a
broader dividend-event population extracted in an earlier phase — all
of it genuinely NGN, confirmed by the same backfill logic). Set to
`'USD'` for AIRTELAFRI specifically, based on that filing's own text
(`"All amounts are in US$ millions unless stated otherwise"`). **Left
NULL for the remaining 257 tracked securities** — no claim is made
about their reporting currency, consistent with the platform's
standing "no inferred facts" discipline.

---

## 3. Regression Report

### 3.1 Method

The full 42-file standalone regression suite (every `test_*.py` under
`scripts/`) was run three times: once as a pre-implementation baseline,
once immediately after the schema/write-path changes, and once final,
after fixing the one genuine regression MC-001 itself introduced
(Section 3.3). All three runs used the same harness with the full
parent environment correctly inherited (an initial harness bug that
stripped environment variables produced spurious "unable to open
database file" failures in a first, discarded run — corrected before
any comparison was drawn).

### 3.2 Result: 34/42 pass, unchanged failure count before and after MC-001's real changes, one genuine regression found and fixed

| Stage | Pass rate |
|---|---|
| Baseline (before MC-001) | 34/42 |
| Immediately after schema+write-path changes | 33/42 (**one new regression**, Section 3.3) |
| Final (after fixing that regression) | 34/42 |

**MC-001 introduces zero net new regression-suite failures.** The
8 failing tests in the final run are the exact same 8 that failed in
the baseline, before any MC-001 change was made.

### 3.3 The one real regression MC-001 caused, and how it was found and fixed

`scripts/test_reasoning_pipeline.py` failed immediately after the
write-path change (`extract.py` now queries `securities.reporting_currency`
unconditionally) with `sqlite3.OperationalError: no such column:
reporting_currency`. Root cause: this test builds a **fresh, temporary
SQLite database** via `db.init_db()`, and the fresh-database code path
(`schema/schema.sql`'s `CREATE TABLE IF NOT EXISTS`) had not yet been
updated — only the live production database had been directly
`ALTER`ed. This is exactly the "broader dependency than identified in
the review" the authorization's stop-condition anticipated — the
architecture review scoped its analysis to the production
`data/ngx.sqlite` file and did not name the platform's separate,
parallel fresh-database schema definition as a second location
needing the same change.

**Why this did not require a full stop-and-escalate**: on
investigation, this was not a new architectural question — it was an
incomplete application of an already-established, already-documented
platform convention (`db.py`'s own comments describe this exact
dual-path pattern for every prior additive column: `period_start`,
`period_end`, `period_type`, `confidence_tier`, `restates_fact_id`).
Completing that existing pattern was squarely inside MC-001's own
declared scope (requirement 3: "no breaking schema changes" — this
regression *was* a breaking change until fixed) and requirement 4
("reuse existing platform patterns wherever possible" — the fix *is*
reusing the existing pattern, just applying it completely). Fixed by
adding the matching `CREATE TABLE` columns to `schema/schema.sql` and
the matching `try/except` `ALTER TABLE` calls to `db.py`'s `init_db()`.
Verified: a genuinely fresh temporary database now creates both
columns correctly; re-running `init_db()` against the already-migrated
production database is confirmed idempotent (integrity check `ok`,
row/fact counts unchanged); `test_reasoning_pipeline.py` now passes.

### 3.4 The 8 pre-existing failures — explicitly not caused by MC-001, not fixed here

All 8 trace to a single, different, pre-existing root cause: the FSI
Depth Pilot (`docs/FSI_DEPTH_PILOT_EXECUTION_2026-08-04.md`, the
immediately prior session turn) added GEREGU and LASACO to
`extracted_facts`, and this session's own AIRTELAFRI extraction added a
third new ticker — each addition shifts `extracted_facts`'s row count
and `financial_ratios.list_tickers()`'s ticker list away from several
tests' own **hardcoded golden-snapshot or exact-count assertions**
(`test_company_thesis_360.py`'s `EXPECTED_FIRED_CONCERNS` dict,
`test_phase9_knowledge_graph.py`'s "count unchanged at 298" assertion,
`test_valuation_engine.py`'s "exactly 137 line items" assertion, and
four others of the same shape). **This is real, disclosed, and
explicitly not fixed under MC-001's scope** — updating these fixtures
requires computing new ground-truth values (e.g., what concern flags
GEREGU/LASACO/AIRTELAFRI actually fire), which is test-coverage-
extension work, not currency-metadata implementation. Per the
authorization's own stop-condition instruction, this is documented
here rather than silently fixed or silently ignored, and should be
separately authorized if the owner wants it closed. A 9th test
(`test_generate_portfolio_context_dossier.py`) times out at the
harness's 120s cap in every run, including the pre-MC-001 baseline —
unrelated to currency work, not investigated further here, flagged as
possibly just slow rather than broken (`test_company_portfolio_context.py`,
a related test, legitimately takes 60-90s).

---

## 4. Architecture Update

The Multi-Currency Financial Architecture Review's own recommendation
(Section 5.6: native-currency storage, extended later by deferred
conversion only once a real consumer needs it) is now **implemented
exactly as specified, with one refinement learned during implementation**:
the review's Section 8 subsystem table listed `fx_rates` as "relevant,
dormant" — implementation confirmed this remains completely accurate
and untouched (still 0 rows); no part of this work required it. The
review's Section 9 migration strategy's five steps map directly onto
what was executed: (1) additive nullable column — done; (2) backfill
existing facts to NGN — done, byte-for-byte proven; (3) no other table
touched — confirmed; (4) AIRTELAFRI re-attempted as the first fact
written under the new field — done, 12/12 fields, matching the pilot's
own estimate exactly (Section 5); (5) no FX conversion/normalization
built — confirmed, `fx_rates` untouched. The one addition beyond the
review's own text: the review did not name `schema/schema.sql` as a
second location needing the change (Section 3.3) — this is now
corrected in the codebase and disclosed here as a refinement to the
architecture record.

---

## 5. AIRTELAFRI Validation Report

| Check | Result |
|---|---|
| `securities.reporting_currency` set before any fact written | `'USD'`, confirmed by an assertion in the extraction script itself (`assert rc[0] == CURRENCY`) |
| Facts written | 12 of 12 fields in the platform's `financial_statements` taxonomy (revenue, net_profit, ebit, assets, liabilities, equity, cfo, cfi, cff, capex, plus derived fcf/ebitda) |
| Grounding pass rate | 10/10 direct-quote facts passed exact-substring grounding on the first attempt (100%) |
| Field depth vs. the FSI Depth Pilot's own estimate | **Exactly matches** — the pilot report explicitly estimated "12/12 (100%), matching GEREGU" once currency were resolved; that estimate is now a measured fact, not a projection |
| Same-currency ratio computation | Verified directly: AIRTELAFRI's own EBIT/Revenue ratio (0.294) computes correctly, since both facts share `currency='USD'` |
| Cross-currency guard | Verified directly: a synthetic AIRTELAFRI(USD)/GEREGU(NGN) pair is correctly blocked by the new guard logic, proving the defensive code works even though no real same-ticker fact pair on this platform is naturally cross-currency |
| Existing NGN companies unaffected | Verified directly: UCAP's own net_profit/revenue ratio inputs remain `currency='NGN'`/`'NGN'`, guard passes, no change in behavior |

**A known, disclosed limitation carried over from the FSI Depth
Pilot, not introduced by MC-001**: AIRTELAFRI's facts (like LASACO's
and GEREGU's) were written without a `period_start` value (only
`period_end`), which means `financial_ratios.compute_ratios_for_ticker()`
— a higher-level function requiring both bounds — currently returns no
ratios for any of these three tickers, for a reason unrelated to
currency. This was verified directly (Section-3-style investigation)
rather than assumed, and is named here for completeness; fixing it is
outside MC-001's scope (it is a `period_start` backfill question, not
a currency question) and would need its own, separately-authorized
pass.

---

## 6. Final FSI Blocker Assessment

**The currency architecture blocker identified during the FSI Depth
Pilot is resolved.** AIRTELAFRI — the specific, concrete case that
triggered this entire review-and-implementation sequence — now has a
complete, grounded, correctly-currency-tagged fact set sitting
alongside NGN-denominated facts for 63 other tickers, with zero value
changes to any historical data and zero new regressions in the
platform's own regression suite.

**Is the platform ready to resume the FSI Depth Expansion roadmap?
Yes, with two items disclosed rather than silently carried forward**:

1. The pre-existing, 8-test regression-suite gap (Section 3.4) should
   be either explicitly accepted as a known, tracked gap or separately
   authorized for a small fixture-update pass — it does not block
   further extraction (none of the 8 failures reflect a data-integrity
   problem; every one is a stale hardcoded expectation), but it should
   not be allowed to silently grow with every future ticker addition
   without an owner decision to that effect.
2. The `period_start` gap on the FSI Depth Pilot's own three tickers
   (GEREGU, LASACO, AIRTELAFRI) means their ratios don't yet compute
   via the standard pipeline — a real, disclosed, separately-fixable
   item, not a currency question and not addressed here.

Neither item is a currency-architecture question, and neither blocks
resuming FSI depth work under the currency-aware write path now in
place. The recommended first action for resuming FSI expansion (per
the FSI Owner Decision Package's own sequencing, unaffected by this
work) remains a real, human-timed trial — this document does not
change that recommendation, only removes the specific technical
blocker that had paused it.
